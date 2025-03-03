import streamlit as st
import requests
from bs4 import BeautifulSoup

# 📌 네이버 금융에서 종목 주요 재무 데이터 가져오기
def get_stock_info(stock_code):
    """
    네이버 금융에서 특정 종목의 주요 재무 지표를 크롤링하여 반환
    """
    url = f"https://finance.naver.com/item/main.nhn?code={stock_code}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None  # 요청 실패 시 None 반환

    soup = BeautifulSoup(response.text, "html.parser")

    try:
        # 📌 현재 주가 가져오기
        current_price = soup.select_one(".no_today .blind").text.strip()

        # 📌 PER & PBR 가져오기
        per = soup.select_one("#_per").text.strip() if soup.select_one("#_per") else "N/A"
        pbr = soup.select_one("#_pbr").text.strip() if soup.select_one("#_pbr") else "N/A"

        # 📌 52주 최고/최저 가져오기
        try:
            high_52 = soup.select_one("table tr:nth-child(1) td em").text.strip()
            low_52 = soup.select_one("table tr:nth-child(2) td em").text.strip()
        except:
            high_52, low_52 = "N/A", "N/A"

        # 📌 시가총액 가져오기
        try:
            market_cap = soup.select_one("div.first dd").text.split()[1]
        except:
            market_cap = "N/A"

        # 📌 BPS (주당순자산)
        try:
            bps = soup.select("table tbody tr td em")[5].text.strip()
        except:
            bps = "N/A"

        # 📌 배당수익률 계산 (주당 배당금 / 현재가)
        try:
            dividend = soup.select("table tbody tr td em")[10].text.strip()
            dividend_yield = round(float(dividend) / float(current_price) * 100, 2) if dividend != "-" else "N/A"
        except:
            dividend_yield = "N/A"

        # 📌 부채비율 (전년도 기준)
        try:
            debt_ratio = soup.select("table tbody tr td em")[7].text.strip()
        except:
            debt_ratio = "N/A"

        # 📌 당기순이익 (전년도)
        try:
            net_income = soup.select("table tbody tr td em")[3].text.strip()
        except:
            net_income = "N/A"

        return {
            "현재가": current_price,
            "52주 최고": high_52,
            "52주 최저": low_52,
            "시가총액": market_cap,
            "PER": per,
            "PBR": pbr,
            "BPS": bps,
            "배당수익률": f"{dividend_yield}%" if dividend_yield != "N/A" else "N/A",
            "부채비율": f"{debt_ratio}%" if debt_ratio != "N/A" else "N/A",
            "당기순이익": f"{net_income}억 원" if net_income != "N/A" else "N/A"
        }
    except Exception as e:
        return None

# 📌 Streamlit UI
st.title("📈 국내 주식 분석 챗봇")
st.write("네이버 금융에서 주식 분봉 데이터를 가져오고, 주요 재무 지표를 확인합니다.")

stock_code = st.text_input("종목 코드 입력 (예: 삼성전자 005930)", "005930")

if st.button("📊 종목 정보 조회"):
    stock_info = get_stock_info(stock_code)
    if stock_info:
        st.write("📊 **종목 주요 정보**")
        for key, value in stock_info.items():
            st.write(f"**{key}:** {value}")
    else:
        st.error("❌ 주요 재무 데이터를 가져오지 못했습니다.")
