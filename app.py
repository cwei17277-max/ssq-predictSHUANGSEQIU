import streamlit as st
import pandas as pd
import numpy as np
import requests
import random
import json
from typing import Dict, List, Any

# ==========================================
# 已配置您专属的腾讯云 Serverless 代理 URL
# ==========================================
PROXY_URL = "https://1333364180-9213182ptj.ap-guangzhou.tencentscf.com"

class LotteryEngine:
    """多彩种实时 API 分析引擎（支持双色球、大乐透、3D、香港六合彩）"""

    @staticmethod
    def fetch_data(lottery_type: str, limit: int = 100) -> List[Dict]:
        """通过专属腾讯云代理抓取各彩种官方实时开奖数据"""
        try:
            # 拼接请求参数
            url = f"{PROXY_URL}?type={lottery_type}&limit={limit}"
            res = requests.get(url, timeout=10)
            
            if res.status_code != 200:
                st.error(f"代理响应状态码异常: {res.status_code}")
                return []

            data = res.json()
            # 兼容处理 JSON 字符串嵌套情况
            if isinstance(data, str):
                data = json.loads(data)

            results = []

            # 1. 双色球 (SSQ) & 福彩 3D
            if lottery_type in ["ssq", "3d"]:
                raw_list = data.get("result", [])
                for item in raw_list[:limit]:
                    code = item.get("code", "")
                    red_str = item.get("red", "")
                    blue_str = item.get("blue", "")
                    if red_str:
                        reds = [int(x) for x in red_str.split(",")]
                        blue = int(blue_str) if blue_str else None
                        results.append({"period": str(code), "reds": reds, "blue": blue})

            # 2. 超级大乐透 (DLT)
            elif lottery_type == "dlt":
                raw_list = data.get("value", {}).get("list", [])
                for item in raw_list[:limit]:
                    code = item.get("lotteryDrawNum", "")
                    nums_str = item.get("lotteryDrawResult", "")  # 格式如: "01 05 12 23 30 02 08"
                    if nums_str:
                        parts = nums_str.split()
                        if len(parts) >= 7:
                            reds = [int(x) for x in parts[:5]]
                            blues = [int(x) for x in parts[5:7]]
                            results.append({"period": str(code), "reds": reds, "blues": blues})

            # 3. 香港六合彩 (LHC)
            elif lottery_type == "lhc":
                raw_list = data.get("data", []) if isinstance(data, dict) else data
                for item in raw_list[:limit]:
                    code = item.get("code", item.get("period", ""))
                    red_str = item.get("red", "")
                    blue_str = item.get("blue", "")  # 特码
                    if red_str and blue_str:
                        reds = [int(x) for x in red_str.split(",")]
                        blue = int(blue_str)
                        results.append({"period": str(code), "reds": reds, "blue": blue})

            return results
        except Exception as e:
            st.error(f"连线专属代理失败: {e}")
            return []

    @classmethod
    def analyze(cls, lottery_type: str, history_limit: int = 100, sim_count: int = 10000) -> Dict[str, Any]:
        """基于真实历史数据的冷热码统计与多维概率推演"""
        history = cls.fetch_data(lottery_type, limit=history_limit)
        if not history:
            return {"error": "无法获取 API 实时数据，请检查网络或代理通道状态"}

        latest_period = history[0]["period"]
        total_fetched = len(history)

        # ----------------------------------------------------
        # 彩种 1：双色球 (SSQ)
        # ----------------------------------------------------
        if lottery_type == "ssq":
            all_reds = [num for item in history for num in item["reds"]]
            hot_reds = pd.Series(all_reds).value_counts().head(15).index.tolist()
            if len(hot_reds) < 6: hot_reds = list(range(1, 34))

            rec_reds = []
            for _ in range(sim_count):
                sample = sorted(random.sample(hot_reds, 6))
                odd_count = sum(1 for x in sample if x % 2 != 0)
                total_sum = sum(sample)
                # 条件控制：奇偶比 2:4 ~ 4:2 且 和值在 80~120
                if 2 <= odd_count <= 4 and 80 <= total_sum <= 120:
                    rec_reds = sample
                    break
            if not rec_reds: rec_reds = sorted(random.sample(hot_reds, 6))

            all_blues = [item["blue"] for item in history if item["blue"] is not None]
            blue_counts = pd.Series(all_blues).value_counts()
            hot_blue = int(blue_counts.index[0])

            return {
                "彩种": "双色球",
                "最新期号": latest_period,
                "解析期数": total_fetched,
                "推荐组合": f"🔴 红球: {rec_reds}  |  🔵 蓝球: [{hot_blue}]",
                "红球高频热码池": hot_reds,
                "推荐和值": sum(rec_reds),
                "奇偶比": f"{sum(1 for x in rec_reds if x % 2 != 0)}:{sum(1 for x in rec_reds if x % 2 == 0)}"
            }

        # ----------------------------------------------------
        # 彩种 2：超级大乐透 (DLT)
        # ----------------------------------------------------
        elif lottery_type == "dlt":
            all_reds = [num for item in history for num in item["reds"]]
            hot_reds = pd.Series(all_reds).value_counts().head(15).index.tolist()
            if len(hot_reds) < 5: hot_reds = list(range(1, 36))

            rec_reds = []
            for _ in range(sim_count):
                sample = sorted(random.sample(hot_reds, 5))
                if 70 <= sum(sample) <= 110:
                    rec_reds = sample
                    break
            if not rec_reds: rec_reds = sorted(random.sample(hot_reds, 5))

            all_blues = [num for item in history for num in item.get("blues", [])]
            hot_blues = sorted([int(x) for x in pd.Series(all_blues).value_counts().head(2).index.tolist()])

            return {
                "彩种": "超级大乐透",
                "最新期号": latest_period,
                "解析期数": total_fetched,
                "推荐组合": f"🔴 前区(红): {rec_reds}  |  🔵 后区(蓝): {hot_blues}",
                "前区热码池": hot_reds,
                "推荐和值": sum(rec_reds)
            }

        # ----------------------------------------------------
        # 彩种 3：福彩 3D
        # ----------------------------------------------------
        elif lottery_type == "3d":
            pos1 = [item["reds"][0] for item in history if len(item["reds"]) == 3]
            pos2 = [item["reds"][1] for item in history if len(item["reds"]) == 3]
            pos3 = [item["reds"][2] for item in history if len(item["reds"]) == 3]

            d1 = int(pd.Series(pos1).value_counts().index[0])
            d2 = int(pd.Series(pos2).value_counts().index[0])
            d3 = int(pd.Series(pos3).value_counts().index[0])

            return {
                "彩种": "福彩 3D",
                "最新期号": latest_period,
                "解析期数": total_fetched,
                "推荐组合": f"🎯 百位: [{d1}] | 十位: [{d2}] | 个位: [{d3}]  (直选号码: {d1}{d2}{d3})",
                "推荐和值": d1 + d2 + d3
            }

        # ----------------------------------------------------
        # 彩种 4：香港六合彩 (LHC - 专项强化特码分析)
        # ----------------------------------------------------
        elif lottery_type == "lhc":
            # 1. 正码分析 (1-49)
            all_reds = [num for item in history for num in item["reds"]]
            hot_reds = pd.Series(all_reds).value_counts().head(18).index.tolist()
            if len(hot_reds) < 6: hot_reds = list(range(1, 50))

            rec_reds = sorted(random.sample(hot_reds, 6))

            # 2. 特码专项统计 (1-49)
            all_specials = [item["blue"] for item in history if item["blue"] is not None]
            special_counts = pd.Series(all_specials).value_counts()
            
            # 第一热门特码
            top_special = int(special_counts.index[0])
            # 前 3 个最热特码候选
            top3_specials = [int(x) for x in special_counts.head(3).index.tolist()]

            # 特码单双/大小特征
            special_attr = f"{'单' if top_special % 2 != 0 else '双'} | {'大' if top_special >= 25 else '小'}"

            return {
                "彩种": "香港六合彩",
                "最新期号": latest_period,
                "解析期数": total_fetched,
                "推荐组合": f"🔴 正码(6位): {rec_reds}  |  🌟 推荐精选特码: [{top_special}]",
                "热门特码候选(Top3)": top3_specials,
                "主推特码属性": special_attr,
                "正码高频热码池": hot_reds,
                "正码和值": sum(rec_reds)
            }


# ==========================================
# 前端 Streamlit 交互界面
# ==========================================
def main():
    st.set_page_config(
        page_title="多彩种 API 实时数据分析平台",
        page_icon="🎰",
        layout="wide"
    )

    st.title("🎰 多彩种 API 实时数据分析与推荐")
    st.caption("数据接入：腾讯云 Serverless 专属代理通道 (`tencentscf.com`)[cite: 6]")
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

        history_count = st.slider("拉取最新历史期数", 10, 100, 100, step=10)
        sim_count = st.slider("算法碰撞迭代次数", 1000, 50000, 10000, step=1000)

        btn = st.button("🚀 连线专属代理并实时分析", type="primary", use_container_width=True)

    with col2:
        if btn:
            with st.spinner("正在通过专属云代理获取最新真实开奖记录..."):
                res = LotteryEngine.analyze(lottery_choice, history_count, sim_count)

                if "error" not in res:
                    st.success(f"✅ 通道连通成功！已同步最新第 **{res['最新期号']}** 期（深度分析了最新 {res['解析期数']} 期数据）。")
                    st.markdown("---")
                    st.subheader("💡 算法推演推荐号码")
                    st.markdown(f"### {res['推荐组合']}")
                    
                    # 如果是六合彩，额外突出特码分析结果
                    if lottery_choice == "lhc":
                        st.info(f"🌟 **特码专项研判**：精选 Top3 热码为 `{res['热门特码候选(Top3)']}`，主推特码形态特征为 `【{res['主推特码属性']}】`")

                    st.markdown("---")
                    st.subheader("📊 详细特征指标")
                    st.json(res)
                else:
                    st.error(res["error"])

if __name__ == "__main__":
    main()
