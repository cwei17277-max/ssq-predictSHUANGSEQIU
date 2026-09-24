import streamlit as st
import pandas as pd
import requests
import re
import json
from typing import Dict, List, Any

class RealLotteryApiEngine:
    """纯真实数据引擎：首选抓取不成功时，自动降级调取多个免费 API 数据源"""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
    }

    @classmethod
    def fetch_real_lottery(cls, lottery_type: str, limit: int = 40) -> List[Dict]:
        """按顺序调用免费 API，成功即返回，失败自动切下一个免费 API"""
        
        # ---------------- 免费 API 1: 百度开放彩票接口 ----------------
        try:
            name_map = {"ssq": "双色球", "dlt": "超级大乐透", "3d": "福彩3D", "lhc": "六合彩"}
            url = f"https://opendata.baidu.com/api.php?query={name_map.get(lottery_type, '双色球')}&resource_id=3571&oe=utf-8"
            res = requests.get(url, headers=cls.HEADERS, timeout=5)
            if res.status_code == 200:
                data = res.json()
                items = data.get("Result", [{}])[0].get("list", [])
                results = []
                for item in items[:limit]:
                    code = str(item.get("period", ""))
                    num_str = item.get("number", "")
                    if num_str:
                        parsed = cls.parse_raw_numbers(code, num_str, lottery_type)
                        if parsed:
                            results.append(parsed)
                if results:
                    return results
        except Exception:
            pass

        # ---------------- 免费 API 2: OICK 免费开放彩票 API ----------------
        try:
            url = f"https://api.oick.cn/lottery/api.php?type={lottery_type}&limit={limit}"
            res = requests.get(url, headers=cls.HEADERS, timeout=5)
            if res.status_code == 200:
                data = res.json()
                data_list = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                results = []
                for item in data_list[:limit]:
                    code = str(item.get("expect", item.get("period", "")))
                    opencode = item.get("opencode", item.get("openCode", ""))
                    if opencode:
                        parsed = cls.parse_raw_numbers(code, opencode, lottery_type)
                        if parsed:
                            results.append(parsed)
                if results:
                    return results
        except Exception:
            pass

        # ---------------- 免费 API 3: RollTools 免费公共 API ----------------
        try:
            type_map_roll = {"ssq": "ssq", "dlt": "dlt", "3d": "fc3d", "lhc": "lhc"}
            url = f"https://www.mxnzp.com/api/lottery/common/list?code={type_map_roll.get(lottery_type, 'ssq')}&page=1&app_id=qqqqqqqqqqqqqqqq&app_secret=1111111111111111"
            res = requests.get(url, headers=cls.HEADERS, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data.get("code") == 1:
                    list_data = data.get("data", {}).get("list", [])
                    results = []
                    for item in list_data[:limit]:
                        code = str(item.get("issue", ""))
                        open_code = item.get("openCode", "")
                        parsed = cls.parse_raw_numbers(code, open_code, lottery_type)
                        if parsed:
                            results.append(parsed)
                    if results:
                        return results
        except Exception:
            pass

        # ---------------- 免费 API 4: 网页实时提取接口 (保底真实解析) ----------------
        try:
            if lottery_type == "ssq":
                html_url = "https://kaijiang.500.com/ssq.shtml"
            elif lottery_type == "dlt":
                html_url = "https://kaijiang.500.com/dlt.shtml"
            elif lottery_type == "3d":
                html_url = "https://kaijiang.500.com/sd.shtml"
            else:
                html_url = None

            if html_url:
                res = requests.get(html_url, headers=cls.HEADERS, timeout=5)
                res.encoding = "gb2312"
                if res.status_code == 200:
                    period_match = re.search(r'font_red1"><b>(\d+)</b>', res.text)
                    nums = re.findall(r'<li class="ball_red">(\d+)</li>', res.text)
                    blue_num = re.findall(r'<li class="ball_blue">(\d+)</li>', res.text)
                    if period_match and nums:
                        period = period_match.group(1)
                        reds = [int(x) for x in nums]
                        blues = [int(x) for x in blue_num] if blue_num else []
                        blue = blues[0] if blues else None
                        return [{"period": period, "reds": reds, "blue": blue, "blues": blues}]
        except Exception:
            pass

        # 若全部免费 API 均因防火墙截断失败，不返回伪造数据，直接返回空
        return []

    @staticmethod
    def parse_raw_numbers(code: str, raw_str: str, lottery_type: str) -> Dict[str, Any]:
        """精准拆分正码与特码/蓝球"""
        raw_str = raw_str.replace("+", "|").replace(" ", ",").replace("-", ",").replace(":", ",")
        parts = raw_str.split("|")

        red_part = parts[0]
        blue_part = parts[1] if len(parts) > 1 else ""

        reds = [int(x) for x in red_part.split(",") if x.strip().isdigit()]
        blues = [int(x) for x in blue_part.split(",") if x.strip().isdigit()]

        blue = blues[0] if blues else None

        return {
            "period": code,
            "reds": reds,
            "blue": blue,
            "blues": blues
        }

    @classmethod
    def analyze(cls, lottery_type: str, history_limit: int = 40) -> Dict[str, Any]:
        history = cls.fetch_real_lottery(lottery_type, history_limit)
        
        if not history:
            return {
                "error": "⚠️ 当前所有免费 API 接口均暂时无法连接或请求超时，请检查网络后再试。"
            }

        latest = history[0]
        period = latest["period"]
        total = len(history)

        # 1. 双色球
        if lottery_type == "ssq":
            draw = f"🔴 红球: {latest['reds']}  |  🔵 蓝球: [{latest['blue']}]"
            all_reds = [num for item in history for num in item["reds"]]
            hot_reds = pd.Series(all_reds).value_counts().head(15).index.tolist()
            all_blues = [item["blue"] for item in history if item["blue"] is not None]
            hot_blue = int(pd.Series(all_blues).value_counts().index[0]) if all_blues else None

            return {
                "彩种名称": "双色球 (SSQ)",
                "最新开奖期号": period,
                "真实开奖号码": draw,
                "获取真实数据期数": f"近 {total} 期",
                "高频热码(红球)": hot_reds,
                "高频热码(蓝球)": hot_blue
            }

        # 2. 超级大乐透
        elif lottery_type == "dlt":
            draw = f"🔴 前区: {latest['reds']}  |  🔵 后区: {latest['blues']}"
            all_reds = [num for item in history for num in item["reds"]]
            hot_reds = pd.Series(all_reds).value_counts().head(15).index.tolist()
            all_blues = [b for item in history for b in item["blues"]]
            hot_blues = sorted([int(x) for x in pd.Series(all_blues).value_counts().head(2).index.tolist()]) if all_blues else []

            return {
                "彩种名称": "超级大乐透 (DLT)",
                "最新开奖期号": period,
                "真实开奖号码": draw,
                "获取真实数据期数": f"近 {total} 期",
                "前区高频热码": hot_reds,
                "后区高频热码": hot_blues
            }

        # 3. 福彩 3D
        elif lottery_type == "3d":
            draw = f"🎯 开奖号码: {latest['reds']}"
            return {
                "彩种名称": "福彩 3D",
                "最新开奖期号": period,
                "真实开奖号码": draw,
                "获取真实数据期数": f"近 {total} 期"
            }

        # 4. 香港六合彩 (含专属特码)
        elif lottery_type == "lhc":
            draw = f"🔴 正码: {latest['reds']}  |  🌟 专属特码: [{latest['blue']}]"
            all_reds = [num for item in history for num in item["reds"]]
            hot_reds = pd.Series(all_reds).value_counts().head(18).index.tolist()
            all_specials = [item["blue"] for item in history if item["blue"] is not None]
            hot_special = int(pd.Series(all_specials).value_counts().index[0]) if all_specials else None

            return {
                "彩种名称": "香港六合彩 (LHC)",
                "最新开奖期号": period,
                "真实开奖号码": draw,
                "获取真实数据期数": f"近 {total} 期",
                "正码热号": hot_reds,
                "特码热号": hot_special
            }

def main():
    st.set_page_config(page_title="真实彩票 API 数据平台", page_icon="🎰", layout="wide")
    st.title("🎰 真实彩票 API 数据与多源备用系统")
    st.caption("网络策略：首选抓取 -> 自动轮询调取免费 API 接口 -> 绝对不生成虚拟数据")
    st.markdown("---")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("⚙️ 彩种选择")
        lottery_choice = st.selectbox(
            "选择彩种",
            options=["ssq", "dlt", "3d", "lhc"],
            format_func=lambda x: {
                "ssq": "🔴 🔵 双色球 (SSQ)",
                "dlt": "🔴 🔵 超级大乐透 (DLT)",
                "3d": "🎯 福彩 3D",
                "lhc": "🌟 香港六合彩 (含特码)"
            }[x]
        )

        history_count = st.slider("同步历史期数", 10, 100, 40, step=10)
        btn = st.button("🚀 调取真实 API 获取开奖号", type="primary", use_container_width=True)

    with col2:
        if btn:
            with st.spinner("正在自动尝试并切换免费 API 获取最新公布开奖号码..."):
                res = RealLotteryApiEngine.analyze(lottery_choice, history_count)

                if "error" not in res:
                    st.success(f"✅ **真实 API 数据获取成功！** 彩种：**{res['彩种名称']}** | 期号：第 **{res['最新开奖期号']}** 期")
                    st.markdown(f"### 📢 官方实时开奖结果\n> **{res['真实开奖号码']}**")
                    st.markdown("---")
                    st.subheader("📊 详细分析与热码汇总")
                    st.json(res)
                else:
                    st.error(res["error"])

if __name__ == "__main__":
    main()
