from datetime import datetime
import xlsxwriter
from pathlib import Path

def generate_excel_report(path, failures):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(f"reports/report_{timestamp}.xlsx")
    output_path.parent.mkdir(exist_ok=True)

    workbook = xlsxwriter.Workbook(str(output_path))
    sheet = workbook.add_worksheet("Path")

    # 헤더에 PASS/FAIL, Reason 추가
    sheet.write_row(0, 0, ["No", "Timestamp", "Latitude", "Longitude", "Speed", "Heading", "Result", "Reason"])

    for i, p in enumerate(path):
        ts = p.get("timestamp")

        # ✅ timestamp가 datetime이면 문자열로 변환
        if isinstance(ts, datetime):
            ts = ts.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        else:
            ts = str(ts)

        # ✅ 이 안에서만 p 사용
        sheet.write_row(i + 1, 0, [
            i + 1,
            ts,
            p.get("latitude"),
            p.get("longitude"),
            p.get("spd_over_grnd"),
            p.get("true_course"),
            "PASS" if p.get("pass", True) else "FAIL",
            p.get("reason", "-")
        ])

    # Failures 시트 그대로 유지
    fail_sheet = workbook.add_worksheet("Failures")
    fail_sheet.write_row(0, 0, ["No", "Latitude", "Longitude", "Reason"])
    for i, f in enumerate(failures):
        fail_sheet.write_row(i + 1, 0, [i + 1, f["latitude"], f["longitude"], f["reason"]])

    workbook.close()
    return output_path
