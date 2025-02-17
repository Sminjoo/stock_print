import streamlit as st
import requests
import time
import mplfinance as mpf
import FinanceDataReader as fdr
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ✅ 1. 한글 폰트 설정
FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "NanumGothic.ttf")

def set_korean_font():
    if os.path.exists(FONT_PATH):
        fe = fm.FontEntry(fname=FONT_PATH, name="NanumGothic")
        fm.fontManager.ttflist.insert(0, fe)
        plt.rcParams.update({"font.family": "NanumGothic", "axes.unicode_minus": False})
    else:
        print("⚠️ 폰트 파일을 찾을 수 없습니다. 'fonts/NanumGothic.ttf' 위치 확인 필요!")

set_korean_font()

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
        process = st.button("시각화 시작")

    # ✅ 기업명이 입력되었을 경우만 실행
    if process or st.session_state.company_name:
        st.session_state.company_name = company_name  # ✅ 세션에 저장
        st.subheader(f"📈 {st.session_state.company_name} 최근 주가 추이")

        # ✅ 반응형 UI 버튼 추가 (선택한 기간을 즉시 반영)
        st.radio(
            "기간 선택",
            options=["1day", "week", "1month", "1year"],
            index=["1day", "week", "1month", "1year"].index(st.session_state.selected_period),
            horizontal=True,
            key="selected_period"  # ✅ `key`를 지정하면 자동으로 값이 업데이트됨
        )

        st.write(f"🔍 선택된 기간: {st.session_state.selected_period}")

        # ✅ 주가 데이터를 가져오고 시각화
        with st.spinner(f"📊 {st.session_state.company_name} ({st.session_state.selected_period}) 데이터 불러오는 중..."):
            ticker = get_ticker(st.session_state.company_name)
            if not ticker:
                st.error("해당 기업의 티커 코드를 찾을 수 없습니다.")
                return

            st.write(f"✅ 가져온 티커 코드: {ticker}")

            df = None
            try:
                if st.session_state.selected_period in ["1day", "week"]:
                    st.write("⏳ 1일 또는 1주 데이터 가져오는 중...")
                    df = get_intraday_data_bs(ticker)  # ✅ Requests 기반 크롤링 적용
                else:
                    st.write("⏳ 1개월 또는 1년 데이터 가져오는 중...")
                    end_date = datetime.now().strftime('%Y-%m-%d')
                    start_date = (datetime.now() - timedelta(days=30 if st.session_state.selected_period == "1month" else 365)).strftime('%Y-%m-%d')
                    df = fdr.DataReader(ticker, start_date, end_date)

                if df is None or df.empty:
                    st.warning(f"📉 {st.session_state.company_name} ({ticker}) - 해당 기간({st.session_state.selected_period})의 거래 데이터가 없습니다.")
                else:
                    st.write(f"📊 데이터 미리보기:\n{df.head()}")
                    plot_stock(df, st.session_state.company_name, st.session_state.selected_period)

            except Exception as e:
                st.error(f"주가 데이터를 불러오는 중 오류 발생: {e}")

# ✅ 3. 주가 시각화 & 티커 조회 함수
def get_ticker(company):
    try:
        listing = fdr.StockListing('KRX')
        if listing.empty:
            listing = fdr.StockListing('KOSPI')
        
        if listing.empty:
            st.error("상장 기업 정보를 불러올 수 없습니다.")
            return None

        for name_col, ticker_col in [("Name", "Code"), ("Name", "Symbol"), ("기업명", "종목코드")]:
            if name_col in listing.columns and ticker_col in listing.columns:
                ticker_row = listing[listing[name_col].str.strip() == company.strip()]
                if not ticker_row.empty:
                    return str(ticker_row.iloc[0][ticker_col]).zfill(6)

        st.error(f"'{company}'에 해당하는 티커 정보를 찾을 수 없습니다.")
        return None

    except Exception as e:
        st.error(f"티커 조회 중 오류 발생: {e}")
        return None

# ✅ 4. 네이버 금융 시간별 시세 크롤링 함수
def get_intraday_data_bs(ticker):
    base_url = f"https://finance.naver.com/item/sise_time.naver?code={ticker}&page="
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
    df["Date"] = datetime.today().strftime("%Y-%m-%d")
    df["Datetime"] = pd.to_datetime(df["Date"] + " " + df["Time"])
    df.set_index("Datetime", inplace=True)

    return df

# ✅ 5. 주가 시각화 함수
def plot_stock(df, company, period):
    if df is None or df.empty:
        st.warning(f"📉 {company} - 해당 기간({period})의 거래 데이터가 없습니다.")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df.index, df["Close"], marker="o", linestyle="-", color="b", label="체결가")
    ax.set_xlabel("시간" if period in ["1day", "week"] else "날짜")
    ax.set_ylabel("주가 (체결가)")
    ax.set_title(f"{company} 주가 ({period})")
    ax.legend()
    ax.grid()
    plt.xticks(rotation=45)

    st.pyplot(fig)

# ✅ 실행
if __name__ == '__main__':
    main()
