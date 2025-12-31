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

def clean_title(text):
    if not text: return ""
    clean = text.replace("상세보기", "").strip()
    return re.sub(r'[^가-힣A-Za-z0-9]', '', clean.split('\n')[0])

def get_movie_report():
    print("🎬 영화 데이터 정밀 수집 엔진 가동 (우회 로직 상시 적용)...")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    # [기본] 봇 감지 우회 설정
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        wait = WebDriverWait(driver, 45)
        
        ticket_map = {}
        for attempt in range(3):
            try:
                print(f"🎫 1/2 예매율 페이지 분석 중... (시도 {attempt+1}/3)")
                driver.get("https://www.kobis.or.kr/kobis/business/stat/boxs/findRealTicketList.do")
                wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#tbody_0 tr")))
                time.sleep(10)
                
                t_rows = driver.find_elements(By.CSS_SELECTOR, "#tbody_0 tr")
                for row in t_rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) > 6:
                        m_key = clean_title(cols[1].text)
                        # 스크린샷 7번째 칸(Index 6) 예매관객수 추출
                        ticket_map[m_key] = cols[6].text.strip()
                if ticket_map: break
            except: time.sleep(5)

        print("📊 2/2 박스오피스 데이터 분석 중...")
        driver.get("https://www.kobis.or.kr/kobis/business/stat/boxs/findDailyBoxOfficeList.do")
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#tbody_0 tr")))
        time.sleep(5)
        
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
                daily_aud = cols[7].text.strip() # 당일
                total_aud = cols[9].text.strip() # 누적
                
                try:
                    open_date = datetime.strptime(open_date_str, "%Y-%m-%d").date()
                    d_day = (today - open_date).days + 1
                    d_day_str = f"개봉 D+{d_day}"
                except: d_day_str = "개봉일 미정"
                
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
        print(f"❌ 수집 오류: {e}")
        return []
    finally:
        if 'driver' in locals(): driver.quit()

def send_msg(content):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    
    if not token or not chat_id:
        print("❌ 오류: TELEGRAM_TOKEN 또는 CHAT_ID 환경 변수가 설정되지 않았습니다.")
        print("💡 .github/workflows/*.yml 파일에 env 설정이 누락되었는지 확인하세요.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(url, json={"chat_id": chat_id, "text": content})
    
    if response.status_code == 200:
        print("✅ 텔레그램 리포트 발송 성공!")
        return True
    else:
        print(f"❌ 텔레그램 전송 실패! 응답 코드: {response.status_code}")
        print(f"📄 응답 내용: {response.text}")
        return False

# 실행부
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
    report += "━━━━━━━━━━━━━━━━━━\n🔗 출처: KOBIS"
    send_msg(report)
else:
    print("⚠️ 수집된 데이터가 없어 발송하지 않았습니다.")

# === END OF CODE ===
