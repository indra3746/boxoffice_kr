import os
import sys
import time
import datetime
import requests

# 1. 텔레그램 전송 함수
def send_telegram(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if token and chat_id and len(text) > 10:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True})
        except Exception as e:
            print(f"텔레그램 전송 실패: {e}")

# 2. KOBIS 박스오피스 수집 함수
def fetch_kobis_boxoffice():
    api_key = os.environ.get("KOBIS_API_KEY")
    if not api_key:
        print("⚠️ KOBIS_API_KEY가 설정되지 않았습니다.")
        sys.exit(1) # 🚨 실패 상태로 종료하여 재시도 유도

    # 한국 시간 기준 어제 날짜 구하기 (KOBIS 일일 박스오피스 기준)
    now_kst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    yesterday = (now_kst - datetime.timedelta(days=1)).strftime("%Y%m%d")
    
    url = f"http://kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key={api_key}&targetDt={yesterday}"

    print(f"🎬 KOBIS API 데이터 수집 시작... (기준일자: {yesterday})")

    try:
        res = requests.get(url, timeout=15)
        if res.status_code != 200:
            print(f"⚠️ KOBIS 응답 에러 (코드: {res.status_code})")
            sys.exit(1) # 🚨 HTTP 에러 시 실패 상태로 종료

        data = res.json()
        daily_list = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])

        if not daily_list:
            print("❌ 수집된 데이터가 없습니다. (KOBIS 업데이트 지연 가능성)")
            sys.exit(1) # 🚨 데이터가 비어있어도 실패 처리하여 10분 뒤 재시도

        rankings = []
        for movie in daily_list[:10]:
            rank = movie.get("rank")
            movie_nm = movie.get("movieNm")
            audi_cnt = int(movie.get("audiCnt", 0))
            rankings.append(f"{rank}위 {movie_nm} (관객수: {audi_cnt:,}명)")

        return rankings

    except Exception as e:
        print(f"❌ 수집 중 오류 발생: {e}")
        sys.exit(1) # 🚨 네트워크 접속 실패 시 깃허브 액션 재시도 실행!

# 3. 메인 로직
def main():
    now_kst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    time_str = now_kst.strftime("%y.%m.%d %H:%M")

    rankings = fetch_kobis_boxoffice()

    msg = f"🍿 **일일 영화 박스오피스 TOP 10 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    msg += "\n".join([f" {x}" for x in rankings]) + "\n\n"
    msg += "🔗 [KOBIS 공식 홈페이지](https://www.kobis.or.kr)\n"

    send_telegram(msg)
    print("--- 전송 완료 ---")

if __name__ == "__main__":
    main()
