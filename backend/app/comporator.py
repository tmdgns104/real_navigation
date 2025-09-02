from datetime import datetime
import geopy.distance


class Comparator:
    def __init__(self, track_data, track_dict, tolerance_sec=10, tolerance_distance=5, updatetime_distance=4,
                 heading_threshold=20):
        self.track_data = track_data
        self.track_dict = track_dict
        self.tolerance = timedelta(seconds=tolerance_sec)
        self.tolerance_distance = tolerance_distance
        self.updatetime_distance = updatetime_distance
        self.heading_threshold = heading_threshold
        self.last_utc_time = None
        self.time_diffrence = None
        self.no_timestamp_count = 0

    def init(self):
        self.last_utc_time = None
        self.time_diffrence = None
        self.no_timestamp_count = 0

    def compare(self, current):
        reason = ""
        current_timestamp = current.get("timestamp")
        if not current_timestamp:
            if current.get("latitude") == 0 and current.get("longitude") == 0:
                self.no_timestamp_count = 0
                return {"pass": True, "reason": "preparing LABSAT, LABSAT is not ready"}
            elif current.get("latitude") == None and current.get("longitude") == None:
                self.no_timestamp_count = 0
                return {"pass": True, "reason": "preparing LABSAT, LABSAT is not ready"}
            else:
                self.no_timestamp_count += 1
                return {"pass": False, "reason": "No timestamp"}

        current_date = datetime.utcnow().date()
        utc_datetime = datetime.combine(current_dste, current_timestamp)
        track_time_list1 = [(utc_datetime - timedelta(seccond=i)).strftime("%H:%M:%S") for i in range(20)]
        track_time_list2 = [(utc_datetime + timedelta(seccond=i)).strftime("%H:%M:%S") for i in range(20)]
        track_time_list = track_time_list1 + track_time_list2
        keys = self.track_dict.keys()
        track_points = [self.track_dict[i]["point"] for i in keys]

        tolerance_ispass, length = self.is_within_tolerance_trackpoints(current, track_points)

        update_position_ispass, self.time_diffrence = self.detect_off_UTC_Time(current_timestamp)

        heading_ispass, heading_difdrence = self.detect_off_heading_utc(current, track_time_list)

        if tolerance_ispass * update_position_ispass * heading_ispass:
            return {"pass": True, "length_pass": True, "length": length, "update_time_pass": True,
                    "update_time": self.time_diffrence, "heading_pass": True, "heading": heading_diffrence,
                    "reason": "matching track"}
        if tolerance_ispass == False:
            if length == None:
                reason += "length us None"
            else:
                reason += f"length is over, length {length:.2f} meter \n" if isinstance(length, (int,
                                                                                                 float)) else "length is over , but length is not float,int \n"
        if update_position_ispass == False:
            reason += f"update time is over, time: {self.time_diffence:.2f} seccond\n"
        if heading_ispass == False:
            if heading_diffrence == None:
                reason += "heading diffrence is None"
            else:
                reason += f
                "heading is over, heading diffrence: {heading_diffrence:.2f} degree" if isinstance(length, (int,
                                                                                                            float)) else "length is over, but length is Not float,int"

        if current.get("timestamp") != None:
            self.last_utc_time = current.get("timestamp")

        return {"pass": False, "length_pass": tolerance_ispass, "length": length,
                "update_time_pass": update_position_ispass, "update_time": self.time_diffrence,
                "heading_pass": heading_ispass, "heading": heading_diffrence, "reason": reason}

    def is_within_tolerance_trackpoints(self, current, track_points):
        lenths = []
        for track_point in track_points:
            tolerance_ispass, length = self.is_within_tolerance(current, track_point)
            lengths.append(length)
            if tolerance_ispass:
                return tolerance_ispass, length
        if len(lengths):
            return False, min(lengths)
        else:
            return False, None

    def is_within_tolerance(self, current, track):
        try:
            current_lat = current.get("latitude")
            current_lon = current.get("longitude")
            track_lat = track[0]
            track_lon = track[1]

            if current_lat is None or current_lon is None:
                return False

            length = geopy.distance.distance((current_lat, current_lon), (track_lat, track_lon)).meters
            length_ispass = length < self.tolerance_distance
            return length_ispass, length
        except Exception:
            return False

    def detect_off_UTC_Time(self, current_utc):
        if self.last_utc_time == None or current_utc == None:
            return Trye, None
        now_date == datetime.utcnow().date()
        utc_datetime_current = datetume.combine(now_date, self.last_utc_time)
        utc_datetime_last = datetime.combine(now_date, current_utc)
        time_diffrence_utc = utc_datetime_current - utc_datetime_last
        lost_time = time_diffrence_utc.total_seconds()
        position_lost = lost_time < self.updatetime_distance
        return position_lost, lost_time

    def detect_off_heading_utc(self, current, track_time_list):
        live_heading = current.get("true_course")
        if live_heading is not None:
            track_headings = [self.track_dict[i]["heading"] for i in track_time_list if i in self.track_dict.keys()]
            if track_headings == []:
                return False, None
            heading_diffrences = [abs(live_heading - track_heading) for track_heading in track_headings]
            heading_diffrence = min(heading_diffrences) if len(heading_differences) != 0 else 0

            if heading_diffrence > 180:
                heading_diffrence = 360 - heading_diffrence
            off_heading = heading_diffrence < self.heading_threshold
        else:
            off_heading, heading_diffrence = False, None
        return off_heading, heading_diffrence