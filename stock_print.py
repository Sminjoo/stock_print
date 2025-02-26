import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import pandas as pd

# ✅ 세션 상태 업데이트 함수 (기간 변경 시 즉시 반영)
def update_period():
    st.session_state.selected_period = st.session_state.radio_selection

# ✅ 1. 최근 거래일 찾기 함수
def get_recent_trading_day():
    today = datetime.now()
    if today.hour < 9:
        today -= timedelta(days=1)
    while today.weekday() in [5, 6]:  # 토요일(5), 일요일(6) 제외
        today -= timedelta(days=1)
    return today.strftime('%Y-%m-%d')

# ✅ 2. 티커 조회 함수
def get_ticker(company, source="yahoo"):
    try:
        listing = fdr.StockListing('KRX')
        ticker_row = listing[listing["Name"].str.strip() == company.strip()]
        if not ticker_row.empty:
            krx_ticker = str(ticker_row.iloc[0]["Code"]).zfill(6)
            return krx_ticker + ".KS" if source == "yahoo" else krx_ticker
        return None
    except Exception as e:
        st.error(f"티커 조회 중 오류 발생: {e}")
        return None

# ✅ 3. 야후 파이낸스에서 분봉 데이터 가져오기 (1day, week)
def get_intraday_data_yahoo(ticker, period="1d", interval="1m"):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        df["Date"] = pd.to_datetime(df["Datetime"])  # ✅ 원본 데이터 유지
        df = df[df["Date"].dt.weekday < 5].reset_index(drop=True)  # ✅ 주말 제거
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
        df["Date"] = pd.to_datetime(df["Date"])  # ✅ 원본 데이터 유지
        df = df[df["Date"].dt.weekday < 5].reset_index(drop=True)  # ✅ 주말 제거
        return df
    except Exception as e:
        st.error(f"FinanceDataReader 데이터 불러오기 오류: {e}")
        return pd.DataFrame()

# ✅ 5. Plotly를 이용한 주가 시각화 함수 (X축 category 타입 유지)
def plot_stock_plotly(df, company, period):
    if df is None or df.empty:
        st.warning(f"📉 {company} - 해당 기간({period})의 거래 데이터가 없습니다.")
        return

    fig = go.Figure()

    # ✅ X축 레이블 설정 (글씨 최소화, 원본 데이터 유지)
    if period == "1day":
        df["FormattedDate"] = df["Date"].dt.strftime("%H:%M")  # 1시간 단위
        tickvals = df["FormattedDate"][::60]  # 60분 간격으로 표시
        hoverformat = "%m-%d %H:%M"  # 마우스 오버 시 월-일 시간
    elif period == "week":
        df["FormattedDate"] = df["Date"].dt.strftime("%m-%d")  # 하루 단위
        tickvals = df["FormattedDate"][::1]  # 하루 간격으로 표시
        hoverformat = "%m-%d %H:%M"  # 마우스 오버 시 월-일 시간
    elif period == "1month":
        df["FormattedDate"] = df["Date"].dt.strftime("%m-%d")  # 4일 단위
        tickvals = df["FormattedDate"][::4]  # 4일 간격으로 표시
        hoverformat = "%m-%d"  # 마우스 오버 시 월-일
    else:  # 1year
        df["FormattedDate"] = df["Date"].dt.strftime("%m")  # 월 단위
        tickvals = df["FormattedDate"].unique()  # 모든 월 표시
        hoverformat = "%Y-%m-%d"  # 마우스 오버 시 연-월-일

    # ✅ 캔들 차트 추가 (데이터 변형 없이 원본 사용)
    fig.add_trace(go.Candlestick(
        x=df["Date"],  # ✅ 원본 날짜 컬럼 사용
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
        xaxis=dict(
            showgrid=True, 
            type="category",  # ✅ category 타입 유지 → 빈 공간 없이 연속적으로 표시
            tickvals=tickvals,  # ✅ X축 레이블 최소화
            tickangle=-45,
            hoverformat=hoverformat  # ✅ 마우스 오버 시 날짜·시간 표시
        ),
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

        st.session_state.radio_selection = st.session_state.selected_period
        selected_period = st.radio(
            "기간 선택",
            options=["1day", "week", "1month", "1year"],
            index=["1day", "week", "1month", "1year"].index(st.session_state.selected_period),
            key="radio_selection",
            on_change=update_period
        )

        st.write(f"🔍 선택된 기간: {st.session_state.selected_period}")

        with st.spinner(f"📊 {st.session_state.company_name} ({st.session_state.selected_period}) 데이터 불러오는 중..."):
            ticker = get_ticker(st.session_state.company_name, source="yahoo" if selected_period in ["1day", "week"] else "fdr")
            if not ticker:
                st.error("티커를 찾을 수 없습니다.")
                return

            df = get_intraday_data_yahoo(ticker) if selected_period in ["1day", "week"] else get_daily_stock_data_fdr(ticker, selected_period)

            if df.empty:
                st.warning(f"📉 {st.session_state.company_name} - 해당 기간({st.session_state.selected_period}) 데이터가 없습니다.")
            else:
                plot_stock_plotly(df, st.session_state.company_name, st.session_state.selected_period)

# ✅ 실행
if __name__ == '__main__':
    main()
