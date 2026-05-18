from datetime import date, datetime
from pathlib import Path

import pynmea2


class NMEAReader:
    VALID_MODES = {"replay", "live"}

    def __init__(self, file_path=None, mode="replay"):
        base_dir = Path(__file__).resolve().parents[1]
        self.file_path = Path(file_path) if file_path else base_dir / "nmea" / "Sample.nmea"
        if not self.file_path.exists():
            raise FileNotFoundError(f"{self.file_path} not found")
        self.mode = mode if mode in self.VALID_MODES else "replay"
        self.lines = self._read_lines()
        self.index = 0
        self.last_timestamp = None

    def _read_lines(self):
        return [
            line.strip()
            for line in self.file_path.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("$")
        ]

    def reset(self):
        self.lines = self._read_lines()
        self.index = 0
        self.last_timestamp = None

    def set_mode(self, mode):
        if mode not in self.VALID_MODES:
            raise ValueError(f"mode must be one of {sorted(self.VALID_MODES)}")
        self.mode = mode
        self.reset()

    def _parse(self, line):
        sentence = line.split("*", 1)[0]
        return pynmea2.parse(sentence)

    def _normalize_message(self, line, msg):
        latitude = getattr(msg, "latitude", None) or None
        longitude = getattr(msg, "longitude", None) or None
        timestamp = getattr(msg, "timestamp", None)
        speed_knots = getattr(msg, "spd_over_grnd", None)
        speed_kmh = float(speed_knots) * 1.852 if speed_knots not in (None, "") else None
        true_course = getattr(msg, "true_course", None)
        true_course = float(true_course) if true_course not in (None, "") else None

        timestamp_db = datetime.combine(date.today(), timestamp) if timestamp else None
        self.last_timestamp = timestamp

        return {
            "real_time": datetime.now(),
            "timestamp": timestamp,
            "timestamp_db": timestamp_db,
            "latitude": latitude,
            "longitude": longitude,
            "spd_over_grnd": speed_kmh,
            "true_course": true_course,
            "current_GPGGA_line": line if msg.sentence_type == "GGA" else None,
            "current_GPRMC_line": line if msg.sentence_type == "RMC" else None,
            "current_GPVTG_line": line if msg.sentence_type == "VTG" else None,
            "current_GPGSA_line": line if msg.sentence_type == "GSA" else None,
            "current_GPGSV_line": line if msg.sentence_type == "GSV" else None,
            "mode": self.mode,
        }

    def get_replay_data(self):
        if not self.lines:
            return None

        is_cycle_end = self.index == len(self.lines) - 1
        line = self.lines[self.index]
        self.index = (self.index + 1) % len(self.lines)

        try:
            msg = self._parse(line)
        except pynmea2.ParseError:
            return None

        data = self._normalize_message(line, msg)
        data["cycle_completed"] = is_cycle_end
        return data

    def get_latest_data(self):
        self.lines = self._read_lines()
        for line in reversed(self.lines):
            try:
                msg = self._parse(line)
            except pynmea2.ParseError:
                continue
            if msg.sentence_type in {"RMC", "GGA", "VTG"}:
                data = self._normalize_message(line, msg)
                data["cycle_completed"] = False
                return data
        return None

    def get_next_data(self):
        if self.mode == "live":
            return self.get_latest_data()
        return self.get_replay_data()

    def get_current_timestamp(self):
        return self.last_timestamp
