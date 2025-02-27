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
        df = df.rename(columns={"Datetime": "Date", "Close": "Close",
                                "Open": "Open", "High": "High", "Low": "Low"})
        df["Date"] = pd.to_datetime(df["Date"])
        df = df[df["Date"].dt.weekday < 5].reset_index(drop=True)  # 주말 데이터 제거
        
        # ✅ 3시 30분까지 데이터 포함하도록 필터 적용
        df = df[df["Date"].dt.time <= datetime.strptime("15:30:00", "%H:%M:%S").time()]
        
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
        df["Date"] = pd.to_datetime(df["Date"])
        df = df[df["Date"].dt.weekday < 5].reset_index(drop=True)  # 주말 제거
        return df
    except Exception as e:
        st.error(f"FinanceDataReader 데이터 불러오기 오류: {e}")
        return pd.DataFrame()

# ✅ 5. Plotly를 이용한 주가 시각화 함수 (1day & week도 캔들 차트 적용)
def plot_stock_plotly(df, company, period):
    if df is None or df.empty:
        st.warning(f"📉 {company} - 해당 기간({period})의 거래 데이터가 없습니다.")
        return

    fig = go.Figure()

    # ✅ x축 날짜 형식 설정
    if period == "1day":
        df["FormattedDate"] = df["Date"].dt.strftime("%H:%M")
    elif period == "week":
        df["FormattedDate"] = df["Date"].dt.strftime("%m-%d %H:%M")
    else:
        df["FormattedDate"] = df["Date"].dt.strftime("%m-%d")

    # ✅ 모든 기간(1day, week, 1month, 1year)에서 캔들 차트 적용
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

# ✅ 실행
def main():
    st.title("Stock Data Viewer")
    st.write("Welcome to the stock data visualization app.")

if __name__ == '__main__':
    main()
