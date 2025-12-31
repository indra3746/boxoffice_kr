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

# 제목 정규화 함수 (공백 및 특수문자 제거)
def normalize_title(text):
    return re.sub(r'[^가-힣A-Za-z0-9]', '', text)

def get_movie_report():
    print("🎬 영화 데이터 정밀 수집 및 포맷팅 시작...")
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
        time.sleep(30)
        
        ticket_map = {}
        t_rows = driver.find_elements(By.CSS_SELECTOR, "#tbody_0 tr")
        for row in t_rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) > 4:
                clean_key = normalize_title(cols[1].text)
                ticket_map[clean_key] = cols[4].text.strip()

        # 2. 박스오피스 당일/누적 관객수 수집
        print("📊 2/2 박스오피스 데이터 수집 중...")
        driver.get("https://www.kobis.or.kr/kobis/business/stat/boxs/findDailyBoxOfficeList.do")
        time.sleep(15)
        
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
                daily_aud = cols[7].text.strip()
                total_aud = cols[9].text.strip()
                
                # D+Day 계산
                try:
                    open_date = datetime.strptime(open_date_str, "%Y-%m-%d").date()
                    d_day = (today - open_date).days + 1
                    d_day_str = f"개봉 D+{d_day}"
                except: d_day_str = "개봉일 미정"
