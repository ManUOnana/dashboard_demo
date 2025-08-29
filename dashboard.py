# dashboard.py
import requests, json, pandas as pd
import plotly.express as px
import streamlit as st
from datetime import date, timedelta

# ==========================
# 1. API 키 (네이버 개발자센터에서 발급받은 값 넣기)
# ==========================
CLIENT_ID = "CvAfxF6YbltarCjZGqMT"
CLIENT_SECRET = "ukaSo5cwr6"

url = "https://openapi.naver.com/v1/datalab/search"
headers = {
    "X-Naver-Client-Id": CLIENT_ID,
    "X-Naver-Client-Secret": CLIENT_SECRET,
    "Content-Type": "application/json"
}

# ==========================
# 2. 원석 후보군 (16종 + 브랜드)
# ==========================
stones = {
    "호안석": ["호안석","호랑이눈","tiger eye"],
    "자수정": ["자수정","amethyst"],
    "오닉스": ["오닉스","흑수정","onyx"],
    "가넷": ["가넷","garnet"],
    "터키석": ["터키석","turquoise"],
    "크리스탈": ["크리스탈","수정","rock crystal"],
    "장미수정": ["장미수정","로즈쿼츠","rose quartz"],
    "진주": ["진주","pearl"],
    "라피스라줄리": ["라피스라줄리","lapis lazuli","청금석"],
    "시트린": ["시트린","citrine"],
    "루비": ["루비","ruby"],
    "투어마린": ["투어마린","tourmaline"],
    "페리도트": ["페리도트","peridot"],
    "아벤츄린": ["아벤츄린","aventurine"],
    "카넬리안": ["카넬리안","carnelian"],
    "아쿠아마린": ["아쿠아마린","aquamarine"],
    "리코맨즈": ["리코맨즈"]
}

# ==========================
# 3. 데이터 수집
# ==========================
end = date.today()
start = end - timedelta(days=365)

def fetch_group(group_dict):
    body = {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "timeUnit": "date",
        "keywordGroups": [{"groupName":k, "keywords":v} for k,v in group_dict.items()]
    }
    res = requests.post(url, headers=headers, data=json.dumps(body))
    res.raise_for_status()
    return res.json()

# 분할 호출 (최대 5개 제한)
keys = list(stones.keys())
rows = []
for i in range(0, len(keys), 5):
    part = {k: stones[k] for k in keys[i:i+5]}
    js = fetch_group(part)
    for r in js["results"]:
        stone = r["title"]
        for d in r["data"]:
            rows.append({"stone": stone, "date": d["period"], "ratio": d["ratio"]})

df = pd.DataFrame(rows)
df["date"] = pd.to_datetime(df["date"])

# ==========================
# 4. 대시보드 레이아웃
# ==========================
st.set_page_config(page_title="리코맨즈 원석 트렌드 대시보드", layout="wide")
st.title("리코맨즈 원석 트렌드 분석")

# ----------------------------------
# 현재 트렌드 TOP5
latest = df.groupby("stone").tail(1)
top5 = latest.sort_values("ratio", ascending=False).head(5)
fig1 = px.bar(top5, x="stone", y="ratio", title="현재 검색량 Top5 원석")
st.plotly_chart(fig1, use_container_width=True)

# ----------------------------------
# 치고 올라오는 원석
df["avg_7d"] = df.groupby("stone")["ratio"].transform(lambda x: x.rolling(7).mean())
df["avg_28d"] = df.groupby("stone")["ratio"].transform(lambda x: x.rolling(28).mean())
latest2 = df.groupby("stone").tail(1)
latest2["rise_score"] = ((latest2["avg_7d"] - latest2["avg_28d"]) / latest2["avg_28d"] * 100).round(2)
rising = latest2.sort_values("rise_score", ascending=False).head(5)
fig2 = px.bar(rising, x="stone", y="rise_score", title="최근 28일 대비 7일 상승률 Top5")
st.plotly_chart(fig2, use_container_width=True)

# ----------------------------------
# 브랜드 검색량 추이 (리코맨즈)
brand = df[df["stone"]=="리코맨즈"]
fig3 = px.line(brand, x="date", y="ratio", title="리코맨즈 검색량 추이")
st.plotly_chart(fig3, use_container_width=True)

# ----------------------------------
# 시즌성 패턴 (월별 평균)
st.header("📌 시즌성 패턴")
sel = st.selectbox("원석 선택", df["stone"].unique())
seasonality = df.copy()
seasonality["month"] = seasonality["date"].dt.to_period("M")
seasonality = seasonality.groupby(["stone","month"])["ratio"].mean().reset_index()
seasonality["month"] = seasonality["month"].astype(str)
fig4 = px.line(seasonality[seasonality["stone"]==sel], x="month", y="ratio", title=f"{sel} 월별 평균 검색량")
st.plotly_chart(fig4, use_container_width=True)

# ----------------------------------
# 안정성 지표
stab = df.groupby("stone")["ratio"].agg(["mean","std"])
stab["cv"] = (stab["std"]/stab["mean"]).round(2)
stable = stab.sort_values("cv").head(5).reset_index()
unstable = stab.sort_values("cv", ascending=False).head(5).reset_index()

st.subheader("📌 안정성 지표")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**꾸준한 원석 Top5**")
    st.dataframe(stable)
with col2:
    st.markdown("**변동성 높은 원석 Top5**")
    st.dataframe(unstable)

# ----------------------------------
# 검색 시장 점유율
latest3 = df.groupby("stone").tail(1)
latest3["share"] = (latest3["ratio"]/latest3["ratio"].sum()*100).round(2)
fig5 = px.pie(latest3, names="stone", values="share", title="검색 시장 점유율")
st.plotly_chart(fig5, use_container_width=True)
