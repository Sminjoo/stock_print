import requests

def check_naver_chart_data(stock_code, minute="5", days=5):
    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={stock_code}&timeframe=minute&count={days * 78}&requestType=0"
    response = requests.get(url)
    data = response.text.split("\n")[3:-2]  # XML 형태로 들어오는 데이터 가공

    print("📌 원본 데이터 샘플 5개 출력:")
    for row in data[:5]:  # 5개만 출력해서 확인
        print(row)

# 삼성전자(005930) 5분봉 데이터 확인
check_naver_chart_data("005930", "5", 5)
