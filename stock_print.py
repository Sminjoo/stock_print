import streamlit as st
import plotly.graph_objects as go
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

# ✅ 1. 최근 거래일 찾기 함수
def get_recent_trading_day():
    today = datetime.now()
    if today.hour < 9:
        today -= timedelta(days=1)

    while today.weekday() in [5, 6]:  # 토요일(5), 일요일(6)이면 하루씩 감소
        today -= timedelta(days=1)

    return today.strftime('%Y-%m-%d')

# ✅ 2. 티커 조회 함수 (FinanceDataReader 기반)
def get_ticker(company):
    try:
        listing = fdr.StockListing('KRX')
        ticker_row = listing[listing["Name"].str.strip() == company.strip()]
        if not ticker_row.empty:
            return str(ticker_row.iloc[0]["Code"]).zfill(6)
        return None
    except Exception as e:
        st.error(f"티커 조회 중 오류 발생: {e}")
        return None

# ✅ 3. Selenium을 이용해 네이버 금융에서 'thistime' 값 가져오기
def get_thistime_value(ticker):
    url = f"https://finance.naver.com/item/sise.naver?code={ticker}"

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # GUI 없이 실행
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(url)
    time.sleep(2)  # 페이지 로딩 대기

    # 🔹 'thistime' 값이 포함된 URL 찾기
    elements = driver.find_elements(By.TAG_NAME, "a")
    thistime_value = None

    for elem in elements:
        link = elem.get_attribute("href")
        if link and "sise_time.naver" in link:
            thistime_value = link.split("thistime=")[-1]  # 'thistime' 값 추출
            break

    driver.quit()

    return thistime_value

# ✅ 4. Selenium을 이용해 네이버 금융에서 분봉 데이터 가져오기
def get_intraday_data_naver(ticker):
    thistime_value = get_thistime_value(ticker)
    if not thistime_value:
        st.error("❌ 'thistime' 값을 가져오지 못했습니다.")
        return pd.DataFrame()

    url = f"https://finance.naver.com/item/sise_time.naver?code={ticker}&thistime={thistime_value}"

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(url)
    time.sleep(2)  # 데이터 로딩 대기

    # 🔹 HTML 테이블 데이터 가져오기
    tables = pd.read_html(driver.page_source, encoding="euc-kr")
    driver.quit()

    if not tables:
        st.error("❌ 네이버 금융에서 데이터를 찾을 수 없습니다.")
        return pd.DataFrame()

    df = tables[0]
    df = df.rename(columns={"체결시간": "Date", "체결가": "Close"})
    df = df[["Date", "Close"]].dropna()
    df["Date"] = pd.to_datetime(df["Date"], format="%H:%M").dt.strftime("%H:%M")

    return df

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
            ticker = get_ticker(st.session_state.company_name, source="fdr")
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
