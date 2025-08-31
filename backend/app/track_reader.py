import pynmea2
from datetime import datetime

class TrackReader:
    def __init__(self, filename):
        self.filename = filename
        self.track_data = {}
        self._load()

    def _load(self):
        with open(self.filename, "r") as f:
            lines = f.readlines()

        for line in lines:
            try:
                msg = pynmea2.parse(line.strip())
            except pynmea2.ParseError:
                continue

            if isinstance(msg, pynmea2.types.talker.RMC):
                timestamp = self._combine_date_time(msg.datestamp, msg.timestamp)
                lat = self._convert_latlon(msg.lat, msg.lat_dir)
                lon = self._convert_latlon(msg.lon, msg.lon_dir)
                speed = float(msg.spd_over_grnd) * 1.852 if msg.spd_over_grnd else 0.0
                course = float(msg.true_course) if msg.true_course else 0.0

                self.track_data[timestamp.isoformat()] = {
                    "latitude": lat,
                    "longitude": lon,
                    "speed": speed,
                    "course": course
                }

    def find_closest_point(self, timestamp_iso, time_window=10):
        try:
            target_time = datetime.fromisoformat(timestamp_iso)
        except ValueError:
            return {}

        candidates = []
        for t_str, data in self.track_data.items():
            t = datetime.fromisoformat(t_str)
            delta = abs((t - target_time).total_seconds())
            if delta <= time_window:
                candidates.append((delta, data))

        if not candidates:
            return {}

        candidates.sort()
        return candidates[0][1]

    def _convert_latlon(self, value, direction):
        if not value:
            return None

        degrees = int(float(value) / 100)
        minutes = float(value) - degrees * 100
        result = degrees + minutes / 60

        if direction in ["S", "W"]:
            result *= -1

        return result

    def _combine_date_time(self, date, time):
        if not date or not time:
            return datetime.utcnow()

        return datetime.combine(date, time)
