import streamlit as st
import pandas as pd
import numpy as np
import requests
import random
from typing import Dict, List, Any

# ==========================================
# 1. 实时 API 动态数据抓取引擎（支持 100 期真实数据抓取）
# ==========================================
class LotteryEngine:
    """彩票数据分析引擎（实时 API 同步版）"""

    @staticmethod
    def fetch_ssq_real_data(limit: int = 100) -> List[Dict]:
        """
        从支持全球访问的开放 API 实时抓取最新双色球开奖数据（最高支持 100 期）
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }

        # 主通道：开源实时彩票 JSON 接口（支持跨国、100期抓取）
        primary_api = f"https://api.oick.cn/lottery/api.php?type=ssq&limit={limit}"
        try:
            res = requests.get(primary_api, headers=headers, timeout=8)
            if res.status_code == 200:
                data = res.json()
                raw_list = data.get("data", []) if isinstance(data, dict) else data
                results = []
                for item in raw_list[:limit]:
                    if "red" in item and "blue" in item:
                        reds = [int(x) for x in item["red"].split(",")]
                        blue = int(item["blue"])
                        results.append({"period": str(item.get("code", "")), "reds": reds, "blue": blue})
                if len(results) >= 10:
                    return results
        except Exception:
            pass

        # 备用通道 1：新浪彩票开放 RESTful 接口
        sina_api = f"https://trend.caipiao.163.com/ssq/ssq_history.json?limit={limit}"
        try:
            res = requests.get(sina_api, headers=headers, timeout=8)
            if res.status_code == 200:
                data = res.json()
                results = []
                for item in data.get("data", [])[:limit]:
                    reds = [int(x) for x in item["red"].split(",")]
                    blue = int(item["blue"])
                    results.append({"period": str(item.get("period", "")), "reds": reds, "blue": blue})
                if len(results) >= 10:
                    return results
        except Exception:
            pass

        # 备用通道 2：如果云服务器 IP 完全被封锁，提示用户
        st.error("⚠️ 所有的公共 API 节点当前均被云机房防火墙阻截，请检查网络或配置代理通道！")
        return []

    @classmethod
    def analyze_shuangseqiu(cls, history_limit: int = 100, sim_count: int = 10000) -> Dict[str, Any]:
        """双色球实时数据分析：热码统计 + 概率算法碰撞"""
        # 实时获取 API 数据
        history = cls.fetch_ssq_real_data(limit=history_limit)
        
        if not history:
            return {"error": "无法获取 API 实时数据"}

        # 1. 统计真实历史数据中的红球频次（热码）
        all_reds = [num for item in history for num in item["reds"]]
        freq = pd.Series(all_reds).value_counts()
        hot_red_pool = freq.head(15).index.tolist()
        
        if len(hot_red_pool) < 6:
            hot_red_pool = list(range(1, 34))

        # 2. 基于真实热码池进行算法推荐筛选
        recommended_reds = []
        for _ in range(sim_count):
            sample = sorted(random.sample(hot_red_pool, 6))
            odd_count = sum(1 for x in sample if x % 2 != 0)
            total_sum = sum(sample)
            
            # 筛选标准：奇偶比 (2:4 ~ 4:2) + 和值区间 (80 ~ 120)
            if 2 <= odd_count <= 4 and 80 <= total_sum <= 120:
                recommended_reds = sample
                break

        if not recommended_reds:
            recommended_reds = sorted(random.sample(hot_red_pool, 6))

        # 3. 统计蓝球真实冷热号
        all_blues = [item["blue"] for item in history]
        blue_freq = pd.Series(all_blues).value_counts()
        hot_blue = int(blue_freq.index[0]) if not blue_freq.empty else random.randint(1, 16)

        return {
            "最新期号": history[0]["period"],
            "解析历史期数": len(history),
            "高频红球池": hot_red_pool,
            "推荐红球": recommended_reds,
            "推荐蓝球": [hot_blue],
            "红球和值": sum(recommended_reds),
            "奇偶比": f"{sum(1 for x in recommended_reds if x % 2 != 0)}:{sum(1 for x in recommended_reds if x % 2 == 0)}"
        }


# ==========================================
# 2. Streamlit Web 界面渲染
# ==========================================
def main():
    st.set_page_config(
        page_title="双色球实时 API 概率分析平台",
        page_icon="🎰",
        layout="wide"
    )

    st.title("📊 双色球实时 API 数据分析与推荐")
    st.markdown("---")

    col1, col2 = st.columns([1, 2])
    
    with col1:
        history_count = st.slider("实时抓取最新历史期数", 10, 100, 100, step=10)
        sim_count = st.slider("算法迭代推算次数", 1000, 50000, 10000, step=1000)
        
        btn = st.button("🔄 连线 API 并实时计算", type="primary")

    with col2:
        if btn:
            with st.spinner(f"正在跨国请求 API 接口，读取最新 {history_count} 期真实开奖数据..."):
                res = LotteryEngine.analyze_shuangseqiu(history_count, sim_count)
                
                if "error" not in res:
                    st.success(f"✅ API 连接成功！已同步最新第 **{res['最新期号']}** 期及之前共 {res['解析历史期数']} 期真实开奖记录。")
                    st.subheader("💡 算法推荐号码（基于最新真实热码推演）")
                    st.markdown(f"### 🔴 红球：`{res['推荐红球']}` | 🔵 蓝球：`{res['推荐蓝球']}`")
                    
                    st.markdown("---")
                    st.subheader("📈 最新 100 期热码统计特征")
                    st.json({
                        "最新开奖期号": res["最新期号"],
                        "前15个高频热码池": res["高频红球池"],
                        "推荐组合和值": res["红球和值"],
                        "推荐组合奇偶比": res["奇偶比"]
                    })
                else:
                    st.error("API 数据抓取失败，请检查 API 连接。")

if __name__ == "__main__":
    main()
