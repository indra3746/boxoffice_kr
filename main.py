import os
import requests
import time
from datetime import datetime
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def get_movie_report():
    print("🎬 일일 박스오피스 데이터 수집 시작...")
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
        wait = WebDriverWait(driver, 60)
        
        # 박스오피스 페이지 접속
        driver.get("https://www.kobis.or.kr/kobis/business/stat/boxs/findDailyBoxOfficeList.do")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#tbody_0 tr td")))
        time.sleep(10) # 렌더링 대기
        
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
                daily_aud = cols[7].text.strip() # 당일 관객수
                total_aud = cols[9].text.strip() # 누적 관객수
                
                try:
                    open_date = datetime.strptime(open_date_str, "%Y-%m-%d").date()
                    d_day = (today - open_date).days + 1
                    d_day_str = f"개봉 D+{d_day}"
                except: d_day_str = "개봉일 미정"
                
                final_data.append({
                    'rank': rank, 'title': title, 'open': open_date_str,
                    'dday': d_day_str, 'daily': daily_aud, 'total': total_aud
                })
        return final_data
    except Exception as e:
        print(f"❌ 수집 중 오류: {e}")
        return []
    finally:
        if 'driver' in locals(): driver.quit()

def send_msg(content):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    if not token or not chat_id:
        print("❌ 환경 변수 설정 오류")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": content})

# 실행 및 리포트 구성
movie_list = get_movie_report()
kst = pytz.timezone('Asia/Seoul')
now_str = datetime.now(kst).strftime('%y.%m.%d %H시')

if movie_list:
    report = f"🎬 일일 박스오피스 현황({now_str} 기준)\n"
    report += "━━━━━━━━━━━━━━━━━━\n"
    for m in movie_list:
        report += f"{m['rank']}️⃣ {m['title']}\n"
        report += f"- 개봉일: {m['open']}({m['dday']})\n"
        report += f"- 당일 {m['daily']}명\n"
        report += f"- 누적 {m['total']}명\n\n"
    report += "━━━━━━━━━━━━━━━━━━\n🔗 출처: KOBIS"
    send_msg(report)
    print("✅ 리포트 발송 완료!")
