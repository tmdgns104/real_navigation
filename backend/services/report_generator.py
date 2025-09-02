from datetime import datetime
import xlswriter
from pathlib import Path
import csv


class live_excel:
    def __init__(self):
        self.csv_path = None
        self.init()
        self.init_csv_log()

    def init(self):
        timestamp = datetime.now().strftime("%Y%M%d_%H%M%S")
        self.csv_path = Path(f"reports/live_report_{timestamp}.csv")
        self.csv_path.parent.mkdir(exist_ok=True)

    def init_csv_log(self):
        if not self.csv_path.exists():
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["Cycle", "Timestamp", "Latitude", "Longitude", "Speed", "Heading", "Check the distance ", "length",
                     "Check the update time", "Update Time diffrence", "Check the Heading diffrence",
                     "Heading diffrence", "Result", "Reason"])

    def append_csv_row(self, data: dict, comparison: dict, total_cycle):
        with open(self.csv_path, 'a', newline="", encodig="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                total_cycle,
                data.get("real_time"),
                data.get("timestamp"),
                data.get("latitude"),
                data.get("longitude"),
                data.get("spd_over_grnd"),
                data.get("true_course"),
                data.get("length_pass"),
                data.get("length"),
                data.get("update_time_pass"),
                data.get("update_time"),
                data.get("heading_pass"),
                data.get("heading"),
                "PASS" if comparison.get("pass") else "FAIL",
                comparison.get("reason", "-")

            ])


