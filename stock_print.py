import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
import datetime
import plotly.express as px

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

        # 📌 52주 최고/최저
        high_52 = soup.select("table tbody tr td em")[0].text.strip()
        low_52 = soup.select("table tbody tr td em")[1].text.strip()

        # 📌 시가총액
        market_cap = soup.select("table tbody tr td em")[2].text.strip()

        # 📌 PER & PBR
        per_tag = soup.select_one("#_per")
        per = per_tag.text.strip() if per_tag else "N/A"

        pbr_tag = soup.select_one("#_pbr")
        pbr = pbr_tag.text.strip() if pbr_tag else "N/A"

        # 📌 BPS (주당순자산)
        bps = soup.select("table tbody tr td em")[5].text.strip()

        # 📌 배당수익률 계산 (주당 배당금 / 현재가)
        dividend_tag = soup.select("table tbody tr td em")[10]
        dividend = dividend_tag.text.strip() if dividend_tag else "0"
        
        try:
            dividend_yield = round(float(dividend) / float(current_price) * 100, 2) if dividend != "0" else "N/A"
        except:
            dividend_yield = "N/A"

        # 📌 부채비율 (전년도 기준)
        debt_ratio_tag = soup.select("table tbody tr td em")[7]
        debt_ratio = debt_ratio_tag.text.strip() if debt_ratio_tag else "N/A"

        # 📌 당기순이익 (전년도)
        net_income_tag = soup.select("table tbody tr td em")[3]
        net_income = net_income_tag.text.strip() if net_income_tag else "N/A"

        return {
            "현재가": current_price,
            "52주 최고": high_52,
            "52주 최저": low_52,
            "시가총액": market_cap,
            "PER": per,
            "PBR": pbr,
            "BPS": bps,
            "배당수익률": f"{dividend_yield}%" if dividend_yield != "N/A" else "N/A",
            "부채비율": f"{debt_ratio}%",
            "당기순이익": f"{net_income}억 원"
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
