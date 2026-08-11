import os
import sys
import time
import requests
from datetime import datetime, timedelta
import pytz

# 1. 텔레그램 전송 함수 (에러 제보용으로 상단 배치)
def send_msg(content):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    
    if not token or not chat_id:
        print("❌ 텔레그램 환경 변수(Secrets) 설정 오류")
        sys.exit(1)
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": content})
    except Exception as e:
        print(f"❌ 텔레그램 전송 실패: {e}")

# 2. KOBIS API 수집 함수
def get_movie_report_api():
    print("🎬 KOBIS API로 박스오피스 데이터 수집 시작...")
    
    # Secrets 우선 적용, 없을 경우 기본 API 키 사용
    api_key = os.environ.get("KOBIS_API_KEY", "c3f72afa541bc5ffbfaafabe41cc667d")
    
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
            
            # 🚨 KOBIS API 키 한도 초과 또는 서버 장애 시 텔레그램으로 에러 내용 즉시 제보
            if 'faultInfo' in data:
                err_msg = f"❌ KOBIS API 에러 발생!\n메시지: {data['faultInfo']['message']}"
                print(err_msg)
                send_msg(err_msg)
                sys.exit(1) # GitHub Actions 재시도 유도
                
            final_data = []
            movie_list = data.get('boxOfficeResult', {}).get('dailyBoxOfficeList', [])
            
            if not movie_list:
                err_msg = "❌ KOBIS 박스오피스 데이터가 비어있습니다."
                print(err_msg)
                send_msg(err_msg)
                sys.exit(1)
            
            for m in movie_list[:10]:
                rank = m['rank']
                title = m['movieNm']
                open_date_str = m.get('openDt', '') # YYYY-MM-DD
                
                daily_aud = format(int(m.get('audiCnt', 0)), ',')
                total_aud = format(int(m.get('audiAcc', 0)), ',')

                try:
                    open_date = datetime.strptime(open_date_str, "%Y-%m-%d").date()
                    d_day = (today.date() - open_date).days
                    d_day_str = f"개봉 D+{d_day}" if d_day > 0 else "개봉 1일차"
                except Exception:
                    d_day_str = "개봉일 미정"
                    
                final_data.append({
                    'rank': rank, 
                    'title': title, 
                    'open': open_date_str,
                    'dday': d_day_str, 
                    'daily': daily_aud, 
                    'total': total_aud
                })
            return final_data

        except requests.exceptions.Timeout:
            print(f"⚠️ KOBIS 서버 응답 지연! ({attempt+1}/{max_retries} 재시도 중...)")
            time.sleep(5)
        except Exception as e:
            err_msg = f"❌ KOBIS 수집 중 기타 오류: {e}"
            print(err_msg)
            send_msg(err_msg)
            sys.exit(1)

    print("❌ KOBIS 서버 타임아웃 초과")
    send_msg("❌ KOBIS 서버 접속 타임아웃 3회 초과")
    sys.exit(1)

# 3. 메인 실행 함수
def main():
    movie_list = get_movie_report_api()
    
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst)
    yesterday = now - timedelta(days=1)
    
    now_str = now.strftime('%y.%m.%d %H시')
    target_date_str = f"{yesterday.strftime('%y')}년 {yesterday.month}월 {yesterday.day}일"

    if movie_list:
        report = f"🎬 {target_date_str} 일일 박스오피스 현황({now_str} 기준)\n"
        report += "━━━━━━━━━━━━━━━━━━\n"
        
        for m in movie_list:
            rank_num = int(m['rank'])
            rank_emoji = f"{rank_num}️⃣" if rank_num < 10 else "🔟"
            
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
        sys.exit(1)

if __name__ == "__main__":
    main()
