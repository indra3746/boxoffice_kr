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
    print("🎬 영화 데이터 정밀 추출 시작...")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # 1. 예매량 데이터 수집 (예매율 페이지)
        print("🎫 1/2 실시간 예매량 수집 중 (30초 대기)...")
        driver.get("https://www.kobis.or.kr/kobis/business/stat/boxs/findRealTicketList.do")
        time.sleep(30) # 예매 테이블은 로딩이 매우 느려 시간을 대폭 늘렸습니다.
        
        ticket_map = {}
        t_rows = driver.find_elements(By.CSS_SELECTOR, "#tbody_0 tr")
        for row in t_rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) > 4:
                # 제목에서 공백과 괄호 내용을 제거하여 매칭용 키 생성
                raw_title = cols[1].text.split('\n')[0].strip()
                title_key = raw_title.replace(" ", "").split('(')[0]
                # [4]번 칸이 예매매수입니다.
                ticket_map[title_key] = cols[4].text.strip()

        # 2. 박스오피스 당일/누적 관객수 수집
        print("📊 2/2 박스오피스 관객수 수집 중...")
        driver.get("https://www.kobis.or.kr/kobis/business/stat/boxs/findDailyBoxOfficeList.do")
        time.sleep(15)
        
        kst = pytz.timezone('Asia/Seoul')
        today = datetime.now(kst).date()
        final_data = []
        
        b_rows = driver.find_elements(By.CSS_SELECTOR, "#tbody_0 tr")
        for row in b_rows[:10]:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) > 10:
                # 정밀 타격 인덱스: [7]당일관객, [9]누적관객 (10번은 스크린수임 확인됨)
                rank = cols[0].text.strip()
                original_title = cols[1].text.split('\n')[0].strip()
                open_date_str = cols[2].text.strip()
                
                daily_aud = cols[7].text.strip() # 당일 관객수
                total_aud = cols[9].text.strip() # 누적 관객수 (사용자님의 1,897은 10번 칸이었음)
                
                # D+Day 계산
                try:
                    open_date = datetime.strptime(open_date_str, "%Y-%m-%d").date()
                    d_day = (today - open_date).days + 1
                    d_day_str = f"개봉 D+{d_day}"
                except: d_day_str = "개봉일 미정"
                
                # 제목 매칭 (공백 및 괄호 제거)
                match_key = original_title.replace(" ", "").split('(')[0]
                ticket_val = ticket_map.get(match_key, "0")
                
                final_data.append({
                    'rank': rank, 'title': original_title, 'open': open_date_str,
                    'dday': d_day_str, 'daily': daily_aud, 'total': total_aud, 'ticket': ticket_val
                })
        return final_data
    except Exception as e:
        print(f"❌ 수집 오류: {e}")
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
now_str = datetime.now(kst).strftime('%y.%m.%d %H시')

if movie_list:
    report = f"🎬 일일 박스오피스 및 예매 현황({now_str} 기준)\n"
    report += "━━━━━━━━━━━━━━━━━━\n"
    for m in movie_list:
        report += f"{m['rank']}️⃣ {m['title']} / 개봉일: {m['open']}({m['dday']})\n"
        report += f"- 당일 {m['daily']}명\n"
        report += f"- 누적 {m['total']}명\n"
        report += f"- 예매량 {m['ticket']}\n\n"
    report += "━━━━━━━━━━━━━━━━━━\n🔗 출처: KOBIS(영화관입장권 통합전산망)"
    send_msg(report)
