import os
import csv
import json
import tempfile
from datetime import datetime, timedelta
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Metric,
    Dimension,
)

GA4_PROPERTY_ID = os.environ["GA4_PROPERTY_ID"]
CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "visitors.csv")


def get_client():
    """GA4 인증 클라이언트 생성"""
    creds_json = os.environ["GA4_CREDENTIALS"]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(creds_json)
        creds_path = f.name
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
    return BetaAnalyticsDataClient()


def fetch_visitors(client, start_date="7daysAgo", end_date="yesterday"):
    """GA4에서 일별 방문자 수 가져오기"""
    request = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[Dimension(name="date")],
        metrics=[Metric(name="activeUsers")],
    )
    response = client.run_report(request)

    results = {}
    for row in response.rows:
        raw_date = row.dimension_values[0].value  # YYYYMMDD
        date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
        visitors = int(row.metric_values[0].value)
        results[date] = visitors

    return results


def load_csv():
    """기존 CSV 데이터 로드"""
    existing = {}
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["date"] and row["visitors"]:
                    existing[row["date"]] = int(row["visitors"])
    return existing


def save_csv(data):
    """CSV 파일 저장 (날짜 내림차순)"""
    sorted_dates = sorted(data.keys(), reverse=True)
    with open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "visitors"])
        writer.writeheader()
        for date in sorted_dates:
            writer.writerow({"date": date, "visitors": data[date]})
    print(f"Saved {len(data)} rows to {CSV_FILE}")


def main():
    client = get_client()

    # 기존 데이터 로드
    existing = load_csv()
    print(f"Existing data: {len(existing)} rows")

    # 최근 7일 데이터 가져오기
    new_data = fetch_visitors(client, start_date="7daysAgo", end_date="yesterday")
    print(f"Fetched from GA4: {new_data}")

    # 병합 (새 데이터가 기존 데이터 덮어씀)
    existing.update(new_data)

    # 저장
    save_csv(existing)


if __name__ == "__main__":
    main()
