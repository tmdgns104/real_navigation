import pynmea2
from datetime import datetime

class NMEAReader:
    def __init__(self, filename):
        self.filename = filename
        self.lines = []
        self.index = 0
        self._load()

    def _load(self):
        with open(self.filename, "r") as f:
            self.lines = f.readlines()

    def reset(self):
        self.index = 0

    def get_next_location(self):
        if self.index >= len(self.lines):
            return None

        line = self.lines[self.index].strip()
        self.index += 1

        try:
            msg = pynmea2.parse(line)
        except pynmea2.ParseError:
            return {}

        if isinstance(msg, pynmea2.types.talker.RMC):
            # Recommended Minimum Navigation Information
            lat = self._convert_latlon(msg.lat, msg.lat_dir)
            lon = self._convert_latlon(msg.lon, msg.lon_dir)
            speed = float(msg.spd_over_grnd) * 1.852 if msg.spd_over_grnd else 0.0  # knots → km/h
            course = float(msg.true_course) if msg.true_course else 0.0
            timestamp = self._combine_date_time(msg.datestamp, msg.timestamp)

            return {
                "latitude": lat,
                "longitude": lon,
                "speed": speed,
                "course": course,
                "timestamp": timestamp.isoformat()
            }

        return {}

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
