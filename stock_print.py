import os
import time
import streamlit as st
import plotly.graph_objects as go
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ✅ ChromeDriver 실행 경로 (Streamlit 프로젝트 내 chromedriver 폴더)
CHROMEDRIVER_PATH = os.path.join(os.getcwd(), "chromedriver-win64", "chromedriver.exe")

# ✅ 최근 거래일 찾기
def get_recent_trading_day():
    today = datetime.now()
    if today.hour < 9:
        today -= timedelta(days=1)
    while today.weekday() in [5, 6]:
        today -= timedelta(days=1)
    return today.strftime('%Y-%m-%d')

# ✅ 네이버 금융에서 분봉 데이터 가져오기
def get_naver_intraday_data(stock_code, minute="1"):
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920x1080")

        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        url = f"https://finance.naver.com/item/sise_time.naver?code={stock_code}&thistime={minute}M"
        driver.get(url)
        time.sleep(2)

        rows = driver.find_elements(By.CSS_SELECTOR, "table.type2 tr")
        data = []
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 6:
                time_data = cols[0].text.strip()
                price = cols[1].text.strip().replace(",", "")
                volume = cols[5].text.strip().replace(",", "")

                if time_data and price.isnumeric() and volume.isnumeric():
                    data.append([time_data, int(price), int(volume)])

        driver.quit()

        df = pd.DataFrame(data, columns=["Time", "Price", "Volume"])
        df["Time"] = pd.to_datetime(df["Time"], format="%H:%M").dt.strftime("%H:%M")
        df.sort_values("Time", ascending=True, inplace=True)

        return df

    except Exception as e:
        st.error(f"네이버 금융 데이터 크롤링 오류: {e}")
        return pd.DataFrame()

# ✅ FinanceDataReader를 통한 일별 시세
def get_daily_stock_data_fdr(ticker, period):
    try:
        end_date = get_recent_trading_day()
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=30 if period == "1month" else 365)).strftime('%Y-%m-%d')
        df = fdr.DataReader(ticker, start_date, end_date)

        if df.empty:
            return pd.DataFrame()

        df = df.reset_index()
        df["Date"] = pd.to_datetime(df["Date"])
        df = df[df["Date"].dt.weekday < 5].reset_index(drop=True)

        return df
    except Exception as e:
        st.error(f"FinanceDataReader 데이터 불러오기 오류: {e}")
        return pd.DataFrame()

# ✅ 네이버 금융 티커 조회
def get_naver_ticker(company):
    try:
        listing = fdr.StockListing('KRX')
        ticker_row = listing[listing["Name"].str.strip() == company.strip()]
        if not ticker_row.empty:
            return str(ticker_row.iloc[0]["Code"]).zfill(6)
        return None
    except Exception as e:
        st.error(f"네이버 금융 티커 조회 오류: {e}")
        return None

# ✅ Plotly 주가 시각화
def plot_stock_plotly(df, company, period):
    if df is None or df.empty:
        st.warning(f"📉 {company} - 해당 기간({period})의 거래 데이터가 없습니다.")
        return

    fig = go.Figure()

    if period in ["1day", "week"]:
        df["FormattedDate"] = df["Time"]
        fig.add_trace(go.Scatter(
            x=df["FormattedDate"],
            y=df["Price"],
            mode="lines+markers",
            line=dict(color="royalblue", width=2),
            marker=dict(size=5),
            name="체결가"
        ))
    else:
        df["FormattedDate"] = df["Date"].dt.strftime("%m-%d")
        fig.add_trace(go.Candlestick(
            x=df["FormattedDate"],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="캔들 차트"
        ))

    fig.update_layout(
        title=f"{company} 주가 ({period})",
        xaxis_title="시간" if period in ["1day", "week"] else "날짜",
        yaxis_title="주가 (KRW)",
        template="plotly_white",
        xaxis=dict(showgrid=True, type="category", tickangle=-45),
        hovermode="x unified"
    )

    st.plotly_chart(fig)

# ✅ Streamlit 실행 함수
def main():
    st.set_page_config(page_title="Stock Price Visualization", page_icon="📈")
    st.title("_주가 시각화_ 📈")

    if "company_name" not in st.session_state:
        st.session_state.company_name = ""
    if "selected_period" not in st.session_state:
        st.session_state.selected_period = "1day"

    with st.sidebar:
        company_name = st.text_input("📌 분석할 기업명 (코스피 상장)", st.session_state.company_name)
        process = st.button("검색")

    if process and company_name:
        st.session_state.company_name = company_name

    if st.session_state.company_name:
        st.subheader(f"📈 {st.session_state.company_name} 최근 주가 추이")

        selected_period = st.radio(
            "기간 선택",
            options=["1day", "week", "1month", "1year"],
            horizontal=True
        )

        st.write(f"🔍 선택된 기간: {selected_period}")

        with st.spinner(f"📊 {st.session_state.company_name} ({selected_period}) 데이터 불러오는 중..."):
            ticker = get_naver_ticker(st.session_state.company_name)

            if not ticker:
                st.error("해당 기업의 네이버 금융 티커를 찾을 수 없습니다.")
                return

            if selected_period in ["1day", "week"]:
                df = get_naver_intraday_data(ticker, minute="1" if selected_period == "1day" else "5")
            else:
                df = get_daily_stock_data_fdr(ticker, selected_period)

            if df.empty:
                st.warning(f"📉 {st.session_state.company_name} - 해당 기간({selected_period})의 거래 데이터가 없습니다.")
            else:
                plot_stock_plotly(df, st.session_state.company_name, selected_period)

# ✅ 실행
if __name__ == '__main__':
    main()
