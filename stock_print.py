import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# 네이버 금융 크롤링 함수
def get_naver_minute_chart(stock_code, minute="5", days=5):
    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={stock_code}&timeframe=minute&count={days * 78}&requestType=0"
    response = requests.get(url)
    data = response.text.split("\n")[3:-2]

    chart_data = []
    for row in data:
        values = row.split("|")
        if len(values) < 6:
            continue
        time, open_, high, low, close, volume = values
        chart_data.append([time, float(open_), float(high), float(low), float(close), int(volume)])

    df = pd.DataFrame(chart_data, columns=['시간', '시가', '고가', '저가', '종가', '거래량'])
    df['시간'] = pd.to_datetime(df['시간'], format='%Y%m%d%H%M')
    return df

# Streamlit UI
st.title("📈 국내 주식 분봉 차트")
stock_code = st.text_input("종목 코드 입력 (예: 삼성전자 005930)", "005930")
minute = st.selectbox("분봉 선택", ["3", "5", "10", "30", "60"])
days = st.slider("데이터 기간 (일)", 1, 5, 3)

if st.button("데이터 가져오기"):
    df = get_naver_minute_chart(stock_code, minute, days)
    st.write(df.head())  # 데이터 확인

    # Plotly를 이용한 차트 그리기
    fig = px.line(df, x='시간', y='종가', title=f"{stock_code} {minute}분봉 차트")
    st.plotly_chart(fig)
