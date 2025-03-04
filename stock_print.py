import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, time
import FinanceDataReader as fdr
import plotly.graph_objects as go
import plotly.express as px

# 📌 가장 최근 거래일을 구하는 함수
def get_recent_trading_day():
    today = datetime.now()
    if today.hour < 9:
        today -= timedelta(days=1)
    while today.weekday() in [5, 6]:  
        today -= timedelta(days=1)
    return today.strftime('%Y-%m-%d')

# 📌 기업명으로부터 증권 코드를 찾는 함수 (KRX 기준)
def get_ticker(company):
    try:
        listing = fdr.StockListing('KRX')
        ticker_row = listing[listing["Name"].str.strip() == company.strip()]
        if not ticker_row.empty:
            return str(ticker_row.iloc[0]["Code"]).zfill(6)  # KRX용 티커 반환
        return None
    except Exception as e:
        st.error(f"티커 조회 중 오류 발생: {e}")
        return None

# 📌 네이버 Fchart API에서 분봉 데이터 가져오기
def get_naver_fchart_minute_data(stock_code, minute="1", days=1):
    now = datetime.now()

    if now.hour < 9:
        now -= timedelta(days=1)

    while True:
        target_date = now.strftime("%Y-%m-%d") if days == 1 else None
        url = f"https://fchart.stock.naver.com/sise.nhn?symbol={stock_code}&timeframe=minute&count={days * 78}&requestType=0"
        response = requests.get(url)

        if response.status_code != 200:
            return pd.DataFrame()  # 요청 실패 시 빈 데이터 반환

        soup = BeautifulSoup(response.text, "lxml")

        data_list = []
        for item in soup.find_all("item"):
            values = item["data"].split("|")
            if len(values) < 6:
                continue

            time_str, _, _, _, close, _ = values
            if close == "null":
                continue

            time_val = datetime.strptime(time_str, "%Y%m%d%H%M")
            close = float(close)

            if target_date:
                if time_val.strftime("%Y-%m-%d") == target_date:
                    data_list.append([time_val, close])
            else:
                data_list.append([time_val, close])

        df = pd.DataFrame(data_list, columns=["시간", "종가"])

        # 📌 ✅ 9시 ~ 15시 30분 데이터만 필터링
        df["시간"] = pd.to_datetime(df["시간"])
        df = df[(df["시간"].dt.time >= time(9, 0)) & (df["시간"].dt.time <= time(15, 30))]

        if df.empty:
            now -= timedelta(days=1)
            while now.weekday() in [5, 6]:  
                now -= timedelta(days=1)
        else:
            break  # 데이터를 찾았으면 반복 종료

    return df

# 📌 FinanceDataReader를 통해 일별 시세를 가져오는 함수
def get_daily_stock_data_fdr(ticker, period):
    try:
        end_date = get_recent_trading_day()
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(
            days=30 if period == "1month" else 365)).strftime('%Y-%m-%d')
        df = fdr.DataReader(ticker, start_date, end_date)
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        df["Date"] = pd.to_datetime(df["Date"])
        df = df[df["Date"].dt.weekday < 5].reset_index(drop=True)  # ✅ 주말 데이터 제거
        return df
    except Exception as e:
        st.error(f"FinanceDataReader 데이터 불러오기 오류: {e}")
        return pd.DataFrame()

# 📌 Streamlit UI
st.title("📈 국내 주식 분봉 & 일별 차트 조회")
st.write("네이버 금융 & FinanceDataReader에서 데이터를 가져와 시각화합니다.")

stock_name = st.text_input("기업명 입력 (예: 삼성전자)", "삼성전자")

if stock_name:
    stock_code = get_ticker(stock_name)
    if stock_code:
        st.write(f"✅ 종목 코드: {stock_code}")
    else:
        st.error("❌ 해당 기업의 종목 코드를 찾을 수 없습니다.")

# 📌 `1 Day` & `Week` 버튼 UI
col1, col2 = st.columns(2)
with col1:
    day_selected = st.button("📅 1 Day")
with col2:
    week_selected = st.button("📆 Week")

# 📌 `1 Month` & `1 Year` 버튼 UI 추가
col3, col4 = st.columns(2)
with col3:
    month_selected = st.button("📆 1 Month")
with col4:
    year_selected = st.button("📆 1 Year")

# 📌 버튼 클릭 여부에 따라 데이터 가져오기
if stock_code:
    if day_selected or week_selected:
        df = get_naver_fchart_minute_data(stock_code, "1" if day_selected else "5", 1 if day_selected else 7)

        if df.empty:
            st.error("❌ 데이터를 불러오지 못했습니다.")
        else:
            # 📌 📊 가격 차트 (분봉 - 선 그래프)
            fig = px.line(df, x="시간", y="종가", title=f"{stock_name} {'1 Day' if day_selected else 'Week'}")
            fig.update_xaxes(type="category")
            st.plotly_chart(fig)

    # 📌 `1 Month` & `1 Year` 캔들차트 (버튼 클릭 시)
    if month_selected or year_selected:
        period = "1month" if month_selected else "1year"
        daily_df = get_daily_stock_data_fdr(stock_code, period)

        if not daily_df.empty:
            st.write(daily_df)

            # 📊 캔들차트 생성 (일별 데이터 전용)
            fig_candle = go.Figure(data=[
                go.Candlestick(
                    x=daily_df["Date"],
                    open=daily_df["Open"],
                    high=daily_df["High"],
                    low=daily_df["Low"],
                    close=daily_df["Close"],
                    increasing_line_color="red",  # 상승: 빨간색
                    decreasing_line_color="blue"  # 하락: 파란색
                )
            ])

            fig_candle.update_layout(
                title=f"{stock_name} {period} 기간 캔들차트",
                xaxis_title="날짜",
                yaxis_title="주가 (KRW)",
                xaxis_rangeslider_visible=False  # X축 아래 슬라이더 제거
            )

            st.plotly_chart(fig_candle)
        else:
            st.error("❌ 일별 데이터를 불러오지 못했습니다.")
