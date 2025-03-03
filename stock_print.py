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

        # 📌 PER, PBR (동종업종비교에서 가져오기)
        try:
            per = soup.find("h4", class_="h_sub sub_tit7").find_next("table").find_all("td")[10].text.strip()
            pbr = soup.find("h4", class_="h_sub sub_tit7").find_next("table").find_all("td")[11].text.strip()
        except:
            per, pbr = "N/A", "N/A"

        # 📌 시가총액 (동종업종비교에서 가져오기)
        try:
            market_cap = soup.find("h4", class_="h_sub sub_tit7").find_next("table").find_all("td")[4].text.strip()
            market_cap = f"{int(market_cap.replace(',', '')) / 10000:.2f}조 원"  # 억 원 → 조 원 변환
        except:
            market_cap = "N/A"

        # 📌 52주 최고/최저 (주요 시세에서 가져오기)
        try:
            high_52 = soup.find("strong", text="주요시세").find_next("table").find_all("td")[0].text.strip()
            low_52 = soup.find("strong", text="주요시세").find_next("table").find_all("td")[1].text.strip()
        except:
            high_52, low_52 = "N/A", "N/A"

        # 📌 최신 연도의 기업실적분석 (당기순이익, 부채비율, BPS, 주당배당금)
        try:
            financial_table = soup.find("h4", class_="h_sub sub_tit6").find_next("table")

            # 테이블에서 모든 행을 가져온 후, 최신 연도 값 선택
            rows = financial_table.find_all("tr")

            # 📌 당기순이익
            net_income = rows[3].find_all("td")[-1].text.strip().replace(",", "")

            # 📌 부채비율
            debt_ratio = rows[7].find_all("td")[-1].text.strip().replace(",", "")

            # 📌 BPS (주당순자산)
            bps = rows[10].find_all("td")[-1].text.strip().replace(",", "")

            # 📌 주당배당금
            dividend = rows[13].find_all("td")[-1].text.strip().replace(",", "")
            dividend = float(dividend) if dividend != "-" else 0
        except:
            net_income, debt_ratio, bps, dividend = "N/A", "N/A", "N/A", 0

        # 📌 배당수익률 계산 (주당 배당금 / 현재가 × 100)
        try:
            dividend_yield = round(dividend / float(current_price) * 100, 2) if dividend > 0 and current_price != "N/A" else "N/A"
        except:
            dividend_yield = "N/A"

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
