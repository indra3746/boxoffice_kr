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
    print("🎬 영화 데이터 통합 수집 시작...")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # 1. 실시간 예매율 페이지 먼저 방문 (데이터가 더 늦게 뜸)
        print("🎫 1/2 실시간 예매 현황 수집 중...")
        driver.get("https://www.kobis.or.kr/kobis/business/stat/boxs/findRealTicketList.do")
        time.sleep(20) # 예매 데이터 로딩을 위해 20초 대기
        
        ticket_dict = {}
        t_rows = driver.find_elements(By.CSS_SELECTOR, "#tbody_0 tr")
        for t_row in t_rows:
            t_cols = t_row.find_elements(By.TAG_NAME, "td")
            if len(t_cols) > 5:
                # 제목에서 공백을 제거하여 매칭 확률을 높임
                raw_title = t_cols[1].text.strip()
                clean_title = raw_title.replace(" ", "")
                ticket_count = t_cols[4].text.strip() # 예매량
                ticket_dict[clean_title] = ticket_count

        # 2. 일일 박스오피스 순위 수집
        print("📊 2/2 일일 박스오피스 순위 수집 중...")
        driver.get("https://www.kobis.or.kr/kobis/business/stat/boxs/findDailyBoxOfficeList.do")
        time.sleep(15)
        
        final_report_data = []
        rows = driver.find_elements(By.CSS_SELECTOR, "#tbody_0 tr")
        
        for row in rows[:10]:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) > 5:
                rank = cols[0].text.strip()
                title = cols[1].text.strip()
                open_date = cols[2].text.strip()
                audience = cols[4].text.strip()
                
                # 공백 제거 후 예매량 매칭 시도
                clean_target = title.replace(" ", "")
                ticket = ticket_dict.get(clean_target, "0")
                
                final_report_data.append({
                    'rank': rank,
                    'title': title,
                    'open': open_date,
                    'audience': audience,
                    'ticket': ticket
                })

        return final_report_data
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return []
    finally:
        if 'driver' in locals(): driver.quit()

def send_msg(content):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": content})

# 실행부
movie_list = get_movie_report()
kst = pytz.timezone('Asia/Seoul')
now = datetime.now(kst)
date_tag = now.strftime('%y.%m.%d %H시')

if movie_list:
    report = f"🎬 일일 박스오피스 및 예매 현황\n"
    report += "━━━━━━━━━━━━━━━━━━\n\n"
    
    for m in movie_list:
        # 1️⃣ 제목 / 관객 00명 / 예매량 00(날짜 기준)
        report += f"{m['rank']}️⃣ {m['title']} / 관객 {m['audience']}명 / 예매량 {m['ticket']}({date_tag} 기준)\n"
        # 개봉일
        report += f"개봉일: {m['open']}\n\n"
    
    report += "━━━━━━━━━━━━━━━━━━\n"
    report += "🔗 출처: KOBIS 통합전산망"
    
    send_msg(report)
    print("✅ 발송 완료!")
else:
    print("⚠️ 데이터 수집 실패")
