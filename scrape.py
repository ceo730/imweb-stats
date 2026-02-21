import os
import csv
import json
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

IMWEB_EMAIL = os.environ["IMWEB_EMAIL"]
IMWEB_PASSWORD = os.environ["IMWEB_PASSWORD"]
SITE_URL = os.environ.get("IMWEB_SITE_URL", "https://closedmockexam.imweb.me")
CSV_FILE = os.path.join(os.path.dirname(__file__), "visitors.csv")


def login(page):
    """아임웹 로그인"""
    page.goto("https://imweb.me/login")
    page.wait_for_load_state("networkidle")

    page.fill('input[type="email"], input[name="email"], input[placeholder*="이메일"]', IMWEB_EMAIL)
    page.fill('input[type="password"], input[name="password"]', IMWEB_PASSWORD)
    page.click('button[type="submit"]')

    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)


def get_visitor_count(page):
    """관리자 통계 페이지에서 어제 방문자 수 가져오기"""
    # 관리자 페이지 접속
    page.goto(f"{SITE_URL}/admin")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(5000)

    # 통계 페이지로 이동 시도
    stats_urls = [
        f"{SITE_URL}/admin/statistics",
        f"{SITE_URL}/admin/stat",
        f"{SITE_URL}/admin/analytics",
    ]

    for url in stats_urls:
        page.goto(url)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
        if "stat" in page.url.lower() or "analytics" in page.url.lower():
            break

    # 페이지 내용에서 방문자 수 추출 시도
    # 아임웹 관리자 대시보드에서 방문자 수 텍스트를 찾음
    page.wait_for_timeout(3000)

    # 스크린샷 저장 (디버깅용)
    page.screenshot(path="debug_screenshot.png", full_page=True)

    # 방문자 수 추출 - 여러 셀렉터 시도
    visitor_count = None

    # 방법 1: API 호출로 통계 데이터 가져오기
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        # 아임웹 내부 API 호출 시도
        response = page.evaluate("""
            async () => {
                const urls = [
                    '/admin/api/statistics/visitor',
                    '/admin/api/stat/visitor',
                    '/admin/api/analytics/visitor',
                ];
                for (const url of urls) {
                    try {
                        const res = await fetch(url);
                        if (res.ok) {
                            return { url, data: await res.json() };
                        }
                    } catch(e) {}
                }
                return null;
            }
        """)
        if response:
            print(f"API response from {response['url']}: {json.dumps(response['data'], indent=2)}")
    except Exception as e:
        print(f"API approach failed: {e}")

    # 방법 2: 페이지에서 텍스트 추출
    try:
        content = page.content()
        print(f"Page URL: {page.url}")
        print(f"Page title: {page.title()}")

        # 방문자 관련 요소 찾기
        selectors = [
            'text=방문자',
            'text=visitor',
            '.stat-visitor',
            '.visitor-count',
            '[class*="visitor"]',
            '[class*="stat"]',
        ]

        for selector in selectors:
            try:
                elements = page.query_selector_all(selector)
                for el in elements:
                    text = el.inner_text()
                    print(f"Found [{selector}]: {text}")
            except Exception:
                pass
    except Exception as e:
        print(f"Text extraction failed: {e}")

    # 방법 3: 대시보드 숫자 추출
    try:
        all_text = page.inner_text("body")
        print(f"\n=== Page text (first 3000 chars) ===\n{all_text[:3000]}")
    except Exception as e:
        print(f"Body text extraction failed: {e}")

    return yesterday, visitor_count


def save_to_csv(date, visitors):
    """CSV 파일에 저장"""
    existing = {}
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing[row["date"]] = row["visitors"]

    existing[date] = str(visitors) if visitors else "N/A"

    sorted_dates = sorted(existing.keys(), reverse=True)

    with open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "visitors"])
        writer.writeheader()
        for d in sorted_dates:
            writer.writerow({"date": d, "visitors": existing[d]})

    print(f"Saved: {date} -> {visitors} visitors")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ko-KR",
        )
        page = context.new_page()

        try:
            print("Logging in...")
            login(page)
            print("Login complete. Fetching stats...")
            date, visitors = get_visitor_count(page)
            print(f"Date: {date}, Visitors: {visitors}")
            save_to_csv(date, visitors)
        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="error_screenshot.png", full_page=True)
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
