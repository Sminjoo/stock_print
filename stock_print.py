import streamlit as st
import plotly.graph_objects as go
import FinanceDataReader as fdr
import pandas as pd
from yahooquery import Ticker  # ✅ yahooquery 사용
from datetime import datetime, timedelta

# ✅ 1. 최근 거래일 찾기 함수
def get_recent_trading_day():
    today = datetime.now()
    if today.hour < 9:  # 9시 이전이면 전날을 기준으로
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
            return f"{krx_ticker}.KS" if source == "yahoo" else krx_ticker
        return None
    except Exception as e:
        st.error(f"티커 조회 중 오류 발생: {e}")
        return None

# ✅ 3. YahooQuery를 활용한 빠른 분봉 데이터 가져오기
@st.cache_data
def get_intraday_data_yahooquery(ticker, period="1d", interval="1m"):
    """ YahooQuery를 사용하여 빠르게 주가 데이터를 가져오는 함수 """
    try:
        stock = Ticker(ticker)
        df = stock.history(period=period, interval=interval)

        if df.empty or "close" not in df.columns:
            return pd.DataFrame()

        df = df.reset_index()
        df = df.rename(columns={"date": "Date", "close": "Close"})
        df["Date"] = pd.to_datetime(df["Date"])
        df = df[df["Date"].dt.weekday < 5].reset_index(drop=True)  # ✅ 주말 데이터 제거

        return df
    except Exception as e:
        st.error(f"YahooQuery 데이터 불러오기 오류: {e}")
        return pd.DataFrame()

# ✅ 4. FinanceDataReader를 통한 일별 시세 (캐싱 + 최신 데이터 업데이트)
@st.cache_data
def get_cached_stock_data(ticker):
    """ 기존 캐시된 1년치 주가 데이터 가져오기 """
    end_date = get_recent_trading_day()
    start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=365)).strftime('%Y-%m-%d')
    df = fdr.DataReader(ticker, start_date, end_date)

    if df.empty:
        return pd.DataFrame()

    df = df.reset_index()
    df = df.rename(columns={"Date": "Date", "Close": "Close"})
    df["Date"] = pd.to_datetime(df["Date"])

    return df[df["Date"].dt.weekday < 5].reset_index(drop=True)

def update_stock_data(ticker, cached_df):
    """ 기존 데이터에 최신 데이터를 추가 """
    if cached_df.empty:
        return get_cached_stock_data(ticker)  # 처음 실행하는 경우 전체 데이터 가져옴

    latest_date = cached_df["Date"].max()  # 가장 최근 데이터 날짜
    today = get_recent_trading_day()  # 오늘 날짜

    if latest_date.strftime('%Y-%m-%d') >= today:  # 이미 최신 데이터 있음
        return cached_df

    # ✅ 기존 데이터 이후의 최신 데이터만 가져옴
    new_df = fdr.DataReader(ticker, latest_date.strftime('%Y-%m-%d'), today)

    if new_df.empty:
        return cached_df  # 추가 데이터 없음

    new_df = new_df.reset_index()
    new_df = new_df.rename(columns={"Date": "Date", "Close": "Close"})
    new_df["Date"] = pd.to_datetime(new_df["Date"])

    # ✅ 기존 데이터와 새로운 데이터 합침
    updated_df = pd.concat([cached_df, new_df]).drop_duplicates(subset=["Date"]).reset_index(drop=True)
    return updated_df

# ✅ 5. Plotly를 이용한 주가 시각화 함수
def plot_stock_plotly(df, company, period):
    if df is None or df.empty:
        st.warning(f"📉 {company} - 해당 기간({period})의 거래 데이터가 없습니다.")
        return

    fig = go.Figure()

    df["FormattedDate"] = df["Date"].dt.strftime("%m-%d")  # 기본 날짜 포맷
    if period in ["1day", "week"]:
        df["FormattedDate"] = df["Date"].dt.strftime("%H:%M") if period == "1day" else df["Date"].dt.strftime("%m-%d %H:%M")

    if period in ["1day", "week"]:
        fig.add_trace(go.Scatter(
            x=df["FormattedDate"],
            y=df["Close"],
            mode="lines+markers",
            line=dict(color="royalblue", width=2),
            marker=dict(size=5),
            name="체결가"
        ))
    else:
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
        xaxis_title="시간" if period == "1day" else "날짜",
        yaxis_title="주가 (KRW)",
        template="plotly_white",
        xaxis=dict(showgrid=True, type="category", tickangle=-45),
        hovermode="x unified"
    )

    st.plotly_chart(fig)

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
            if selected_period in ["1day", "week"]:
                ticker = get_ticker(st.session_state.company_name, source="yahoo")
                if not ticker:
                    st.error("해당 기업의 야후 파이낸스 티커 코드를 찾을 수 없습니다.")
                    return

                interval = "1m" if selected_period == "1day" else "5m"
                df = get_intraday_data_yahooquery(ticker, period="5d" if selected_period == "week" else "1d", interval=interval)
            else:
                ticker = get_ticker(st.session_state.company_name, source="fdr")
                if not ticker:
                    st.error("해당 기업의 FinanceDataReader 티커 코드를 찾을 수 없습니다.")
                    return

                cached_df = get_cached_stock_data(ticker)
                df = update_stock_data(ticker, cached_df)

            if df.empty:
                st.warning(f"📉 {st.session_state.company_name} - 해당 기간({st.session_state.selected_period})의 거래 데이터가 없습니다.")
            else:
                plot_stock_plotly(df, st.session_state.company_name, st.session_state.selected_period)

if __name__ == '__main__':
    main()
