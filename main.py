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
    print("🎬 영화 데이터 정밀 수집을 시작합니다...")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # 1. 예매 현황 페이지 접속 (예매량 추출)
        print("🎫 1/2 예매량 데이터 수집 중...")
        driver.get("https://www.kobis.or.kr/kobis/business/stat/boxs/findRealTicketList.do")
        time.sleep(20) # 테이블 완전 로딩 대기
        
        ticket_map = {}
        t_rows = driver.find_elements(By.CSS_SELECTOR, "#tbody_0 tr")
        for row in t_rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) > 4:
                # [1]제목, [4]예매량(매수)
                title = cols[1].text.strip().replace(" ", "")
                amount = cols[4].text.strip()
                ticket_map[title] = amount

        # 2. 일일 박스오피스 페이지 접속 (관객수 추출)
        print("📊 2/2 관객수 데이터 수집 중...")
        driver.get("https://www.kobis.or.kr/kobis/business/stat/boxs/findDailyBoxOfficeList.do")
        time.sleep(15)
        
        final_list = []
        b_rows = driver.find_elements(By.CSS_SELECTOR, "#tbody_0 tr")
        for row in b_rows[:10]:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) > 5:
                # [0]순위, [1]제목, [2]개봉일, [5]관객수
                rank = cols[0].text.strip()
                original_title = cols[1].text.strip().split('\n')[0]
                open_date = cols[2].text.strip()
                audience = cols[5].text.strip() # 실제 '명' 단위 관객수
                
                # 제목 매칭 (공백 제거 기준)
                match_title = original_title.replace(" ", "")
                ticket_val = ticket_map.get(match_title, "데이터없음")
                
                final_list.append({
                    'rank': rank,
                    'title': original_title,
                    'open': open_date,
                    'audience': audience,
                    'ticket': ticket_val
                })
        return final_list

    except Exception as e:
        print(f"❌ 오류: {e}")
        return []
    finally:
        if 'driver' in locals(): driver.quit()

def send_msg(content):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": content})

# 실행부
movie_data = get_movie_report()
kst = pytz.timezone('Asia/Seoul')
now = datetime.now(kst)
time_tag = now.strftime('%y.%m.%d %H시')

if movie_data:
    report = f"🎬 일일 박스오피스 및 예매 현황\n"
    report += "━━━━━━━━━━━━━━━━━━\n\n"
    for m in movie_data:
        # 요청하신 양식: 1️⃣ 제목 / 관객 00명 / 예매량 00(날짜 기준)
        report += f"{m['rank']}️⃣ {m['title']} / 관객 {m['audience']}명 / 예매량 {m['ticket']}({time_tag} 기준)\n"
        report += f"개봉일: {m['open']}\n\n"
    
    report += "━━━━━━━━━━━━━━━━━━\n"
    report += "🔗 출처: KOBIS(영화관입장권 통합전산망)"
    send_msg(report)
else:
    print("⚠️ 수집 실패")
