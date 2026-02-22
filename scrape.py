import os
import csv
import json
import tempfile
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Metric,
    Dimension,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
SITES_FILE = os.path.join(SCRIPT_DIR, "sites.json")


def get_client():
    """GA4 인증 클라이언트 생성"""
    creds_json = os.environ["GA4_CREDENTIALS"]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(creds_json)
        creds_path = f.name
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
    return BetaAnalyticsDataClient()


def fetch_visitors(client, property_id, start_date="7daysAgo", end_date="yesterday"):
    """GA4에서 일별 방문자 수 가져오기"""
    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[Dimension(name="date")],
        metrics=[Metric(name="activeUsers")],
    )
    response = client.run_report(request)

    results = {}
    for row in response.rows:
        raw_date = row.dimension_values[0].value
        date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
        visitors = int(row.metric_values[0].value)
        results[date] = visitors

    return results


def load_csv(csv_path):
    """기존 CSV 데이터 로드"""
    existing = {}
    if os.path.exists(csv_path):
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["date"] and row["visitors"]:
                    existing[row["date"]] = int(row["visitors"])
    return existing


def save_csv(csv_path, data):
    """CSV 파일 저장 (날짜 내림차순)"""
    sorted_dates = sorted(data.keys(), reverse=True)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "visitors"])
        writer.writeheader()
        for date in sorted_dates:
            writer.writerow({"date": date, "visitors": data[date]})
    print(f"  Saved {len(data)} rows")


def main():
    client = get_client()
    os.makedirs(DATA_DIR, exist_ok=True)

    with open(SITES_FILE, "r", encoding="utf-8") as f:
        sites = json.load(f)

    for site in sites:
        name = site["name"]
        property_id = site["property_id"]
        csv_path = os.path.join(DATA_DIR, f"{name}.csv")

        print(f"[{name}] property_id={property_id}")

        try:
            existing = load_csv(csv_path)
            print(f"  Existing: {len(existing)} rows")

            new_data = fetch_visitors(client, property_id)
            print(f"  Fetched: {new_data}")

            existing.update(new_data)
            save_csv(csv_path, existing)
        except Exception as e:
            print(f"  ERROR: {e}")


if __name__ == "__main__":
    main()
