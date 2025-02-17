import streamlit as st
import requests
import time
import mplfinance as mpf
import FinanceDataReader as fdr
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import os
import plotly.graph_objects as go  # ✅ Plotly 추가

# ✅ 1. 최근 거래일 찾기 함수
def get_recent_trading_day():
    today = datetime.now()
    if today.hour < 9:  # 오전 9시 이전이면 전날을 기준으로
        today -= timedelta(days=1)

    # 주말 및 공휴일 고려하여 가장 최근의 거래일 찾기
    while today.weekday() in [5, 6]:  # 토요일(5), 일요일(6)이면 하루씩 감소
        today -= timedelta(days=1)

    return today.strftime('%Y-%m-%d')

# ✅ 2. 메인 실행 함수
def main():
    st.set_page_config(page_title="Stock Price Visualization", page_icon=":chart_with_upwards_trend:")
    st.title("_주가 시각화_ :chart_with_upwards_trend:")

    # ✅ 세션 상태 초기화
    if "company_name" not in st.session_state:
        st.session_state.company_name = ""
    if "selected_period" not in st.session_state:
        st.session_state.selected_period = "1day"

    with st.sidebar:
        company_name = st.text_input("분석할 기업명 (코스피 상장)", st.session_state.company_name)
        process = st.button("검색")

    if process and company_name:
        st.session_state.company_name = company_name

    # ✅ 기업명이 입력되었을 경우만 실행
    if st.session_state.company_name:
        st.subheader(f"📈 {st.session_state.company_name} 최근 주가 추이")

        # ✅ 기간 선택 버튼
        selected_period = st.radio(
            "기간 선택",
            options=["1day", "week", "1month", "1year"],
            horizontal=True,
            index=["1day", "week", "1month", "1year"].index(st.session_state.selected_period)
        )

        if selected_period != st.session_state.selected_period:
            st.session_state.selected_period = selected_period

        st.write(f"🔍 선택된 기간: {st.session_state.selected_period}")

        # ✅ 주가 데이터 가져오기
        with st.spinner(f"📊 {st.session_state.company_name} ({st.session_state.selected_period}) 데이터 불러오는 중..."):
            ticker = get_ticker(st.session_state.company_name)
            if not ticker:
                st.error("해당 기업의 티커 코드를 찾을 수 없습니다.")
                return

            st.write(f"✅ 가져온 티커 코드: {ticker}")

            df = None
            try:
                if st.session_state.selected_period in ["1day", "week"]:
                    df = get_intraday_data_bs(ticker, st.session_state.selected_period)
                else:
                    df = get_daily_stock_data(ticker, st.session_state.selected_period)

                if df is None or df.empty:
                    st.warning(f"📉 {st.session_state.company_name} ({ticker}) - 해당 기간({st.session_state.selected_period})의 거래 데이터가 없습니다.")
                else:
                    plot_stock_plotly(df, st.session_state.company_name, st.session_state.selected_period)

            except Exception as e:
                st.error(f"주가 데이터를 불러오는 중 오류 발생: {e}")

# ✅ 3. 주가 시각화 & 티커 조회 함수
def get_ticker(company):
    try:
        listing = fdr.StockListing('KRX')
        if listing.empty:
            listing = fdr.StockListing('KOSPI')
        
        if listing.empty:
            st.error("상장 기업 정보를 불러올 수 없습니다.")
            return None

        for name_col, ticker_col in [("Name", "Code"), ("Name", "Symbol"), ("기업명", "종목코드")]:
            if name_col in listing.columns and ticker_col in listing.columns:
                ticker_row = listing[listing[name_col].str.strip() == company.strip()]
                if not ticker_row.empty:
                    return str(ticker_row.iloc[0][ticker_col]).zfill(6)

        st.error(f"'{company}'에 해당하는 티커 정보를 찾을 수 없습니다.")
        return None

    except Exception as e:
        st.error(f"티커 조회 중 오류 발생: {e}")
        return None

# ✅ 4. 네이버 금융 시간별 시세 크롤링 함수 (1일/1주)
def get_intraday_data_bs(ticker, period):
    base_url = f"https://finance.naver.com/item/sise_time.naver?code={ticker}&page="
    headers = {"User-Agent": "Mozilla/5.0"}

    prices = []
    times = []
    page = 1

    recent_trading_day = get_recent_trading_day()

    while True:
        url = base_url + str(page)
        res = requests.get(url, headers=headers)
        time.sleep(1)

        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.select("table.type2 tr")

        if not rows or "체결시각" in rows[0].text:
            break

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 2:
                continue  

            try:
                time_str = cols[0].text.strip()
                close_price = int(cols[1].text.replace(",", ""))

                times.append(time_str)
                prices.append(close_price)

            except ValueError:
                continue

        page += 1

    if not prices:
        return pd.DataFrame()

    df = pd.DataFrame({"Time": times, "Close": prices})
    df["Date"] = recent_trading_day
    df["Datetime"] = pd.to_datetime(df["Date"] + " " + df["Time"])
    df.set_index("Datetime", inplace=True)

    return df

# ✅ 5. FinanceDataReader를 통한 일별 시세 크롤링 함수 (1개월/1년)
def get_daily_stock_data(ticker, period):
    end_date = get_recent_trading_day()
    start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=30 if period == "1month" else 365)).strftime('%Y-%m-%d')
    df = fdr.DataReader(ticker, start_date, end_date)
    return df

# ✅ 6. Plotly를 이용한 주가 시각화 함수
def plot_stock_plotly(df, company, period):
    if df is None or df.empty:
        st.warning(f"📉 {company} - 해당 기간({period})의 거래 데이터가 없습니다.")
        return

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["Close"],
        mode="lines+markers",
        line=dict(color="royalblue", width=2),
        marker=dict(size=5),
        name="체결가"
    ))

    fig.update_layout(
        title=f"{company} 주가 ({period})",
        xaxis_title="시간" if period in ["1day", "week"] else "날짜",
        yaxis_title="주가 (체결가)",
        template="plotly_white",
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True),
        hovermode="x unified"
    )

    st.plotly_chart(fig)

# ✅ 실행
if __name__ == '__main__':
    main()

