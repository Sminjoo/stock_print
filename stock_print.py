import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import pandas as pd

# ✅ 1. 최근 거래일 찾기 함수
def get_recent_trading_day():
    today = datetime.now()
    if today.hour < 9:  # 9시 이전이면 전날을 기준으로
        today -= timedelta(days=1)

    while today.weekday() in [5, 6]:  # 토요일(5), 일요일(6)이면 하루씩 감소
        today -= timedelta(days=1)

    return today.strftime('%Y-%m-%d')

# ✅ 2. 티커 조회 함수 (야후 파이낸스 vs. FinanceDataReader 각각 다르게)
def get_ticker(company, source="yahoo"):
    try:
        listing = fdr.StockListing('KRX')
        ticker_row = listing[listing["Name"].str.strip() == company.strip()]
        if not ticker_row.empty:
            krx_ticker = str(ticker_row.iloc[0]["Code"]).zfill(6)
            if source == "yahoo":
                return krx_ticker + ".KS"  # 야후 파이낸스용 티커 변환
            return krx_ticker  # FinanceDataReader용 티커
        return None

    except Exception as e:
        st.error(f"티커 조회 중 오류 발생: {e}")
        return None

# ✅ 3. 야후 파이낸스에서 분봉 데이터 가져오는 함수 (1day, week)
def get_intraday_data_yahoo(ticker, period="1d", interval="1m"):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)

        if df.empty:
            return pd.DataFrame()

        df = df.reset_index()
        df = df.rename(columns={"Datetime": "Date", "Close": "Close"})
        return df
    except Exception as e:
        st.error(f"야후 파이낸스 데이터 불러오기 오류: {e}")
        return pd.DataFrame()

# ✅ 4. FinanceDataReader를 통한 일별 시세 (1month, 1year)
def get_daily_stock_data_fdr(ticker, period):
    try:
        end_date = get_recent_trading_day()
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=30 if period == "1month" else 365)).strftime('%Y-%m-%d')
        df = fdr.DataReader(ticker, start_date, end_date)

        if df.empty:
            return pd.DataFrame()

        df = df.reset_index()
        df = df.rename(columns={"Date": "Date", "Close": "Close"})

        return df
    except Exception as e:
        st.error(f"FinanceDataReader 데이터 불러오기 오류: {e}")
        return pd.DataFrame()

# ✅ 5. Plotly를 이용한 주가 시각화 함수 (주말 부분을 회색 처리)
def plot_stock_plotly(df, company, period):
    if df is None or df.empty:
        st.warning(f"📉 {company} - 해당 기간({period})의 거래 데이터가 없습니다.")
        return

    fig = go.Figure()

    if period in ["1day", "week"]:
        fig.add_trace(go.Scatter(
            x=df["Date"],
            y=df["Close"],
            mode="lines+markers",
            line=dict(color="royalblue", width=2),
            marker=dict(size=5),
            name="체결가"
        ))

        # ✅ 주말 부분을 회색 처리
        for i in range(len(df) - 1):
            day_of_week = df["Date"].dt.weekday.iloc[i]
            if day_of_week in [5, 6]:  # 토요일(5), 일요일(6)
                fig.add_shape(
                    type="rect",
                    x0=df["Date"].iloc[i], x1=df["Date"].iloc[i + 1],
                    y0=0, y1=1,
                    xref="x", yref="paper",
                    fillcolor="rgba(200, 200, 200, 0.3)",
                    layer="below",
                    line_width=0,
                )
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
                ticker = get_ticker(st.session_state.company_name, source="yahoo")  # ✅ 야후 파이낸스용 티커
                if not ticker:
                    st.error("해당 기업의 야후 파이낸스 티커 코드를 찾을 수 없습니다.")
                    return

                interval = "1m" if selected_period == "1day" else "5m"
                df = get_intraday_data_yahoo(ticker, period="5d" if selected_period == "week" else "1d", interval=interval)

            else:
                ticker = get_ticker(st.session_state.company_name, source="fdr")  # ✅ FinanceDataReader용 티커
                if not ticker:
                    st.error("해당 기업의 FinanceDataReader 티커 코드를 찾을 수 없습니다.")
                    return

                df = get_daily_stock_data_fdr(ticker, selected_period)

            if df.empty:
                st.warning(f"📉 {st.session_state.company_name} - 해당 기간({st.session_state.selected_period})의 거래 데이터가 없습니다.")
            else:
                plot_stock_plotly(df, st.session_state.company_name, st.session_state.selected_period)

# ✅ 실행
if __name__ == '__main__':
    main()
