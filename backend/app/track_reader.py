from datetime import date, datetime
import math
from pathlib import Path

from pynmea2 import ParseError, parse


class TrackReader:
    def __init__(self, file_path=None):
        base_dir = Path(__file__).resolve().parents[1]
        self.file_path = Path(file_path) if file_path else base_dir / "nmea" / "track.nmea"
        self.track_data = []
        self.track_coordinates_dict = {}
        self._load()

    def calculate_heading(self, coord1, coord2):
        lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
        lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
        d_lon = lon2 - lon1
        x = math.sin(d_lon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
        return (math.degrees(math.atan2(x, y)) + 360) % 360

    def _load(self):
        if not self.file_path.exists():
            print(f"{self.file_path} not found")
            return

        for line in self.file_path.read_text(encoding="utf-8").splitlines():
            if not line.strip().startswith("$"):
                continue
            try:
                sentence = line.strip().split("*", 1)[0]
                msg = parse(sentence)
            except ParseError:
                continue

            if msg.sentence_type not in {"GGA", "RMC"}:
                continue

            latitude = getattr(msg, "latitude", None)
            longitude = getattr(msg, "longitude", None)
            timestamp = getattr(msg, "timestamp", None)
            if not latitude or not longitude or not timestamp:
                continue

            heading = getattr(msg, "true_course", None)
            heading = float(heading) if heading not in (None, "") else None
            point = {
                "latitude": latitude,
                "longitude": longitude,
                "timestamp": timestamp,
                "timestamp_db": datetime.combine(date.today(), timestamp),
                "heading": heading,
            }
            self.track_data.append(point)

        for idx, point in enumerate(self.track_data):
            if point["heading"] is None and idx > 0:
                previous = self.track_data[idx - 1]
                point["heading"] = self.calculate_heading(
                    (previous["latitude"], previous["longitude"]),
                    (point["latitude"], point["longitude"]),
                )
            self.track_coordinates_dict[point["timestamp"].strftime("%H:%M:%S")] = {
                "point": (point["latitude"], point["longitude"]),
                "heading": point["heading"],
            }

    def get_all_track(self):
        return self.track_data
