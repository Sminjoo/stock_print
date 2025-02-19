import streamlit as st
import plotly.graph_objects as go
import FinanceDataReader as fdr
from pykrx import stock
from datetime import datetime, timedelta
import pandas as pd

# ✅ 1. 최근 거래일 찾기 함수
def get_recent_trading_day():
    today = datetime.now()
    if today.hour < 9:  # 9시 이전이면 전날을 기준으로
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
                    df = get_intraday_data_pykrx(ticker, st.session_state.selected_period)
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
        ticker_row = listing[listing["Name"].str.strip() == company.strip()]
        if not ticker_row.empty:
            return str(ticker_row.iloc[0]["Code"]).zfill(6)
        return None

    except Exception as e:
        st.error(f"티커 조회 중 오류 발생: {e}")
        return None

# ✅ 4. Pykrx를 활용한 분 단위 & 일별 시세 (1일/1주)
def get_intraday_data_pykrx(ticker, period):
    today = get_recent_trading_day()
    start_date = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=4 if period == "week" else 0)).strftime("%Y%m%d")

    if period == "1day":
        # ✅ 1일치 분 단위 데이터 가져오기
        df = stock.get_market_ohlcv_by_date(fromdate=today, todate=today, ticker=ticker, freq="m")  # "m" = 분 단위
    else:
        # ✅ 최근 5거래일 일별 시세 가져오기
        df = stock.get_market_ohlcv_by_date(fromdate=start_date, todate=today, ticker=ticker, freq="d")  # "d" = 일 단위

    if df.empty:
        return pd.DataFrame()

    df = df.reset_index()
    df = df.rename(columns={"날짜": "Date", "종가": "Close"})

    return df

# ✅ 5. FinanceDataReader를 통한 일별 시세 (1개월/1년)
def get_daily_stock_data(ticker, period):
    end_date = get_recent_trading_day()
    start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=30 if period == "1month" else 365)).strftime('%Y-%m-%d')
    df = fdr.DataReader(ticker, start_date, end_date)

    if df.empty:
        return pd.DataFrame()

    df = df.reset_index()  # ✅ "Date" 컬럼 추가 (에러 방지)
    df = df.rename(columns={"Date": "Date", "Close": "Close"})

    return df

# ✅ 6. Plotly를 이용한 주가 시각화 함수
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

# ✅ 실행
if __name__ == '__main__':
    main()
