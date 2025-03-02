import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
import datetime
import plotly.express as px

# 📌 네이버 fchart API에서 분봉 데이터 가져오기
def get_naver_fchart_minute_data(stock_code, minute="1", days=1):
    """
    네이버 금융 Fchart API에서 분봉 데이터를 가져와서 DataFrame으로 변환
    """
    # 📌 현재 시간 가져오기
    now = datetime.datetime.now()
    
    # 📌 아침 9시 이전이면 전날 데이터 가져오기
    if now.hour < 9:
        now -= datetime.timedelta(days=1)
    
    # 📌 주말이면 금요일 데이터 가져오기
    if now.weekday() == 6:  # 일요일
        now -= datetime.timedelta(days=2)  # 금요일로 이동
    elif now.weekday() == 5:  # 토요일
        now -= datetime.timedelta(days=1)  # 금요일로 이동

    # 📌 기준 날짜 (1 Day 모드에서만 사용)
    target_date = now.strftime("%Y-%m-%d") if days == 1 else None
    st.write(f"📅 **가져올 데이터 기간: {target_date if target_date else '최근 7일'}**")

    # 📌 분봉 설정 (1분봉 or 5분봉)
    timeframe = "minute1" if minute == "1" else "minute5"

    # 📌 네이버 Fchart API 요청
    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={stock_code}&timeframe={timeframe}&count={days * 78}&requestType=0"
    response = requests.get(url)

    if response.status_code != 200:
        return pd.DataFrame()  # 요청 실패 시 빈 데이터 반환
    
    soup = BeautifulSoup(response.text, "lxml")  # ✅ XML 파싱

    data_list = []
    for item in soup.find_all("item"):
        values = item["data"].split("|")
        if len(values) < 6:
            continue

        time, _, _, _, close, _ = values  # ✅ 종가(close)만 사용 (거래량 삭제)
        if close == "null":
            continue
        
        time = pd.to_datetime(time, format="%Y%m%d%H%M")
        close = float(close)

        # 📌 1 Day 모드일 때만 날짜 필터링
        if target_date:
            if time.strftime("%Y-%m-%d") == target_date:
                data_list.append([time, close])
        else:
            data_list.append([time, close])  # ✅ Week 모드에서는 전체 추가

    df = pd.DataFrame(data_list, columns=["시간", "종가"])
    
    # 📌 ✅ 9시 ~ 15시 30분 데이터만 필터링 (Week 모드에서도 적용)
    df["시간"] = pd.to_datetime(df["시간"])
    df = df[(df["시간"].dt.time >= datetime.time(9, 0)) & (df["시간"].dt.time <= datetime.time(15, 30))]

    # 📌 Week 모드일 경우, 데이터 없는 날 제거
    if days == 7:
        df["날짜"] = df["시간"].dt.date  # 날짜 컬럼 추가
        unique_dates = df["날짜"].unique()
        st.write(f"📆 **데이터 포함된 날짜:** {unique_dates}")

    # 📌 X축을 문자형으로 변환 (빈 데이터 없이 연속된 데이터만 표시)
    df["시간"] = df["시간"].astype(str)

    return df

# 📌 Streamlit UI
st.title("📈 국내 주식 분봉 차트 조회 (1 Day / Week)")
st.write("네이버 금융에서 주식 분봉 데이터를 가져와 시각화합니다.")

stock_code = st.text_input("종목 코드 입력 (예: 삼성전자 005930)", "005930")

# 📌 `1 Day` & `Week` 버튼 UI
col1, col2 = st.columns(2)
with col1:
    day_selected = st.button("📅 1 Day (1분봉)")
with col2:
    week_selected = st.button("📆 Week (5분봉)")

# 📌 버튼 클릭 여부에 따라 데이터 가져오기
if day_selected or week_selected:
    if day_selected:
        st.write("🔍 **1 Day 모드: 1분봉 데이터 가져오는 중...**")
        df = get_naver_fchart_minute_data(stock_code, "1", 1)  # 1분봉, 하루치
    else:
        st.write("🔍 **Week 모드: 5분봉 데이터 가져오는 중...**")
        df = get_naver_fchart_minute_data(stock_code, "5", 7)  # 5분봉, 7일치

    if df.empty:
        st.error("❌ 데이터를 불러오지 못했습니다. 종목 코드를 확인하세요.")
    else:
        st.success(f"✅ {stock_code} 데이터 조회 완료!")
        st.write(df.head())

        # 📌 📊 가격 차트 (X축을 문자형으로 설정하여 데이터 없는 날 제외)
        fig = px.line(df, x="시간", y="종가", title=f"{stock_code} {'1분봉 (1 Day)' if day_selected else '5분봉 (Week)'}")
        fig.update_xaxes(type="category")  # ✅ X축을 카테고리(문자형)로 설정
        st.plotly_chart(fig)
