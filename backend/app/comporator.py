from datetime import datetime, timedelta

import geopy.distance


class Comparator:
    def __init__(
        self,
        track_data,
        track_dict,
        tolerance_sec=3,
        tolerance_distance=5,
        updatetime_distance=4,
        heading_threshold=20,
    ):
        self.track_data = track_data
        self.track_dict = track_dict
        self.tolerance_sec = tolerance_sec
        self.tolerance = timedelta(seconds=tolerance_sec)
        self.tolerance_distance = tolerance_distance
        self.updatetime_distance = updatetime_distance
        self.heading_threshold = heading_threshold
        self.last_utc_time = None
        self.time_difference = None
        self.no_timestamp_count = 0

    def init(self):
        self.last_utc_time = None
        self.time_difference = None
        self.no_timestamp_count = 0

    def compare(self, current):
        current_timestamp = current.get("timestamp")
        if not current_timestamp:
            if current.get("latitude") in (0, None) and current.get("longitude") in (0, None):
                self.no_timestamp_count = 0
                return {"pass": True, "reason": "preparing LABSAT, LABSAT is not ready"}
            self.no_timestamp_count += 1
            return {"pass": False, "reason": "No timestamp"}

        current_date = datetime.utcnow().date()
        utc_datetime = datetime.combine(current_date, current_timestamp)
        track_time_list = [
            (utc_datetime + timedelta(seconds=offset)).strftime("%H:%M:%S")
            for offset in range(-self.tolerance_sec, self.tolerance_sec + 1)
        ]
        track_candidates = self.get_track_candidates(track_time_list)
        track_points = [item["point"] for item in track_candidates]

        distance_pass, distance = self.is_within_tolerance_trackpoints(current, track_points)
        update_time_pass, self.time_difference = self.detect_off_utc_time(current_timestamp)
        heading_pass, heading_difference = self.detect_off_heading(current, track_candidates)

        self.last_utc_time = current_timestamp
        result = {
            "pass": distance_pass and update_time_pass and heading_pass,
            "length_pass": distance_pass,
            "length": distance,
            "update_time_pass": update_time_pass,
            "update_time": self.time_difference,
            "heading_pass": heading_pass,
            "heading": heading_difference,
            "reason": "matching track",
        }
        if not result["pass"]:
            result["reason"] = self._build_reason(distance_pass, distance, update_time_pass, heading_pass, heading_difference)
        return result

    def get_track_candidates(self, track_time_list):
        return [
            self.track_dict[key]
            for key in track_time_list
            if key in self.track_dict
        ]

    def _build_reason(self, distance_pass, distance, update_time_pass, heading_pass, heading_difference):
        reasons = []
        if not distance_pass:
            if distance is None:
                reasons.append("distance could not be calculated")
            else:
                reasons.append(f"distance is over tolerance: {distance:.2f}m")
        if not update_time_pass:
            reasons.append(f"update time is over tolerance: {self.time_difference:.2f}s")
        if not heading_pass:
            if heading_difference is None:
                reasons.append("heading could not be compared")
            else:
                reasons.append(f"heading is over tolerance: {heading_difference:.2f}deg")
        return "\n".join(reasons)

    def is_within_tolerance_trackpoints(self, current, track_points):
        lengths = []
        for track_point in track_points:
            distance_pass, length = self.is_within_tolerance(current, track_point)
            if length is not None:
                lengths.append(length)
            if distance_pass:
                return True, length
        return False, min(lengths) if lengths else None

    def is_within_tolerance(self, current, track):
        current_lat = current.get("latitude")
        current_lon = current.get("longitude")
        if current_lat is None or current_lon is None:
            return False, None

        length = geopy.distance.distance((current_lat, current_lon), track).meters
        return length < self.tolerance_distance, length

    def detect_off_utc_time(self, current_utc):
        if self.last_utc_time is None or current_utc is None:
            return True, None

        now_date = datetime.utcnow().date()
        previous = datetime.combine(now_date, self.last_utc_time)
        current = datetime.combine(now_date, current_utc)
        difference = (current - previous).total_seconds()
        return 0 <= difference <= self.updatetime_distance, difference

    def detect_off_heading(self, current, track_candidates):
        live_heading = current.get("true_course")
        if live_heading is None:
            return False, None

        track_headings = [
            item["heading"]
            for item in track_candidates
            if item["heading"] is not None
        ]
        if not track_headings:
            return False, None

        differences = [
            min(abs(live_heading - track_heading), 360 - abs(live_heading - track_heading))
            for track_heading in track_headings
        ]
        heading_difference = min(differences)
        return heading_difference < self.heading_threshold, heading_difference
