import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import pandas as pd
import requests
from bs4 import BeautifulSoup

# ✅ 1. 최근 거래일 찾기 함수
def get_recent_trading_day():
    today = datetime.now()
    if today.hour < 9:
        today -= timedelta(days=1)

    while today.weekday() in [5, 6]:  # 토요일(5), 일요일(6)이면 하루씩 감소
        today -= timedelta(days=1)

    return today.strftime('%Y-%m-%d')

# ✅ 2. 티커 조회 함수 (야후 & FinanceDataReader)
def get_ticker(company, source="yahoo"):
    try:
        listing = fdr.StockListing('KRX')
        ticker_row = listing[listing["Name"].str.strip() == company.strip()]
        if not ticker_row.empty:
            krx_ticker = str(ticker_row.iloc[0]["Code"]).zfill(6)
            if source == "yahoo":
                return krx_ticker + ".KS"  # ✅ 야후 파이낸스용 티커 변환
            return krx_ticker  # ✅ FinanceDataReader용 티커
        return None

    except Exception as e:
        st.error(f"티커 조회 중 오류 발생: {e}")
        return None

# ✅ 3. 네이버 금융에서 'thistime' 값을 가져오기
def get_thistime_value(ticker):
    url = f"https://finance.naver.com/item/sise.naver?code={ticker}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        script_tags = soup.find_all("script")
        for script in script_tags:
            if "thistime" in script.text:
                lines = script.text.split("\n")
                for line in lines:
                    if "thistime" in line:
                        thistime_value = line.split("=")[-1].strip().replace(";", "").replace("'", "")
                        return thistime_value
        return None

    except requests.exceptions.RequestException as e:
        st.error(f"❌ 네이버 금융 데이터 요청 실패: {e}")
        return None

# ✅ 4. 네이버 금융에서 분봉 데이터 가져오기 (1day, week)
def get_intraday_data_naver(ticker):
    thistime_value = get_thistime_value(ticker)
    if not thistime_value:
        st.error("❌ 'thistime' 값을 가져오지 못했습니다.")
        return pd.DataFrame()

    url = f"https://finance.naver.com/item/sise_time.naver?code={ticker}&thistime={thistime_value}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        table = soup.find("table", class_="type2")
        if table is None:
            st.error("❌ 네이버 금융에서 데이터를 찾을 수 없습니다.")
            return pd.DataFrame()

        df = pd.read_html(str(table), encoding="euc-kr")[0]

        df = df.rename(columns={"체결시간": "Date", "체결가": "Close"})
        df = df[["Date", "Close"]].dropna()

        df["Date"] = pd.to_datetime(df["Date"], format="%H:%M").dt.strftime("%H:%M")

        return df

    except requests.exceptions.RequestException as e:
        st.error(f"❌ 네이버 금융 데이터 요청 실패: {e}")
        return pd.DataFrame()

# ✅ 5. FinanceDataReader를 통한 일별 시세 (1month, 1year)
def get_daily_stock_data_fdr(ticker, period):
    try:
        end_date = get_recent_trading_day()
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=30 if period == "1month" else 365)).strftime('%Y-%m-%d')
        df = fdr.DataReader(ticker, start_date, end_date)

        if df.empty:
            return pd.DataFrame()

        df = df.reset_index()
        df = df.rename(columns={"Date": "Date", "Close": "Close"})

        df["Date"] = pd.to_datetime(df["Date"])
        df = df[df["Date"].dt.weekday < 5].reset_index(drop=True)

        return df
    except Exception as e:
        st.error(f"FinanceDataReader 데이터 불러오기 오류: {e}")
        return pd.DataFrame()

# ✅ 6. Streamlit 메인 실행 함수
def main():
    st.set_page_config(page_title="Stock Price Visualization", page_icon=":chart_with_upwards_trend:")
    st.title("_주가 시각화_ :chart_with_upwards_trend:")

    if "company_name" not in st.session_state:
        st.session_state.company_name = ""
    if "selected_period" not in st.session_state:
        st.session_state.selected_period = "1day"

    with st.sidebar:
        company_name = st.text_input("분석할 기업명 (코스피 상장)", st.session_state.company_name)
        process = st.button("검색")

    if process and company_name:
        st.session_state.company_name = company_name

    if st.session_state.company_name:
        st.subheader(f"📈 {st.session_state.company_name} 최근 주가 추이")

        selected_period = st.radio(
            "기간 선택",
            options=["1day", "week", "1month", "1year"],
            horizontal=True,
            index=["1day", "week", "1month", "1year"].index(st.session_state.selected_period)
        )

        if selected_period != st.session_state.selected_period:
            st.session_state.selected_period = selected_period

        st.write(f"🔍 선택된 기간: {st.session_state.selected_period}")

        with st.spinner(f"📊 {st.session_state.company_name} ({st.session_state.selected_period}) 데이터 불러오는 중..."):
            ticker = get_ticker(st.session_state.company_name, source="fdr")  # ✅ 네이버 금융 & FDR 티커 사용
            if not ticker:
                st.error("해당 기업의 티커 코드를 찾을 수 없습니다.")
                return

            if selected_period in ["1day", "week"]:
                df = get_intraday_data_naver(ticker)
            else:
                df = get_daily_stock_data_fdr(ticker, selected_period)

            if df.empty:
                st.warning(f"📉 {st.session_state.company_name} - 해당 기간({st.session_state.selected_period})의 거래 데이터가 없습니다.")
            else:
                plot_stock_plotly(df, st.session_state.company_name, st.session_state.selected_period)

# ✅ 실행
if __name__ == '__main__':
    main()
