import streamlit as st
import pandas as pd
import requests
import re
import json
from typing import Dict, List, Any

class RealLotteryEngine:
    """
    综合真实彩票数据引擎：
    1. 官方/权威源直连
    2. 多重公共免费 API 自动轮询
    3. 跨国 CDN 代理隧道穿透 (绕过防火墙/DNS阻断)
    4. 100% 纯真实数据，不生成任何离线伪造数据
    """

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
    }

    PROXIES = [
        "https://api.allorigins.win/raw?url=",
        "https://corsproxy.io/?"
    ]

    @classmethod
    def request_with_tunnel(cls, target_url: str, timeout: int = 5) -> str:
        """带隧道穿透的通用网络请求：先直连，失败后自动使用代理隧道穿透"""
        # 1. 尝试直连
        try:
            res = requests.get(target_url, headers=cls.HEADERS, timeout=timeout)
            if res.status_code == 200 and len(res.text) > 20:
                return res.text
        except Exception:
            pass

        # 2. 尝试代理隧道穿透
        for proxy in cls.PROXIES:
            try:
                tunnel_url = f"{proxy}{requests.utils.quote(target_url)}"
                res = requests.get(tunnel_url, headers=cls.HEADERS, timeout=timeout + 2)
                if res.status_code == 200 and len(res.text) > 20:
                    return res.text
            except Exception:
                continue

        return ""

    @classmethod
    def parse_raw_numbers(cls, code: str, raw_str: str, lottery_type: str) -> Dict[str, Any]:
        """统一解析号码：拆分正码、蓝球/特码"""
        clean_str = raw_str.replace("+", "|").replace(" ", ",").replace("-", ",").replace(":", ",")
        parts = clean_str.split("|")

        red_part = parts[0]
        blue_part = parts[1] if len(parts) > 1 else ""

        reds = [int(x) for x in red_part.split(",") if x.strip().isdigit()]
        blues = [int(x) for x in blue_part.split(",") if x.strip().isdigit()]

        blue = blues[0] if blues else None

        return {
            "period": str(code),
            "reds": reds,
            "blue": blue,
            "blues": blues
        }

    @classmethod
    def fetch_ssq(cls, limit: int = 40) -> List[Dict]:
        """抓取双色球真实数据"""
        # 源 1: 福彩官方接口 (隧道穿透)
        url1 = f"http://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=ssq&pageNo=1&pageSize={limit}"
        text1 = cls.request_with_tunnel(url1)
        if text1:
            try:
                data = json.loads(text1)
                items = data.get("result", [])
                results = []
                for item in items:
                    code = item.get("code", "")
                    reds = [int(x) for x in item.get("red", "").split(",") if x.isdigit()]
                    blue = int(item.get("blue", "")) if item.get("blue", "").isdigit() else None
                    if reds and blue is not None:
                        results.append({"period": str(code), "reds": reds, "blue": blue, "blues": [blue]})
                if results: return results
            except Exception: pass

        # 源 2: 新浪彩票接口
        url2 = f"https://trend.lottery.sina.com.cn/api/method.php?action=get_draw_list&lottery_type=ssq&page=1&page_size={limit}"
        text2 = cls.request_with_tunnel(url2)
        if text2:
            try:
                data = json.loads(text2)
                items = data.get("result", {}).get("data", [])
                results = []
                for item in items:
                    code = item.get("issue", "")
                    opencode = item.get("opencode", "")
                    parsed = cls.parse_raw_numbers(code, opencode, "ssq")
                    if parsed and parsed["reds"]:
                        results.append(parsed)
                if results: return results
            except Exception: pass

        # 源 3: 百度开放彩票接口
        url3 = "https://opendata.baidu.com/api.php?query=双色球&resource_id=3571&oe=utf-8"
        text3 = cls.request_with_tunnel(url3)
        if text3:
            try:
                data = json.loads(text3)
                items = data.get("Result", [{}])[0].get("list", [])
                results = []
                for item in items[:limit]:
                    parsed = cls.parse_raw_numbers(item.get("period", ""), item.get("number", ""), "ssq")
                    if parsed and parsed["reds"]:
                        results.append(parsed)
                if results: return results
            except Exception: pass

        return []

    @classmethod
    def fetch_dlt(cls, limit: int = 40) -> List[Dict]:
        """抓取大乐透真实数据"""
        # 源 1: 新浪彩票接口
        url1 = f"https://trend.lottery.sina.com.cn/api/method.php?action=get_draw_list&lottery_type=dlt&page=1&page_size={limit}"
        text1 = cls.request_with_tunnel(url1)
        if text1:
            try:
                data = json.loads(text1)
                items = data.get("result", {}).get("data", [])
                results = []
                for item in items:
                    code = item.get("issue", "")
                    opencode = item.get("opencode", "")
                    parsed = cls.parse_raw_numbers(code, opencode, "dlt")
                    if parsed and parsed["reds"]:
                        results.append(parsed)
                if results: return results
            except Exception: pass

        # 源 2: 百度开放 API
        url2 = "https://opendata.baidu.com/api.php?query=超级大乐透&resource_id=3571&oe=utf-8"
        text2 = cls.request_with_tunnel(url2)
        if text2:
            try:
                data = json.loads(text2)
                items = data.get("Result", [{}])[0].get("list", [])
                results = []
                for item in items[:limit]:
                    parsed = cls.parse_raw_numbers(item.get("period", ""), item.get("number", ""), "dlt")
                    if parsed and parsed["reds"]:
                        results.append(parsed)
                if results: return results
            except Exception: pass

        return []

    @classmethod
    def fetch_3d(cls, limit: int = 40) -> List[Dict]:
        """抓取福彩3D真实数据"""
        url1 = f"https://trend.lottery.sina.com.cn/api/method.php?action=get_draw_list&lottery_type=sd&page=1&page_size={limit}"
        text1 = cls.request_with_tunnel(url1)
        if text1:
            try:
                data = json.loads(text1)
                items = data.get("result", {}).get("data", [])
                results = []
                for item in items:
                    code = item.get("issue", "")
                    opencode = item.get("opencode", "")
                    reds = [int(x) for x in opencode.split(",") if x.strip().isdigit()]
                    if reds:
                        results.append({"period": str(code), "reds": reds, "blue": None, "blues": []})
                if results: return results
            except Exception: pass

        return []

    @classmethod
    def fetch_lhc(cls, limit: int = 40) -> List[Dict]:
        """抓取香港六合彩真实数据 (含特码)"""
        # 源 1: OICK 免费彩票 API
        url1 = f"https://api.oick.cn/lottery/api.php?type=lhc&limit={limit}"
        text1 = cls.request_with_tunnel(url1)
        if text1:
            try:
                data = json.loads(text1)
                items = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                results = []
                for item in items[:limit]:
                    code = item.get("expect", item.get("period", ""))
                    opencode = item.get("opencode", item.get("openCode", ""))
                    if opencode:
                        parsed = cls.parse_raw_numbers(code, opencode, "lhc")
                        if parsed and parsed["reds"]:
                            results.append(parsed)
                if results: return results
            except Exception: pass

        # 源 2: RollTools API
        url2 = f"https://www.mxnzp.com/api/lottery/common/list?code=lhc&page=1&app_id=qqqqqqqqqqqqqqqq&app_secret=1111111111111111"
        text2 = cls.request_with_tunnel(url2)
        if text2:
            try:
                data = json.loads(text2)
                if data.get("code") == 1:
                    list_data = data.get("data", {}).get("list", [])
                    results = []
                    for item in list_data[:limit]:
                        code = item.get("issue", "")
                        open_code = item.get("openCode", "")
                        parsed = cls.parse_raw_numbers(code, open_code, "lhc")
                        if parsed and parsed["reds"]:
                            results.append(parsed)
                    if results: return results
            except Exception: pass

        return []

    @classmethod
    def analyze(cls, lottery_type: str, limit: int = 40) -> Dict[str, Any]:
        """统一分析入口"""
        if lottery_type == "ssq":
            history = cls.fetch_ssq(limit)
        elif lottery_type == "dlt":
            history = cls.fetch_dlt(limit)
        elif lottery_type == "3d":
            history = cls.fetch_3d(limit)
        elif lottery_type == "lhc":
            history = cls.fetch_lhc(limit)
        else:
            history = []

        if not history:
            return {
                "error": "⚠️ 当前所有免费 API 接口及跨国代理隧道均无法连接。请检查本地网络或通过本地 Python 运行。"
            }

        latest = history[0]
        period = latest["period"]
        total = len(history)

        # 按彩种输出开奖及分析
        if lottery_type == "ssq":
            draw = f"🔴 红球: {latest['reds']}  |  🔵 蓝球: [{latest['blue']}]"
            all_reds = [num for item in history for num in item["reds"]]
            hot_reds = pd.Series(all_reds).value_counts().head(15).index.tolist() if all_reds else []
            all_blues = [item["blue"] for item in history if item["blue"] is not None]
            hot_blue = int(pd.Series(all_blues).value_counts().index[0]) if all_blues else None

            return {
                "彩种名称": "双色球 (SSQ)",
                "最新期号": period,
                "真实开奖结果": draw,
                "已获取真实期数": f"近 {total} 期",
                "高频热码(红球)": hot_reds,
                "高频热码(蓝球)": hot_blue
            }

        elif lottery_type == "dlt":
            draw = f"🔴 前区: {latest['reds']}  |  🔵 后区: {latest['blues']}"
            all_reds = [num for item in history for num in item["reds"]]
            hot_reds = pd.Series(all_reds).value_counts().head(15).index.tolist() if all_reds else []
            all_blues = [b for item in history for b in item["blues"]]
            hot_blues = sorted([int(x) for x in pd.Series(all_blues).value_counts().head(2).index.tolist()]) if all_blues else []

            return {
                "彩种名称": "超级大乐透 (DLT)",
                "最新期号": period,
                "真实开奖结果": draw,
                "已获取真实期数": f"近 {total} 期",
                "前区高频热码": hot_reds,
                "后区高频热码": hot_blues
            }

        elif lottery_type == "3d":
            draw = f"🎯 开奖号码: {latest['reds']}"
            return {
                "彩种名称": "福彩 3D",
                "最新期号": period,
                "真实开奖结果": draw,
                "已获取真实期数": f"近 {total} 期"
            }

        elif lottery_type == "lhc":
            draw = f"🔴 正码: {latest['reds']}  |  🌟 专属特码: [{latest['blue']}]"
            all_reds = [num for item in history for num in item["reds"]]
            hot_reds = pd.Series(all_reds).value_counts().head(18).index.tolist() if all_reds else []
            all_specials = [item["blue"] for item in history if item["blue"] is not None]
            hot_special = int(pd.Series(all_specials).value_counts().index[0]) if all_specials else None

            return {
                "彩种名称": "香港六合彩 (LHC)",
                "最新期号": period,
                "真实开奖结果": draw,
                "已获取真实期数": f"近 {total} 期",
                "正码热号": hot_reds,
                "特码热号": hot_special
            }


def main():
    st.set_page_config(page_title="真实彩票 API 数据平台", page_icon="🎰", layout="wide")
    st.title("🎰 综合真实彩票 API 与代理隧道穿透平台")
    st.caption("运行机制：全网多源 API 轮询 + 代理隧道穿透防护 | 绝不提供离线假数据")
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
        btn = st.button("🚀 启动网络穿透获取真实开奖", type="primary", use_container_width=True)

    with col2:
        if btn:
            with st.spinner("正在通过安全代理隧道连接全网彩票服务器..."):
                res = RealLotteryEngine.analyze(lottery_choice, history_count)

                if "error" not in res:
                    st.success(f"✅ **真实 API 获取成功！** 彩种：**{res['彩种名称']}** | 期号：第 **{res['最新期号']}** 期")
                    st.markdown(f"### 📢 官方同步开奖号码\n> **{res['真实开奖结果']}**")
                    st.markdown("---")
                    st.subheader("📊 详细数据与热码分析")
                    st.json(res)
                else:
                    st.error(res["error"])

if __name__ == "__main__":
    main()
