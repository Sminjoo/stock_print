import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
import datetime
import plotly.express as px

# 📌 네이버 fchart API에서 분봉 데이터 가져오기
def get_naver_fchart_minute_data(stock_code, minute="5", days=1):
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

    # 📌 기준 날짜 출력 (디버깅용)
    target_date = now.strftime("%Y-%m-%d")
    st.write(f"📅 **가져올 데이터 날짜: {target_date}**")

    # 네이버 Fchart API 요청
    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={stock_code}&timeframe=minute&count={days * 78}&requestType=0"
    response = requests.get(url)
    
    if response.status_code != 200:
        return pd.DataFrame()  # 요청 실패 시 빈 데이터 반환
    
    soup = BeautifulSoup(response.text, "lxml")  # ✅ XML 파싱

    data_list = []
    for item in soup.find_all("item"):
        values = item["data"].split("|")
        if len(values) < 6:
            continue

        time, _, _, _, close, volume = values  # 종가(close)와 거래량(volume)만 사용
        if close == "null" or volume == "null":
            continue
        
        time = pd.to_datetime(time, format="%Y%m%d%H%M")
        close = float(close)
        volume = int(volume)

        # 📌 가져올 날짜의 데이터만 필터링
        if time.strftime("%Y-%m-%d") == target_date:
            data_list.append([time, close, volume])

    df = pd.DataFrame(data_list, columns=["시간", "종가", "거래량"])
    
    # 📌 ✅ 9시 ~ 15시 30분 데이터만 필터링
    df["시간"] = pd.to_datetime(df["시간"])  # ✅ datetime 변환
    df = df[(df["시간"].dt.time >= datetime.time(9, 0)) & (df["시간"].dt.time <= datetime.time(15, 30))]

    # 📌 5분봉 데이터가 맞는지 확인 (시간 간격 체크)
    if not df.empty:
        df["시간 간격"] = df["시간"].diff().dt.total_seconds() / 60  # 분 단위 차이 계산
        avg_interval = df["시간 간격"].dropna().mean()
        st.write(f"⏳ **평균 시간 간격: {avg_interval}분** (5분봉인지 확인)")
    
    # 📌 X축을 문자형으로 변환 (빈 데이터 없이 연속된 데이터만 표시)
    df["시간"] = df["시간"].astype(str)
    
    return df

# 📌 Streamlit UI
st.title("📈 국내 주식 분봉 차트 조회")
st.write("네이버 금융에서 주식 분봉 데이터를 가져와 시각화합니다.")

stock_code = st.text_input("종목 코드 입력 (예: 삼성전자 005930)", "005930")
minute = st.selectbox("분봉 선택", ["1", "3", "5", "10", "30", "60"], index=2)
days = st.slider("데이터 기간 (일)", 1, 10, 1)  # ✅ 기본값을 1일로 설정

if st.button("📊 데이터 가져오기"):
    st.write(f"🔍 **{stock_code} | {minute}분봉 | 최근 {days}일 데이터 조회 중...**")
    
    df = get_naver_fchart_minute_data(stock_code, minute, days)

    if df.empty:
        st.error("❌ 데이터를 불러오지 못했습니다. 종목 코드를 확인하세요.")
    else:
        st.success(f"✅ {stock_code} {minute}분봉 데이터 조회 완료!")
        st.write(df.head())

        # 📌 📊 가격 차트 (X축을 문자형으로 설정하여 데이터 없는 날 제외)
        fig = px.line(df, x="시간", y="종가", title=f"{stock_code} {minute}분봉 차트")
        fig.update_xaxes(type="category")  # ✅ X축을 카테고리(문자형)로 설정
        st.plotly_chart(fig)

        # 📌 거래량 막대 그래프 (X축을 문자형으로 설정)
        fig_vol = px.bar(df, x="시간", y="거래량", title=f"{stock_code} 거래량 변화")
        fig_vol.update_xaxes(type="category")  # ✅ X축을 문자형으로 설정
        st.plotly_chart(fig_vol)
