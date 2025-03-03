import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import datetime
import plotly.express as px

# 📌 가장 최근 거래일을 구하는 함수
def get_recent_trading_day():
    """
    가장 최근 거래일을 구하는 함수
    Returns:
        str: 최근 거래일(YYYY-MM-DD 형식)
    """
    today = datetime.datetime.now()
    if today.hour < 9:  # 9시 이전이면 전날을 기준으로
        today -= datetime.timedelta(days=1)
    while today.weekday() in [5, 6]:  # 토요일(5), 일요일(6)이면 하루씩 감소
        today -= datetime.timedelta(days=1)
    return today.strftime('%Y-%m-%d')


# 📌 기업명으로부터 증권 코드를 찾는 함수 (KRX 기준)
def get_ticker(company):
    """
    기업명으로부터 증권 코드를 찾는 함수
    Args:
        company (str): 기업명
    Returns:
        str: 티커 코드 (6자리 숫자 문자열)
    """
    try:
        listing = fdr.StockListing('KRX')
        ticker_row = listing[listing["Name"].str.strip() == company.strip()]
        if not ticker_row.empty:
            return str(ticker_row.iloc[0]["Code"]).zfill(6)  # KRX용 티커 반환
        return None
    except Exception as e:
        st.error(f"티커 조회 중 오류 발생: {e}")
        return None


# 📌 네이버 fchart API에서 분봉 데이터 가져오기
def get_naver_fchart_minute_data(stock_code, minute="1", days=1):
    """
    네이버 금융 Fchart API에서 분봉 데이터를 가져와서 DataFrame으로 변환
    """
    # 📌 현재 시간 가져오기
    now = datetime.datetime.now()

    # 📌 아침 9시 이전이면 전날 데이터 가져오기
    if now.hour < 9:
        now -= datetime.timedelta(days=1)

    # 📌 주말이면 금요일 데이터 가져오기
    if now.weekday() == 6:  # 일요일
        now -= datetime.timedelta(days=2)  # 금요일로 이동
    elif now.weekday() == 5:  # 토요일
        now -= datetime.timedelta(days=1)  # 금요일로 이동

    # 📌 기준 날짜 설정 (1 Day 모드일 때만 사용)
    target_date = now.strftime("%Y-%m-%d") if days == 1 else None

    # 📌 ✅ 네이버 Fchart API 호출
    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={stock_code}&timeframe=minute&count={days * 78}&requestType=0"
    response = requests.get(url)

    if response.status_code != 200:
        return pd.DataFrame()  # 요청 실패 시 빈 데이터 반환

    soup = BeautifulSoup(response.text, "lxml")  # ✅ XML 파싱

    data_list = []
    for item in soup.find_all("item"):
        values = item["data"].split("|")
        if len(values) < 6:
            continue

        time, _, _, _, close, _ = values  # ✅ 종가(close)만 사용 (거래량 삭제)
        if close == "null":
            continue

        time = pd.to_datetime(time, format="%Y%m%d%H%M")
        close = float(close)

        # 📌 1 Day 모드일 때만 날짜 필터링
        if target_date:
            if time.strftime("%Y-%m-%d") == target_date:
                data_list.append([time, close])
        else:
            data_list.append([time, close])  # ✅ Week 모드에서는 전체 추가

    df = pd.DataFrame(data_list, columns=["시간", "종가"])

    # 📌 ✅ 9시 ~ 15시 30분 데이터만 필터링
    df["시간"] = pd.to_datetime(df["시간"])
    df = df[(df["시간"].dt.time >= datetime.time(9, 0)) & (df["시간"].dt.time <= datetime.time(15, 30))]

    # 📌 X축을 문자형으로 변환 (빈 데이터 없이 연속된 데이터만 표시)
    df["시간"] = df["시간"].astype(str)

    return df


# 📌 FinanceDataReader를 통해 일별 시세를 가져오는 함수 (1개월, 1년)
def get_daily_stock_data_fdr(ticker, period):
    """
    FinanceDataReader를 통해 일별 시세를 가져오는 함수
    Args:
        ticker (str): 티커 코드
        period (str): 기간 ("1month" 또는 "1year")
    Returns:
        DataFrame: 주식 데이터
    """
    try:
        end_date = get_recent_trading_day()
        start_date = (datetime.datetime.strptime(end_date, '%Y-%m-%d') - datetime.timedelta(
            days=30 if period == "1month" else 365)).strftime('%Y-%m-%d')
        df = fdr.DataReader(ticker, start_date, end_date)
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        df = df.rename(columns={"Date": "Date", "Close": "Close"})
        # 주말 데이터 완전 제거
        df["Date"] = pd.to_datetime(df["Date"])
        df = df[df["Date"].dt.weekday < 5].reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"FinanceDataReader 데이터 불러오기 오류: {e}")
        return pd.DataFrame()


# 📌 Streamlit UI
st.title("📈 국내 주식 분봉 차트 조회 (1 Day / Week)")
st.write("네이버 금융에서 주식 분봉 데이터를 가져와 시각화합니다.")

stock_code = st.text_input("종목 코드 입력 (예: 삼성전자 005930)", "005930")

# 📌 `1 Day` & `Week` 버튼 UI
col1, col2 = st.columns(2)
with col1:
    day_selected = st.button("📅 1 Day")
with col2:
    week_selected = st.button("📆 Week")

# 📌 버튼 클릭 여부에 따라 데이터 가져오기
if day_selected or week_selected:
    df = get_naver_fchart_minute_data(stock_code, "1" if day_selected else "5", 1 if day_selected else 7)

    if df.empty:
        st.error("❌ 데이터를 불러오지 못했습니다. 종목 코드를 확인하세요.")
    else:
        # 📌 📊 가격 차트 (X축을 문자형으로 설정하여 데이터 없는 날 제외)
        fig = px.line(df, x="시간", y="종가", title=f"{stock_code} {'1 Day' if day_selected else 'Week'}")
        fig.update_xaxes(type="category")  # ✅ X축을 카테고리(문자형)로 설정
        st.plotly_chart(fig)
