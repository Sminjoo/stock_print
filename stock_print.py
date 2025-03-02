import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup

def get_naver_fchart_minute_data(stock_code, minute="5", days=5):
    """
    네이버 금융 Fchart API에서 분봉 데이터를 가져와서 DataFrame으로 변환
    """
    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={stock_code}&timeframe=minute&count={days * 78}&requestType=0"
    response = requests.get(url)
    
    if response.status_code != 200:
        return pd.DataFrame()  # 요청 실패 시 빈 데이터 반환
    
    soup = BeautifulSoup(response.text, "lxml")  # ✅ XML 파싱 오류 해결

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

        data_list.append([time, close, volume])

    df = pd.DataFrame(data_list, columns=["시간", "종가", "거래량"])
    return df


# 📌 Streamlit UI
st.title("📈 국내 주식 분봉 차트 조회")
st.write("네이버 금융에서 주식 분봉 데이터를 가져와 시각화합니다.")

stock_code = st.text_input("종목 코드 입력 (예: 삼성전자 005930)", "005930")
minute = st.selectbox("분봉 선택", ["1", "3", "5", "10", "30", "60"], index=2)
days = st.slider("데이터 기간 (일)", 1, 10, 5)

if st.button("📊 데이터 가져오기"):
    st.write(f"🔍 **{stock_code} | {minute}분봉 | 최근 {days}일 데이터 조회 중...**")
    
    df = get_naver_fchart_minute_data(stock_code, minute, days)

    if df.empty:
        st.error("❌ 데이터를 불러오지 못했습니다. 종목 코드를 확인하세요.")
    else:
        st.success(f"✅ {stock_code} {minute}분봉 데이터 조회 완료!")
        st.write(df.head())

        import plotly.express as px
        fig = px.line(df, x="시간", y="종가", title=f"{stock_code} {minute}분봉 차트")
        st.plotly_chart(fig)

        fig_vol = px.bar(df, x="시간", y="거래량", title=f"{stock_code} 거래량 변화")
        st.plotly_chart(fig_vol)
