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
        # 📌 현재 주가
        try:
            current_price = soup.select_one(".no_today .blind").text.strip().replace(",", "")
        except:
            current_price = "N/A"

        # 📌 PER & PBR
        try:
            per = soup.select_one("#_per").text.strip() if soup.select_one("#_per") else "N/A"
            pbr = soup.select_one("#_pbr").text.strip() if soup.select_one("#_pbr") else "N/A"
        except:
            per, pbr = "N/A", "N/A"

        # 📌 52주 최고/최저
        try:
            high_52 = soup.select_one("th.title:-soup-contains('52주 최고') + td.num span.tah").text.strip()
            low_52 = soup.select_one("th.title:-soup-contains('52주 최저') + td.num span.tah").text.strip()
        except:
            high_52, low_52 = "N/A", "N/A"

        # 📌 시가총액
        try:
            market_cap = soup.select_one("#_sise_market_sum").text.strip().replace(",", "") + "억원"
        except:
            market_cap = "N/A"

        # 📌 BPS (주당순자산)
        try:
            bps = soup.select_one("th.h_th2.th_cop_anal18 + td.t_line.cell_strong").text.strip().replace(",", "")
        except:
            bps = "N/A"

        # 📌 주당배당금 가져오기
        try:
            dividend = soup.select_one("th.h_th2.th_cop_anal19 + td.t_line.cell_strong").text.strip().replace(",", "")
            dividend = float(dividend) if dividend != "-" else 0
        except:
            dividend = 0

        # 📌 배당수익률 계산 (주당 배당금 / 현재가 × 100)
        try:
            dividend_yield = round(dividend / float(current_price) * 100, 2) if dividend > 0 and current_price != "N/A" else "N/A"
        except:
            dividend_yield = "N/A"

        # 📌 부채비율 (전년도 기준, 3번째 값)
        try:
            debt_ratio = soup.select("th.h_th2.th_cop_anal14 + td")[2].text.strip().replace(",", "")
        except:
            debt_ratio = "N/A"

        # 📌 당기순이익 (전년도)
        try:
            net_income = soup.select_one("th.h_th2.th_cop_anal10 + td.t_line.cell_strong").text.strip().replace(",", "")
        except:
            net_income = "N/A"

        return {
            "현재가": f"{current_price}원" if current_price != "N/A" else "N/A",
            "PER": per,
            "PBR": pbr,
            "52주 최고": f"{high_52}원" if high_52 != "N/A" else "N/A",
            "52주 최저": f"{low_52}원" if low_52 != "N/A" else "N/A",
            "시가총액": market_cap,
            "BPS": f"{bps}원" if bps != "N/A" else "N/A",
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
