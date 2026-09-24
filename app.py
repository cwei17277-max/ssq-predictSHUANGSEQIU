import streamlit as st
import pandas as pd
import numpy as np
import requests
import random
import json
from typing import Dict, List, Any

PROXY_URL = "https://1333364180-9213182ptj.ap-guangzhou.tencentscf.com"

class LotteryEngine:
    """多彩种真实 API 分析引擎"""

    @staticmethod
    def fetch_data(lottery_type: str, limit: int = 100) -> List[Dict]:
        try:
            url = f"{PROXY_URL}?type={lottery_type}&limit={limit}"
            res = requests.get(url, timeout=12)
            
            if res.status_code != 200:
                st.error(f"代理通道响应状态码异常 ({res.status_code})，请检查云函数配置。")
                return []

            data = res.json()
            if isinstance(data, str):
                data = json.loads(data)

            results = []

            # 获取数组主体
            data_list = []
            if isinstance(data, list):
                data_list = data
            elif isinstance(data, dict):
                if "data" in data and isinstance(data["data"], list):
                    data_list = data["data"]
                elif "result" in data and isinstance(data["result"], list):
                    data_list = data["result"]
                elif "value" in data and isinstance(data["value"], dict) and "list" in data["value"]:
                    data_list = data["value"]["list"]

            for item in data_list[:limit]:
                # 兼容不同 API 的期号字段
                code = str(item.get("expect", item.get("code", item.get("period", item.get("lotteryDrawNum", "")))))
                
                # 兼容不同 API 的开奖号码字段
                open_num = str(item.get("opencode", item.get("openCode", item.get("lotteryDrawResult", item.get("number", "")))))

                if open_num and open_num != "None":
                    # 处理带加号/竖线/空格的分隔符
                    open_num = open_num.replace("+", "|").replace(" ", ",").replace("-", ",")
                    parts = open_num.split("|")

                    red_str = parts[0]
                    blue_str = parts[1] if len(parts) > 1 else ""

                    # 提取红球数字
                    reds = [int(x) for x in red_str.split(",") if x.strip().isdigit()]
                    
                    # 提取蓝球数字
                    blues = [int(x) for x in blue_str.split(",") if x.strip().isdigit()]

                    if reds:
                        blue = blues[0] if blues else (blues if len(blues) > 0 else None)
                        results.append({
                            "period": code,
                            "reds": reds,
                            "blue": blue,
                            "blues": blues
                        })

            return results
        except Exception as e:
            st.error(f"数据解析异常: {e}")
            return []

    @classmethod
    def analyze(cls, lottery_type: str, history_limit: int = 100, sim_count: int = 10000) -> Dict[str, Any]:
        history = cls.fetch_data(lottery_type, limit=history_limit)
        if not history:
            return {"error": "暂无法获取真实 API 开奖数据，请检查云函数部署或网络连通性"}

        latest_item = history[0]
        latest_period = latest_item["period"]
        total_fetched = len(history)

        if lottery_type == "ssq":
            latest_draw = f"🔴 红球: {latest_item['reds']}  |  🔵 蓝球: [{latest_item['blue']}]"

            all_reds = [num for item in history for num in item["reds"]]
            hot_reds = pd.Series(all_reds).value_counts().head(15).index.tolist()
            if len(hot_reds) < 6: hot_reds = list(range(1, 34))

            rec_reds = sorted(random.sample(hot_reds, 6))
            all_blues = [item["blue"] for item in history if item["blue"] is not None]
            hot_blue = int(pd.Series(all_blues).value_counts().index[0]) if all_blues else random.randint(1, 16)

            return {
                "彩种": "双色球",
                "最新期号": latest_period,
                "最新开奖号码": latest_draw,
                "解析期数": total_fetched,
                "推荐组合": f"🔴 红球: {rec_reds}  |  🔵 蓝球: [{hot_blue}]",
                "红球高频热码池": hot_reds,
                "推荐和值": sum(rec_reds)
            }

        elif lottery_type == "dlt":
            latest_draw = f"🔴 前区: {latest_item['reds'][:5]}  |  🔵 后区: {latest_item.get('blues', []) or latest_item['reds'][5:]}"

            all_reds = [num for item in history for num in item["reds"]]
            hot_reds = pd.Series(all_reds).value_counts().head(15).index.tolist()
            if len(hot_reds) < 5: hot_reds = list(range(1, 36))

            rec_reds = sorted(random.sample(hot_reds, 5))
            all_blues = [num for item in history for num in item.get("blues", [])]
            hot_blues = sorted([int(x) for x in pd.Series(all_blues).value_counts().head(2).index.tolist()]) if all_blues else [1, 2]

            return {
                "彩种": "超级大乐透",
                "最新期号": latest_period,
                "最新开奖号码": latest_draw,
                "解析期数": total_fetched,
                "推荐组合": f"🔴 前区(红): {rec_reds}  |  🔵 后区(蓝): {hot_blues}",
                "前区热码池": hot_reds,
                "推荐和值": sum(rec_reds)
            }

        elif lottery_type == "3d":
            nums = latest_item['reds']
            draw_str = "".join(map(str, nums)) if len(nums) == 3 else str(nums)
            latest_draw = f"🎯 开奖号码: [{draw_str}]"

            pos1 = [item["reds"][0] for item in history if len(item["reds"]) >= 3]
            pos2 = [item["reds"][1] for item in history if len(item["reds"]) >= 3]
            pos3 = [item["reds"][2] for item in history if len(item["reds"]) >= 3]

            d1 = int(pd.Series(pos1).value_counts().index[0]) if pos1 else random.randint(0, 9)
            d2 = int(pd.Series(pos2).value_counts().index[0]) if pos2 else random.randint(0, 9)
            d3 = int(pd.Series(pos3).value_counts().index[0]) if pos3 else random.randint(0, 9)

            return {
                "彩种": "福彩 3D",
                "最新期号": latest_period,
                "最新开奖号码": latest_draw,
                "解析期数": total_fetched,
                "推荐组合": f"🎯 百位: [{d1}] | 十位: [{d2}] | 个位: [{d3}]  (直选: {d1}{d2}{d3})",
                "推荐和值": d1 + d2 + d3
            }

        elif lottery_type == "lhc":
            latest_draw = f"🔴 正码: {latest_item['reds']}  |  🌟 特码: [{latest_item['blue']}]"

            all_reds = [num for item in history for num in item["reds"]]
            hot_reds = pd.Series(all_reds).value_counts().head(18).index.tolist()
            if len(hot_reds) < 6: hot_reds = list(range(1, 50))

            rec_reds = sorted(random.sample(hot_reds, 6))
            all_specials = [item["blue"] for item in history if item["blue"] is not None]
            top_special = int(pd.Series(all_specials).value_counts().index[0]) if all_specials else random.randint(1, 49)

            return {
                "彩种": "香港六合彩",
                "最新期号": latest_period,
                "最新开奖号码": latest_draw,
                "解析期数": total_fetched,
                "推荐组合": f"🔴 正码: {rec_reds}  |  🌟 推荐特码: [{top_special}]"
            }

def main():
    st.set_page_config(page_title="多彩种 API 实时数据分析平台", page_icon="🎰", layout="wide")
    st.title("🎰 多彩种 API 实时数据分析与推荐")
    st.caption("数据接入：腾讯云 Serverless 专属代理通道 (`tencentscf.com`) | 真实 API 实时同步")
    st.markdown("---")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("⚙️ 参数配置")
        lottery_choice = st.selectbox(
            "选择分析彩种",
            options=["ssq", "dlt", "3d", "lhc"],
            format_func=lambda x: {
                "ssq": "🔴 🔵 双色球 (SSQ)",
                "dlt": "🔴 🔵 超级大乐透 (DLT)",
                "3d": "🎯 福彩 3D",
                "lhc": "🌟 香港六合彩 (含特码分析)"
            }[x]
        )

        history_count = st.slider("拉取最新历史期数", 10, 100, 40, step=10)
        sim_count = st.slider("算法碰撞迭代次数", 1000, 50000, 10000, step=1000)

        btn = st.button("🚀 连线专属代理并实时分析", type="primary", use_container_width=True)

    with col2:
        if btn:
            with st.spinner("正在通过专属云代理获取并分析真实开奖记录..."):
                res = LotteryEngine.analyze(lottery_choice, history_count, sim_count)

                if "error" not in res:
                    st.success(f"✅ **通道连通成功！** 已同步最新真实第 **{res['最新期号']}** 期数据。\n\n🎉 **本期实际开奖号码**：{res['最新开奖号码']}")
                    st.markdown("---")
                    st.subheader("💡 算法推演推荐号码")
                    st.markdown(f"### {res['推荐组合']}")
                    st.markdown("---")
                    st.subheader("📊 详细特征指标")
                    st.json(res)
                else:
                    st.error(res["error"])

if __name__ == "__main__":
    main()
