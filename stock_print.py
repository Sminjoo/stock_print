import streamlit as st
import requests
import time
import mplfinance as mpf
import FinanceDataReader as fdr
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd

# ✅ 1. 한글 폰트 설정
def set_korean_font():
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
    if not os.path.exists(font_path):  
        os.system("apt-get update -qq")
        os.system("apt-get install fonts-nanum* -qq")

    fe = fm.FontEntry(fname=font_path, name="NanumGothic")
    fm.fontManager.ttflist.insert(0, fe)  
    plt.rcParams.update({"font.family": "NanumGothic", "axes.unicode_minus": False})

set_korean_font()  # ✅ 한 번만 실행

# ✅ 2. 메인 실행 함수
def main():
    st.set_page_config(page_title="Stock Price Visualization", page_icon=":chart_with_upwards_trend:")
    st.title("_주가 시각화_ :chart_with_upwards_trend:")

    with st.sidebar:
        company_name = st.text_input("분석할 기업명 (코스피 상장)")
        process = st.button("시각화 시작")

    if process:
        if not company_name:
            st.info("기업명을 입력해주세요.")
            st.stop()

        st.subheader(f"📈 {company_name} 최근 주가 추이")

        # ✅ 반응형 UI 버튼 추가 (선택한 기간을 즉시 반영)
        selected_period = st.radio(
            "기간 선택",
            options=["1day", "week", "1month", "1year"],
            horizontal=True
        )

        # ✅ 주가 데이터를 가져오고 시각화
        with st.spinner(f"📊 {company_name} ({selected_period}) 데이터 불러오는 중..."):
            ticker = get_ticker(company_name)
            if not ticker:
                st.error("해당 기업의 티커 코드를 찾을 수 없습니다.")
                st.stop()

            df = None
            try:
                if selected_period in ["1day", "week"]:
                    df = get_intraday_data_bs(ticker)  # ✅ Requests 기반 크롤링 적용
                else:
                    end_date = datetime.now().strftime('%Y-%m-%d')
                    start_date = (datetime.now() - timedelta(days=30 if selected_period == "1month" else 365)).strftime('%Y-%m-%d')
                    df = fdr.DataReader(ticker, start_date, end_date)

                if df is None or df.empty:
                    st.warning(f"📉 {company_name} ({ticker}) - 해당 기간({selected_period})의 거래 데이터가 없습니다.")
                else:
                    visualize_stock(df, company_name, selected_period)

            except Exception as e:
                st.error(f"주가 데이터를 불러오는 중 오류 발생: {e}")

# ✅ 3. 주가 시각화 & 티커 조회 함수
def get_ticker(company):
    """
    FinanceDataReader를 통해 KRX 상장 기업 정보를 불러오고,
    입력한 기업명에 해당하는 티커 코드를 반환합니다.
    """
    try:
        listing = fdr.StockListing('KRX')
        if listing.empty:
            listing = fdr.StockListing('KOSPI')
        
        if listing.empty:
            st.error("상장 기업 정보를 불러올 수 없습니다.")
            return None

        # 컬럼명 처리 (KRX 데이터 컬럼명 기준)
        for name_col, ticker_col in [("Name", "Code"), ("Name", "Symbol"), ("기업명", "종목코드")]:
            if name_col in listing.columns and ticker_col in listing.columns:
                ticker_row = listing[listing[name_col].str.strip() == company.strip()]
                if not ticker_row.empty:
                    ticker = str(ticker_row.iloc[0][ticker_col]).zfill(6)
                    st.write(f"✅ 가져온 티커 코드: {ticker}")
                    return ticker

        st.error(f"'{company}'에 해당하는 티커 정보를 찾을 수 없습니다. \n예: '삼성전자' 입력 시 '005930' 반환")
        return None

    except Exception as e:
        st.error(f"티커 조회 중 오류 발생: {e}")
        return None

# ✅ 4. 네이버 금융 시간별 시세 크롤링 함수 (Requests 사용)
def get_intraday_data_bs(ticker):
    """
    네이버 금융에서 시간별 체결가 데이터를 가져와 DataFrame으로 반환 (Selenium 없이 Requests 사용)
    :param ticker: 종목코드 (예: '035720' - 카카오)
    :return: DataFrame (Datetime, Close, Volume)
    """
    base_url = f"https://finance.naver.com/item/sise_time.naver?code={ticker}&page="
    headers = {"User-Agent": "Mozilla/5.0"}
    
    price = []  # 체결가 저장 리스트
    volume = []  # 거래량 저장 리스트
    times = []  # 체결 시간 저장 리스트
    page = 1  # 첫 번째 페이지부터 시작

    while True:
        url = base_url + str(page)
        res = requests.get(url, headers=headers)
        time.sleep(1)  # 네이버 서버 부하 방지를 위해 1초 대기

        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.select("table.type2 tr")

        # 데이터가 없거나 마지막 페이지면 종료
        if not rows or "체결시각" in rows[0].text:
            break

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 6:  # 데이터가 부족하면 무시
                continue  

            try:
                time_str = cols[0].text.strip()  # HH:MM 형식의 시간
                close_price = int(cols[1].text.replace(",", ""))  # 체결가
                volume_data = int(cols[5].text.replace(",", ""))  # 거래량

                times.append(time_str)
                price.append(close_price)
                volume.append(volume_data)

            except ValueError:
                continue

        page += 1  # 다음 페이지로 이동

    # ✅ DataFrame 생성 및 정리
    if not price or not volume:
        return pd.DataFrame()

    df = pd.DataFrame({"Time": times, "Close": price, "Volume": volume})
    df["Date"] = datetime.today().strftime("%Y-%m-%d")  # 날짜 추가
    df["Datetime"] = pd.to_datetime(df["Date"] + " " + df["Time"])  # 시간 합치기
    df.set_index("Datetime", inplace=True)
    df = df[["Close", "Volume"]]  # 필요한 열만 남기기

    return df

# ✅ 5. 주가 시각화 함수
def visualize_stock(df, company, period):
    """
    가져온 주가 데이터를 기반으로 시각화
    :param df: 주가 데이터 DataFrame
    :param company: 기업명
    :param period: 기간 (1day, week, 1month, 1year)
    """
    if df is None or df.empty:
        st.warning(f"📉 {company} - 해당 기간({period})의 거래 데이터가 없습니다.")
        return

    fig, _ = mpf.plot(df, type='line' if period in ["1day", "week"] else 'candle',
                       style='charles', title=f"{company} 주가 ({period})",
                       volume=True, returnfig=True)
    st.pyplot(fig)

# ✅ 실행
if __name__ == '__main__':
    main()