import os
import requests
import time
from datetime import datetime, timedelta
import pytz

def get_movie_report_api():
    print("🎬 KOBIS API로 박스오피스 데이터 수집 시작...")
    
    api_key = "c3f72afa541bc5ffbfaafabe41cc667d"
    
    kst = pytz.timezone('Asia/Seoul')
    today = datetime.now(kst)
    yesterday = today - timedelta(days=1)
    target_dt = yesterday.strftime('%Y%m%d')
    
    url = f"http://kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key={api_key}&targetDt={target_dt}"
    
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'faultInfo' in data:
                print(f"❌ API 에러: {data['faultInfo']['message']}")
                return []
                
            final_data = []
            movie_list = data['boxOfficeResult']['dailyBoxOfficeList']
            
            for m in movie_list[:10]:
                rank = m['rank']
                title = m['movieNm']
                open_date_str = m['openDt'] # YYYY-MM-DD
                
                daily_aud = format(int(m['audiCnt']), ',')
                total_aud = format(int(m['audiAcc']), ',')
                
                try:
                    open_date = datetime.strptime(open_date_str, "%Y-%m-%d").date()
                    d_day = (today.date() - open_date).days
                    d_day_str = f"개봉 D+{d_day}" if d_day > 0 else "개봉 1일차"
                except: 
                    d_day_str = "개봉일 미정"
                    
                final_data.append({
                    'rank': rank, 'title': title, 'open': open_date_str,
                    'dday': d_day_str, 'daily': daily_aud, 'total': total_aud
                })
                
            return final_data
            
        except requests.exceptions.Timeout:
            print(f"⚠️ KOBIS 서버 응답 지연! ({attempt+1}/{max_retries} 재시도 중...)")
            time.sleep(5)
        except Exception as e:
            print(f"❌ 수집 중 오류: {e}")
            break
            
    return []

def send_msg(content):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    if not token or not chat_id:
        print("❌ 텔레그램 환경 변수(Secrets) 설정 오류")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": content})

def main():
    movie_list = get_movie_report_api()
    
    # 날짜 세팅 (오늘 기준 시간 및 어제 날짜 계산)
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst)
    yesterday = now - timedelta(days=1)
    
    now_str = now.strftime('%y.%m.%d %H시')
    target_date_str = f"{yesterday.strftime('%y')}년 {yesterday.month}월 {yesterday.day}일"

    if movie_list:
        # 💡 사용자님이 요청하신 새로운 헤더 포맷 적용!
        report = f"🎬 {target_date_str} 일일 박스오피스 현황({now_str} 기준)\n"
        report += "━━━━━━━━━━━━━━━━━━\n"
        
        for m in movie_list:
            rank_emoji = f"{m['rank']}️⃣" if int(m['rank']) < 10 else "🔟"
            
            report += f"{rank_emoji} {m['title']}\n"
            report += f"- 개봉일: {m['open']}({m['dday']})\n"
            report += f"- 당일 {m['daily']}명\n"
            report += f"- 누적 {m['total']}명\n\n"
            
        report += "━━━━━━━━━━━━━━━━━━\n🔗 출처: KOBIS 오픈 API"
        
        print(report)
        send_msg(report)
        print("✅ 리포트 발송 완료!")
    else:
        print("❌ 전송할 데이터가 없습니다.")

if __name__ == "__main__":
    main()
