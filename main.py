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
from webdriver_manager.chrome import ChromeDriverManager

# 제목 정규화: 특수문자, 공백을 제거하여 순수 텍스트만 추출
def clean_title(text):
    if not text: return ""
    # 한글, 영문, 숫자만 남기고 제거
    return re.sub(r'[^가-힣A-Za-z0-9]', '', text.split('\n')[0]).strip()

def get_movie_report():
    print("🎬 영화 데이터 최종 정밀 수집 엔진 가동...")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # 1. 예매 현황 페이지 접속 (예매관객수 추출)
        print("🎫 1/2 예매율 페이지 분석 중 (35초 대기)...")
        driver.get("https://www.kobis.or.kr/kobis/business/stat/boxs/findRealTicketList.do")
        time.sleep(35) # 동적 로딩을 위해 대기 시간을 넉넉히 설정
        
        ticket_map = {}
        t_rows = driver.find_elements(By.CSS_SELECTOR, "#tbody_0 tr")
        for row in t_rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) > 6:
                # 스크린샷 기준 7번째 칸(Index 6)이 '예매관객수'
                raw_title = cols[1].text.strip()
                match_key = clean_title(raw_title)
                ticket_count = cols[6].text.strip()
                if match_key:
                    ticket_map[match_key] = ticket_count

        # 2. 일일 박스오피스 페이지 접속 (당일/누적 관객수 추출)
        print("📊 2/2 박스오피스 데이터 분석 중...")
        driver.get("https://www.kobis.or.kr/kobis/business/stat/boxs/findDailyBoxOfficeList.do")
        time.sleep(15)
        
        kst = pytz.timezone('Asia/Seoul')
        today = datetime.now(kst).date()
        final_data = []
        
        b_rows = driver.find_elements(By.CSS_SELECTOR, "#tbody_0 tr")
        for row in b_rows[:10]: # TOP 10만 수집
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) > 9:
                # 사용자 검증 완료 인덱스: [7]당일관객, [9]누적관객
                rank = cols[0].text.strip()
                title = cols[1].text.split('\n')[0].strip()
                open_date_str = cols[2].text.strip()
                daily_aud = cols[7].text.strip() # 당일 관객수
                total_aud = cols[9].text.strip() # 누적 관객수
                
                # D+Day 계산
                try:
                    open_date = datetime.strptime(open_date_str, "%Y-%m-%d").date()
                    d_day = (today - open_date).days + 1
                    d_day_str = f"개봉 D+{d_day}"
                except: d_day_str = "개봉일 미정"
                
                # 부분 일치 매칭 로직 (제목이 포함관계에 있으면 매칭)
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

# --- 실행부 ---
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
    print("✅ 발송 성공!")
else:
    print("⚠️ 데이터가 없어 발송하지 못했습니다.")
