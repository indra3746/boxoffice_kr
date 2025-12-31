import os
import requests
import time
from datetime import datetime
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def get_movie_report():
    print("🎬 영화 데이터 수집을 시작합니다...")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # 1. 일일 박스오피스 순위 수집 (전날 기준)
        driver.get("https://www.kobis.or.kr/kobis/business/stat/boxs/findDailyBoxOfficeList.do")
        time.sleep(15)
        
        movie_dict = {}
        rows = driver.find_elements(By.CSS_SELECTOR, "#tbody_0 tr")
        
        for row in rows[:10]:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) > 5:
                rank = cols[0].text.strip()
                title = cols[1].text.strip()
                open_date = cols[2].text.strip()
                audience = cols[4].text.strip()
                movie_dict[title] = {
                    'rank': rank,
                    'open': open_date,
                    'audience': audience,
                    'ticket': "정보없음" # 예매량 초기값
                }

        # 2. 실시간 예매율 페이지에서 예매량 수집
        driver.get("https://www.kobis.or.kr/kobis/business/stat/boxs/findRealTicketList.do")
        time.sleep(15)
        
        ticket_rows = driver.find_elements(By.CSS_SELECTOR, "#tbody_0 tr")
        for t_row in ticket_rows:
            t_cols = t_row.find_elements(By.TAG_NAME, "td")
            if len(t_cols) > 5:
                t_title = t_cols[1].text.strip()
                t_count = t_cols[4].text.strip() # 실시간 예매량
                
                # 기존 박스오피스 리스트에 있는 영화라면 예매량 업데이트
                if t_title in movie_dict:
                    movie_dict[t_title]['ticket'] = t_count

        return movie_dict
    except Exception as e:
        print(f"❌ 데이터 수집 중 오류: {e}")
        return {}
    finally:
        if 'driver' in locals(): driver.quit()

def send_msg(content):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": content})

# 실행 및 리포트 구성
movie_data = get_movie_report()
kst = pytz.timezone('Asia/Seoul')
now = datetime.now(kst)
date_str = now.strftime('%y.%m.%d %H시') # 예시: 25.12.31 08시

if movie_data:
    report = f"🎬 일일 박스오피스 및 예매 현황\n"
    report += f"📅 리포트 생성: {now.strftime('%Y-%m-%d %H:%M')}\n"
    report += "━━━━━━━━━━━━━━━━━━\n\n"
    
    # 딕셔너리를 순위순으로 정렬하여 출력
    sorted_movies = sorted(movie_data.items(), key=lambda x: int(x[1]['rank']))
    
    for title, info in sorted_movies:
        # 번호 이모지
        num_emoji = f"{info['rank']}️⃣"
        
        # 1. 순위 제목 / 관객수 / 예매량(기준일시)
        report += f"{num_emoji} {title} / 관객 {info['audience']}명 / 예매량 {info['ticket']}({date_str} 기준)\n"
        
        # 2. 개봉일
        report += f"개봉일: {info['open']}\n"
        
        # 3. 줄간격
        report += "\n"
        
    report += "━━━━━━━━━━━━━━━━━━\n"
    report += "🔗 데이터 출처: KOBIS(영화관입장권 통합전산망)"
    
    send_msg(report)
    print("✅ 영화 리포트 발송 완료!")
else:
    print("⚠️ 발송할 데이터가 없습니다.")
