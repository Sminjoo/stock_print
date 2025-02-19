import streamlit as st
import requests
import time
import plotly.graph_objects as go
import FinanceDataReader as fdr
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import re

# ✅ 1. 최근 거래일 찾기 함수
def get_recent_trading_day():
    today = datetime.now()
    if today.hour < 9:  # 9시 이전이면 전날을 기준으로
        today -= timedelta(days=1)

    while today.weekday() in [5, 6]:  # 토요일(5), 일요일(6)이면 하루씩 감소
        today -= timedelta(days=1)

    return today.strftime('%Y-%m-%d')

# ✅ 2. 네이버 금융에서 'thistime' 값 가져오기
def get_thistime(ticker):
    try:
        url = f"https://finance.naver.com/item/sise.naver?code={ticker}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        # ✅ "thistime=" 값이 포함된 링크 찾기
        link = soup.find("a", href=re.compile(f"/item/sise_time.naver\\?code={ticker}&thistime="))
        if link:
            href = link["href"]
            match = re.search(r"thistime=(\d{14})", href)  # YYYYMMDDHHMMSS 형식
            if match:
                return match.group(1)  # 정확한 thistime 값 반환

        return None

    except Exception as e:
        st.error(f"❌ 'thistime' 값을 가져오는 중 오류 발생: {e}")
        return None

# ✅ 3. 네이버 금융 시간별 시세 크롤링 (1일/1주)
def get_intraday_data_naver(ticker, period):
    thistime = get_thistime(ticker)  # 최신 thistime 값 가져오기
    if not thistime:
        st.warning(f"⚠️ {ticker}의 'thistime' 값을 가져올 수 없습니다.")
        return pd.DataFrame()

    base_url = f"https://finance.naver.com/item/sise_time.naver?code={ticker}&thistime={thistime}&page="
    headers = {"User-Agent": "Mozilla/5.0"}

    prices = []
    times = []
    page = 1

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
    df["Date"] = get_recent_trading_day()
    df["Datetime"] = pd.to_datetime(df["Date"] + " " + df["Time"])
    df.set_index("Datetime", inplace=True)

    return df

# ✅ 4. FinanceDataReader를 통한 일별 시세 (1개월/1년)
def get_daily_stock_data(ticker, period):
    end_date = get_recent_trading_day()
    start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=30 if period == "1month" else 365)).strftime('%Y-%m-%d')
    df = fdr.DataReader(ticker, start_date, end_date)

    if df.empty:
        return pd.DataFrame()

    df = df.reset_index()
    df = df.rename(columns={"Date": "Date", "Close": "Close"})

    # ✅ **주말(토요일 & 일요일) 제거**
    df = df[df["Date"].dt.weekday < 5]

    return df

# ✅ 5. 주가 시각화 & 티커 조회 함수
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

# ✅ 6. Plotly를 이용한 주가 시각화 함수
def plot_stock_plotly(df, company, period):
    if df is None or df.empty:
        st.warning(f"📉 {company} - 해당 기간({period})의 거래 데이터가 없습니다.")
        return

    fig = go.Figure()

    if period in ["1day", "week"]:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df["Close"],
            mode="lines+markers",
            line=dict(color="royalblue", width=2),
            marker=dict(size=5),
            name="체결가"
        ))
    else:
        fig.add_trace(go.Candlestick(
            x=df["Date"],
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
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True),
        hovermode="x unified"
    )

    st.plotly_chart(fig)

# ✅ 7. 메인 실행 함수
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

        with st.spinner(f"📊 {st.session_state.company_name} ({st.session_state.selected_period}) 데이터 불러오는 중..."):
            ticker = get_ticker(st.session_state.company_name)
            if not ticker:
                st.error("해당 기업의 티커 코드를 찾을 수 없습니다.")
                return

            df = get_intraday_data_naver(ticker, selected_period) if selected_period in ["1day", "week"] else get_daily_stock_data(ticker, selected_period)
            plot_stock_plotly(df, st.session_state.company_name, selected_period)

if __name__ == '__main__':
    main()
