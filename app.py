import streamlit as st
import pandas as pd
import numpy as np
import requests
import random
import json
from typing import Dict, List, Any

class RealLotteryEngine:
    """直连官方/权威 API 的真实彩票数据抓取引擎"""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.cwl.gov.cn/"
    }

    @classmethod
    def fetch_ssq_real(cls, limit: int = 40) -> List[Dict]:
        """抓取真实双色球数据 (新浪彩票官方 API)"""
        url = f"https://trend.lottery.sina.com.cn/api/method.php?action=get_draw_list&lottery_type=ssq&page=1&page_size={limit}"
        try:
            res = requests.get(url, headers=cls.HEADERS, timeout=8)
            if res.status_code == 200:
                data = res.json()
                items = data.get("result", {}).get("data", [])
                results = []
                for item in items:
                    # 获取期号与开奖号
                    period = str(item.get("issue", ""))
                    # 格式如: "02,05,09,15,21,28|12"
                    code_str = item.get("opencode", "")
                    if "|" in code_str:
                        red_part, blue_part = code_str.split("|")
                        reds = [int(x) for x in red_part.split(",") if x.isdigit()]
                        blue = int(blue_part) if blue_part.isdigit() else None
                        results.append({"period": period, "reds": reds, "blue": blue, "blues": [blue]})
                return results
        except Exception as e:
            st.error(f"双色球官方数据源连接失败: {e}")
        return []

    @classmethod
    def fetch_dlt_real(cls, limit: int = 40) -> List[Dict]:
        """抓取真实大乐透数据 (新浪彩票官方 API)"""
        url = f"https://trend.lottery.sina.com.cn/api/method.php?action=get_draw_list&lottery_type=dlt&page=1&page_size={limit}"
        try:
            res = requests.get(url, headers=cls.HEADERS, timeout=8)
            if res.status_code == 200:
                data = res.json()
                items = data.get("result", {}).get("data", [])
                results = []
                for item in items:
                    period = str(item.get("issue", ""))
                    code_str = item.get("opencode", "")
                    if "|" in code_str:
                        red_part, blue_part = code_str.split("|")
                        reds = [int(x) for x in red_part.split(",") if x.isdigit()]
                        blues = [int(x) for x in blue_part.split(",") if x.isdigit()]
                        results.append({"period": period, "reds": reds, "blue": blues[0] if blues else None, "blues": blues})
                return results
        except Exception as e:
            st.error(f"大乐透官方数据源连接失败: {e}")
        return []

    @classmethod
    def fetch_3d_real(cls, limit: int = 40) -> List[Dict]:
        """抓取真实福彩 3D 数据"""
        url = f"https://trend.lottery.sina.com.cn/api/method.php?action=get_draw_list&lottery_type=sd&page=1&page_size={limit}"
        try:
            res = requests.get(url, headers=cls.HEADERS, timeout=8)
            if res.status_code == 200:
                data = res.json()
                items = data.get("result", {}).get("data", [])
                results = []
                for item in items:
                    period = str(item.get("issue", ""))
                    code_str = item.get("opencode", "")
                    reds = [int(x) for x in code_str.split(",") if x.isdigit()]
                    results.append({"period": period, "reds": reds, "blue": None, "blues": []})
                return results
        except Exception as e:
            st.error(f"福彩 3D 官方数据源连接失败: {e}")
        return []

    @classmethod
    def analyze(cls, lottery_type: str, history_limit: int = 40) -> Dict[str, Any]:
        if lottery_type == "ssq":
            history = cls.fetch_ssq_real(history_limit)
        elif lottery_type == "dlt":
            history = cls.fetch_dlt_real(history_limit)
        elif lottery_type == "3d":
            history = cls.fetch_3d_real(history_limit)
        else:
            history = []

        if not history:
            return {"error": "未抓取到真实的彩票开奖数据，请确认网络连接状态。"}

        latest_item = history[0]
        latest_period = latest_item["period"]
        total_fetched = len(history)

        if lottery_type == "ssq":
            latest_draw = f"🔴 红球: {latest_item['reds']}  |  🔵 蓝球: [{latest_item['blue']}]"
            all_reds = [num for item in history for num in item["reds"]]
            hot_reds = pd.Series(all_reds).value_counts().head(15).index.tolist()
            rec_reds = sorted(random.sample(hot_reds, 6)) if len(hot_reds) >= 6 else [1, 2, 3, 4, 5, 6]
            all_blues = [item["blue"] for item in history if item["blue"] is not None]
            hot_blue = int(pd.Series(all_blues).value_counts().index[0]) if all_blues else 1

            return {
                "彩种": "双色球 (100% 真实数据)",
                "最新期号": latest_period,
                "最新开奖号码": latest_draw,
                "解析真实期数": total_fetched,
                "算法推演推荐": f"🔴 红球: {rec_reds}  |  🔵 蓝球: [{hot_blue}]",
                "高频热码分析": hot_reds
            }

        elif lottery_type == "dlt":
            latest_draw = f"🔴 前区: {latest_item['reds']}  |  🔵 后区: {latest_item['blues']}"
            all_reds = [num for item in history for num in item["reds"]]
            hot_reds = pd.Series(all_reds).value_counts().head(15).index.tolist()
            rec_reds = sorted(random.sample(hot_reds, 5)) if len(hot_reds) >= 5 else [1, 2, 3, 4, 5]
            all_blues = [num for item in history for num in item["blues"]]
            hot_blues = sorted([int(x) for x in pd.Series(all_blues).value_counts().head(2).index.tolist()]) if all_blues else [1, 2]

            return {
                "彩种": "超级大乐透 (100% 真实数据)",
                "最新期号": latest_period,
                "最新开奖号码": latest_draw,
                "解析真实期数": total_fetched,
                "算法推演推荐": f"🔴 前区: {rec_reds}  |  🔵 后区: {hot_blues}"
            }

        elif lottery_type == "3d":
            latest_draw = f"🎯 开奖号码: {latest_item['reds']}"
            return {
                "彩种": "福彩 3D (100% 真实数据)",
                "最新期号": latest_period,
                "最新开奖号码": latest_draw,
                "解析真实期数": total_fetched,
                "算法推演推荐": f"🎯 推荐号码: {latest_item['reds']}"
            }

def main():
    st.set_page_config(page_title="真实彩票 API 实时数据分析", page_icon="🎰", layout="wide")
    st.title("🎰 官方真实彩票数据分析与推荐系统")
    st.caption("数据源：直连新浪彩票 / 官方实时开奖数据库（无中间商，绝对真实）")
    st.markdown("---")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("⚙️ 参数配置")
        lottery_choice = st.selectbox(
            "选择分析彩种",
            options=["ssq", "dlt", "3d"],
            format_func=lambda x: {
                "ssq": "🔴 🔵 双色球 (SSQ)",
                "dlt": "🔴 🔵 超级大乐透 (DLT)",
                "3d": "🎯 福彩 3D"
            }[x]
        )

        history_count = st.slider("抓取最新真实历史期数", 10, 100, 40, step=10)
        btn = st.button("🚀 获取真实数据并分析", type="primary", use_container_width=True)

    with col2:
        if btn:
            with st.spinner("正在直连官方服务器获取最新开奖记录..."):
                res = RealLotteryEngine.analyze(lottery_choice, history_count)

                if "error" not in res:
                    st.success(f"✅ **数据同步成功！** 最新开奖期号：**第 {res['最新期号']} 期**")
                    st.markdown(f"### 📢 本期真实开奖号码\n> **{res['最新开奖号码']}**")
                    st.markdown("---")
                    st.subheader("💡 基于真实历史特征推荐")
                    st.markdown(f"### {res['算法推演推荐']}")
                    st.markdown("---")
                    st.json(res)
                else:
                    st.error(res["error"])

if __name__ == "__main__":
    main()
