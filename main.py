import os
import requests
import time
import re
from datetime import datetime
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 제목 정규화: 특수문자와 공백을 제거하여 매칭용 데이터 생성
def clean_title(text):
    if not text: return ""
    # "상세보기" 등 불필요한 단어 제거 및 특수문자 삭제
    clean = text.replace("상세보기", "").strip()
    return re.sub(r'[^가-힣A-Za-z0-9]', '', clean.split('\n')[0])

def get_movie_report():
    print("🎬 영화 데이터 정밀 수집 엔진 가동 (최종 보강판)...")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 40)
        
        # 1. 예매 현황 페이지 접속 (예매관객수 추출)
        print("🎫 1/2 예매율 페이지 분석 중...")
        driver.get("https://www.kobis.or.kr/kobis/business/stat/boxs/findRealTicketList.do")
        
        # 테이블이 나타날 때까지 대기
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#tbody_0 tr")))
        time.sleep(10) # 렌더링을 위해 추가 대기
        
        ticket_map = {}
        t_rows = driver.find_elements(By.CSS_SELECTOR, "#tbody_0 tr")
        print(f"로그: 예매 페이지에서 {len(t_rows)}개의 영화를 발견했습니다.")
        
        for row in t_rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) > 6:
                # 스크린샷 7번째 칸(Index 6) 타격
                raw_title = cols[1].text.strip()
                match_key = clean_title(raw_title)
                ticket_count = cols[6].text.strip()
                if match_key:
                    ticket_map[match_key] = ticket_count

        # 2. 일일 박스오피스 페이지 접속 (당일/누적 관객수 추출)
        print("📊 2/2 박스오피스 데이터 분석 중...")
        driver.get("https://www.kobis.or.kr/kobis/business/stat/boxs/findDailyBoxOfficeList.do")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#tbody_0 tr")))
        time.sleep(5)
        
        kst = pytz.timezone('Asia/Seoul')
        today = datetime.now(kst).date()
        final_data = []
        
        b_rows = driver.find_elements(By.CSS_SELECTOR, "#tbody_0 tr")
        for row in b_rows[:10]:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) > 9:
                # 검증된 인덱스: [7]당일관객, [9]누적관객
                rank = cols[0].text.strip()
                title = cols[1].text.split('\n')[0].strip()
                open_date_str = cols[2].text.strip()
                daily_aud = cols[7].text.strip()
                total_aud = cols[9].text.strip()
                
                # D+Day 계산
                try:
                    open_date = datetime.strptime(open_date_str, "%Y-%m-%d").date()
                    d_day = (today - open_date).days + 1
                    d_day_str = f"개봉 D+{d_day}"
                except: d_day_str = "개봉일 미정"
                
                # 유연한 제목 매칭 (한 글자라도 겹치면 매칭 성공)
                search_key = clean_title(title)
                ticket_val = "0"
                for k, v in ticket_map.items():
                    if search_key in k or k in search_key:
                        ticket_val = v
                        break
                
                final_data.append({
                    'rank': rank, 'title': title, 'open': open_date_str,
                    'dday': d_day_str, 'daily': daily_aud, 'total': total_aud, 'ticket': ticket_val
                })
        return final_data
        
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

# 실행 및 리포트 구성
movie_list = get_movie_report()
kst = pytz.timezone('Asia/Seoul')
now_str = datetime.now(kst).strftime('%y.%m.%d %H시')

if movie_list:
    report = f"🎬 일일 박스오피스 및 예매 현황({now_str} 기준)\n"
    report += "━━━━━━━━━━━━━━━━━━\n"
    for m in movie_list:
        report += f"{m['rank']}️⃣ {m['title']}\n"
        report += f"- 개봉일: {m['open']}({m['dday']})\n"
        report += f"- 당일 {m['daily']}명\n"
        report += f"- 누적 {m['total']}명\n"
        report += f"- 예매량 {m['ticket']}\n\n"
    report += "━━━━━━━━━━━━━━━━━━\n🔗 출처: KOBIS(영화관입장권 통합전산망)"
    send_msg(report)
    print("✅ 발송 완료!")
