from datetime import datetime
from pathlib import Path
import csv


class live_excel:
    def __init__(self):
        self.csv_path = None
        self.init()
        self.init_csv_log()

    def init(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_path = Path("reports") / f"live_report_{timestamp}.csv"
        self.csv_path.parent.mkdir(exist_ok=True)

    def init_csv_log(self):
        if self.csv_path.exists():
            return
        with self.csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Cycle",
                    "Real Time",
                    "Timestamp",
                    "Latitude",
                    "Longitude",
                    "Speed(km/h)",
                    "Heading",
                    "Distance Pass",
                    "Distance(m)",
                    "Update Time Pass",
                    "Update Time Difference(s)",
                    "Heading Pass",
                    "Heading Difference(deg)",
                    "Result",
                    "Reason",
                ]
            )

    def append_csv_row(self, data, comparison, total_cycle):
        with self.csv_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    total_cycle,
                    data.get("real_time"),
                    data.get("timestamp"),
                    data.get("latitude"),
                    data.get("longitude"),
                    data.get("spd_over_grnd"),
                    data.get("true_course"),
                    comparison.get("length_pass"),
                    comparison.get("length"),
                    comparison.get("update_time_pass"),
                    comparison.get("update_time"),
                    comparison.get("heading_pass"),
                    comparison.get("heading"),
                    "PASS" if comparison.get("pass") else "FAIL",
                    comparison.get("reason", "-"),
                ]
            )
