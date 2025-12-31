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

# 제목 정규화: 매칭 정확도를 위해 특수문자와 공백을 제거
def clean_title(text):
    if not text: return ""
    clean = text.replace("상세보기", "").strip()
    return re.sub(r'[^가-힣A-Za-z0-9]', '', clean.split('\n')[0])

def get_movie_report():
    print("🎬 영화 데이터 수집 시작 (재시도 로직 강화 버전)...")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 90) # 대기 시간을 90초로 대폭 상향
        
        # 1. 예매 현황 페이지 접속 (재시도 3회 적용)
        ticket_map = {}
        for attempt in range(3):
            try:
                print(f"🎫 1/2 예매율 페이지 접속 중... (시도 {attempt+1}/3)")
                driver.get("https://www.kobis.or.kr/kobis/business/stat/boxs/findRealTicketList.do")
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#tbody_0 tr")))
                time.sleep(15) # 렌더링 추가 대기
                
                t_rows = driver.find_elements(By.CSS_SELECTOR, "#tbody_0 tr")
                for row in t_rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) > 6:
                        # 스크린샷 기준 7번째 칸(Index 6)이 '예매관객수'
                        m_key = clean_title(cols[1].text)
                        ticket_map[m_key] = cols[6].text.strip()
                if ticket_map: break
            except Exception as e:
                print(f"⚠️ 시도 {attempt+1} 실패, 다시 시도합니다...")
                time.sleep(5)

        # 2. 박스오피스 페이지 접속
        print("📊 2/2 박스오피스 데이터 분석 중...")
        driver.get("https://www.kobis.or.kr/kobis/business/stat/boxs/findDailyBoxOfficeList.do")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#tbody_0 tr")))
        time.sleep(10)
        
        kst = pytz.timezone('Asia/Seoul')
        today = datetime.now(kst).date()
        final_data = []
        
        b_rows = driver.find_elements(By.CSS_SELECTOR, "#tbody_0 tr")
        for row in b_rows[:10]:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) > 9:
                rank = cols[0].text.strip()
                title = cols[1].text.split('\n')[0].strip()
                open_date_str = cols[2].text.strip()
                # [7]당일관객, [9]누적관객 (사용자 결과 기반)
                daily_aud = cols[7].text.strip()
                total_aud = cols[9].text.strip()
                
                try:
                    open_date = datetime.strptime(open_date_str, "%Y-%m-%d").date()
                    d_day = (today - open_date).days + 1
                    d_day_str = f"개봉 D+{d_day}"
                except: d_day_str = "개봉일 미정"
                
                search_key = clean_title(title)
                ticket_val = ticket_map.get(search_key, "0")
                
                # 부분 일치 매칭 (한 번 더 시도)
                if ticket_val == "0":
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
        print(f"❌ 치명적 오류 발생: {e}")
        return []
    finally:
        if 'driver' in locals(): driver.quit()

def send_msg(content):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": content})

# 실행부
movie_list = get_movie_report()
kst = pytz.timezone('Asia/Seoul')
now_str = datetime.now(kst).strftime('%y.%m.%d %H시')
