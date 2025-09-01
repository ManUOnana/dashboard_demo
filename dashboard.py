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
# 2. 원석 후보군 (16종)
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
    "아쿠아마린": ["아쿠아마린","aquamarine"]
}

# 브랜드 따로 정의
brand_keywords = {"리코맨즈": ["리코맨즈"]}

# ==========================
# 3. 데이터 수집 함수
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

# ----- 원석 데이터 -----
keys = list(stones.keys())
rows = []
for i in range(0, len(keys), 5):  # 5개씩 분할 호출
    part = {k: stones[k] for k in keys[i:i+5]}
    js = fetch_group(part)
    for r in js["results"]:
        stone = r["title"]
        for d in r["data"]:
            rows.append({"원석": stone, "날짜": d["period"], "검색량지수": d["ratio"]})

df = pd.DataFrame(rows)
df["날짜"] = pd.to_datetime(df["날짜"])

# ----- 브랜드 데이터 -----
brand_rows = []
js_brand = fetch_group(brand_keywords)
for r in js_brand["results"]:
    brand = r["title"]
    for d in r["data"]:
        brand_rows.append({"브랜드": brand, "날짜": d["period"], "검색량지수": d["ratio"]})

df_brand = pd.DataFrame(brand_rows)
df_brand["날짜"] = pd.to_datetime(df_brand["날짜"])

# ==========================
# 4. 추가 지표 계산
# ==========================
# 최근 평균
df["최근7일평균"] = df.groupby("원석")["검색량지수"].transform(lambda x: x.rolling(7).mean())
df["최근28일평균"] = df.groupby("원석")["검색량지수"].transform(lambda x: x.rolling(28).mean())

latest2 = df.groupby("원석").tail(1)
latest2["상승률(%)"] = ((latest2["최근7일평균"] - latest2["최근28일평균"]) / latest2["최근28일평균"] * 100).round(2)

# 안정성 지표
stab = df.groupby("원석")["검색량지수"].agg(평균검색량="mean", 표준편차="std")
stab["변동계수"] = (stab["표준편차"] / stab["평균검색량"]).round(2)

stable = stab.sort_values("변동계수").head(5).reset_index()
unstable = stab.sort_values("변동계수", ascending=False).head(5).reset_index()

# 시장 점유율
latest3 = df.groupby("원석").tail(1)
latest3["시장점유율(%)"] = (latest3["검색량지수"] / latest3["검색량지수"].sum() * 100).round(2)

# ==========================
# 5. 값 소수점 자리 제한
# ==========================
num_cols = ["검색량지수","최근7일평균","최근28일평균","상승률(%)","평균검색량","표준편차","변동계수","시장점유율(%)"]

for col in num_cols:
    if col in df.columns:
        df[col] = df[col].round(2)
    if col in df_brand.columns:
        df_brand[col] = df_brand[col].round(2)
    if col in latest2.columns:
        latest2[col] = latest2[col].round(2)

# ==========================
# 6. 대시보드 레이아웃
# ==========================
st.set_page_config(page_title="리코맨즈 원석 트렌드 대시보드", layout="wide")
st.title("리코맨즈 원석 트렌드 분석")

# 원석별 최신 데이터 (여기서 미리 정의)
latest = df.groupby("원석").tail(1)

# ----------------------------------
# 현재 트렌드 TOP5 + 검색 시장 점유율 (한 줄 배치)
st.subheader(" 현재 검색 현황(어제 기준)")
col1, col2 = st.columns(2)

with col1:
    top5 = latest.sort_values("검색량지수", ascending=False).head(5)
    fig1 = px.bar(top5, x="원석", y="검색량지수", title="검색량 Top5 원석")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    fig5 = px.pie(latest3, names="원석", values="시장점유율(%)", title="검색 시장 점유율")
    st.plotly_chart(fig5, use_container_width=True)

# ----------------------------------
# 어제 기준 Top 원석 장기 추세 (이동평균, 기본 1위 원석)
st.subheader(" 어제 기준 Top 원석 장기 추세 (이동평균)")

# Top5 원석 리스트 (어제 기준)
top5_names = top5["원석"].tolist()

# 현재 1위 원석 (top5의 첫 번째 행)
first_rank = top5.iloc[0]["원석"]

# 원석 선택 (기본값 = 1위 원석)
selected_stone = st.selectbox(
    "원석 선택 (어제 기준 Top5)", 
    options=top5_names, 
    index=0  # 첫 번째(=현재 1위 원석) 기본 선택
)

# 이동평균 기간 선택 (토글 느낌)
ma_option = st.radio(
    "이동평균 기간", 
    options=[7, 28], 
    index=0, 
    horizontal=True
)

# 선택된 원석 데이터 필터링
df_selected = df[df["원석"] == selected_stone].copy()
df_selected[f"검색량_{ma_option}일평균"] = (
    df_selected["검색량지수"].rolling(ma_option).mean()
)

# 라인 차트 (이동평균만 표시)
fig = px.line(
    df_selected,
    x="날짜",
    y=f"검색량_{ma_option}일평균",
    title=f"{selected_stone} 검색량 {ma_option}일 이동평균 추이"
)

st.plotly_chart(fig, use_container_width=True)


# ----------------------------------
# 치고 올라오는 원석
rising = latest2.sort_values("상승률(%)", ascending=False).head(5)
fig2 = px.bar(rising, x="원석", y="상승률(%)", title="최근 주간 검색량 급상승 Top5")
st.plotly_chart(fig2, use_container_width=True)

# ----------------------------------
# 시즌성 패턴 (월별 평균)
st.header(" 시즌성 패턴")
sel = st.selectbox("원석 선택", df["원석"].unique())
seasonality = df.copy()
seasonality["월"] = seasonality["날짜"].dt.to_period("M")
seasonality = seasonality.groupby(["원석","월"])["검색량지수"].mean().reset_index()
seasonality["월"] = seasonality["월"].astype(str)
fig4 = px.line(seasonality[seasonality["원석"]==sel], x="월", y="검색량지수", title=f"{sel} 월별 평균 검색량")
st.plotly_chart(fig4, use_container_width=True)

# ----------------------------------
# 안정성 지표
st.subheader(" 안정성 지표")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**꾸준한 원석 Top5**")
    st.dataframe(stable)
with col2:
    st.markdown("**변동성 높은 원석 Top5**")
    st.dataframe(unstable)

# ----------------------------------
# 브랜드 비교 섹션
st.header("브랜드 검색량 변화 비교")  # 메인 섹션 제목 (굵고 크게)

st.markdown("리코맨즈 브랜드 검색량의 변화를 확인합니다. "
            "특정 시점(이벤트, 시즌, 개선 전후 등)과 비교 분석에 활용할 수 있습니다.")

fig3 = px.line(
    df_brand,
    x="날짜",
    y="검색량지수",
    title="리코맨즈 검색량 추이"  # 그래프 안쪽 작은 제목
)
st.plotly_chart(fig3, use_container_width=True)
