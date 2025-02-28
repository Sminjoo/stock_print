import streamlit as st
import plotly.graph_objects as go
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

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

# ✅ 3. 네이버 금융에서 분봉 데이터 가져오기 (1day, week)
def get_intraday_data_naver(ticker):
    today = datetime.now().strftime('%Y%m%d')
    url_template = f"https://finance.naver.com/item/sise_time.naver?code={ticker}&thistime={today}333333&page={{}}"
    all_data = []
    page = 1
    max_pages = 40  # ✅ 최대 40페이지까지만 크롤링

    while page <= max_pages:
        url = url_template.format(page)
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        if response.status_code != 200:
            st.error(f"네이버 금융 데이터 요청 실패 (페이지 {page})")
            break
        
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'class': 'type2'})
        
        if not table:
            break  # 데이터가 없으면 종료
        
        rows = table.find_all('tr')[2:]  # 첫 번째 행(컬럼명) 제외
        page_data = []
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 2:
                continue
            
            time = cols[0].text.strip()
            price = cols[1].text.strip().replace(',', '')
            
            if time and price.isdigit():
                page_data.append([time, int(price)])
        
        if not page_data:
            break  # 더 이상 데이터가 없으면 크롤링 종료
        
        all_data.extend(page_data)

        # ✅ 9:00 데이터가 포함되면 즉시 종료
        if "09:00" in [data[0] for data in page_data]:
            break

        page += 1
        time.sleep(0.3)  # ✅ 딜레이 추가 (로딩 속도 조절)

    df = pd.DataFrame(all_data, columns=['Time', 'Price'])
    
    # ✅ 9:00~15:30 데이터만 필터링
    df = df[(df["Time"] >= "09:00") & (df["Time"] <= "15:30")]

    df['Time'] = pd.to_datetime(df['Time'], format='%H:%M').dt.strftime('%H:%M')
    df = df.iloc[::-1].reset_index(drop=True)  # 시간순 정렬
    return df

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
        df = df[df["Date"].dt.weekday < 5].reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"FinanceDataReader 데이터 불러오기 오류: {e}")
        return pd.DataFrame()

# ✅ 5. Plotly를 이용한 주가 시각화 함수 (x축 간격 조정)
def plot_stock_plotly(df, company, period):
    if df is None or df.empty:
        st.warning(f"📉 {company} - 해당 기간({period})의 거래 데이터가 없습니다.")
        return

    fig = go.Figure()

    # ✅ x축 날짜 형식 설정
    if period == "1day":
        df["FormattedDate"] = df["Time"]
    elif period == "week":
        df["FormattedDate"] = df["Date"].dt.strftime("%m-%d %H:%M")
    else:
        df["FormattedDate"] = df["Date"].dt.strftime("%m-%d")

    # ✅ x축 간격 설정
    if period == "1day":
        tickvals = df.iloc[::60]["FormattedDate"].tolist()
    elif period == "week":
        tickvals = df[df["FormattedDate"].str.endswith("09:00")]["FormattedDate"].tolist()
    elif period == "1month":
        tickvals = df.iloc[::4]["FormattedDate"].tolist()
    else:
        df['Year'] = df['Date'].dt.year
        df['Month'] = df['Date'].dt.month
        first_month = df['Month'].iloc[0]
        first_year = df['Year'].iloc[0]
        
        monthly_data = []
        for (year, month), group in df.groupby(['Year', 'Month']):
            if year == first_year and month == first_month:
                continue
            first_day = group.iloc[0]
            monthly_data.append(first_day)
        
        if monthly_data:
            monthly_df = pd.DataFrame(monthly_data)
            tickvals = monthly_df["FormattedDate"].tolist()
        else:
            tickvals = []

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
        xaxis=dict(
            showgrid=True, 
            type="category", 
            tickmode='array', 
            tickvals=tickvals, 
            tickangle=-45
        ),
        hovermode="x unified"
    )

    st.plotly_chart(fig)

# ✅ 6. Streamlit 메인 실행 함수
# ✅ 6. Streamlit 메인 실행 함수
def main():
    st.set_page_config(page_title="Stock Price Visualization", page_icon=":chart_with_upwards_trend:")
    st.title("_주가 시각화_ :chart_with_upwards_trend:")

    # ✅ Streamlit 세션 상태 초기화
    if "company_name" not in st.session_state:
        st.session_state.company_name = ""
    if "selected_period" not in st.session_state:
        st.session_state.selected_period = "1day"
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False  # 🚀 데이터를 처음부터 로드하지 않음

    # ✅ 사이드바 입력
    with st.sidebar:
        company_name = st.text_input("분석할 기업명 (코스피 상장)", st.session_state.company_name)
        process = st.button("검색")

    if process and company_name:
        st.session_state.company_name = company_name
        st.session_state.data_loaded = False  # 🚀 새로운 기업 검색 시 데이터 리셋

    # ✅ 메인 화면: 주가 데이터 선택
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

        # ✅ 🚀 "데이터 불러오기" 버튼 추가 (바로 크롤링 안 하고, 버튼 누를 때 실행)
        if st.button("📊 데이터 불러오기"):
            st.session_state.data_loaded = True  # ✅ 버튼을 눌렀을 때만 크롤링 시작

        # ✅ 🚀 데이터가 로드되지 않았다면 크롤링 실행 X (앱 멈춤 방지)
        if not st.session_state.data_loaded:
            st.warning("📢 '데이터 불러오기' 버튼을 눌러 주세요!")
            return

        with st.spinner(f"📊 {st.session_state.company_name} ({st.session_state.selected_period}) 데이터 불러오는 중..."):
            ticker = get_ticker(st.session_state.company_name)
            if not ticker:
                st.error("해당 기업의 티커 코드를 찾을 수 없습니다.")
                return

            if st.session_state.selected_period in ["1day", "week"]:
                df = get_intraday_data_naver(ticker)  # ✅ 🚀 버튼 누를 때만 크롤링 실행
            else:
                df = get_daily_stock_data_fdr(ticker, st.session_state.selected_period)

            if df.empty:
                st.warning(f"📉 {st.session_state.company_name} - 해당 기간({st.session_state.selected_period})의 거래 데이터가 없습니다.")
            else:
                plot_stock_plotly(df, st.session_state.company_name, st.session_state.selected_period)

# ✅ 실행
if __name__ == '__main__':
    main()
