import os
from pynmea2 import parse
import math
from datetime import datetime, date
from .db import MongoDBHandler

db_handler = MongoDBHandler()


class TrackReader:
    def __init__(self):
        self.path = r"../nmea"
        self.track_data = []
        self.track_coordinates_dict = {}
        self.track_cordinates = []
        self._load()

    def caculate_heading(self, cord1, cord2):
        lat1, lon1 = math.radians(cord1[0]), math.radians(cord1[1])
        lat2, lon2 = math.radians(cord2[0]), math.radians(cord2[1])
        d_lon = lon2 - lon1
        x = math.sin(d_lon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(d_lon))
        initial_heading = math.atan2(x, y)
        initial_heading = math.degrees(initial_heading)
        compass_heading = (initial_heading + 360) % 360
        return compass_heading

    def _load(self):
        full_path = os.path.join(self.path, 'track.nmea')
        point_list = []
        if not os.path.exists(full_path):
            print("track.nmea 없음")
            return
        heading = None
        with open(full_path, 'r') as f:
            for idx, line in enumerate(f):
                msg = parse(line.strip())
                if msg.sentence_type in ["RMC"]:
                    heading = msg.true_course
                if msg.sentence_type in ["GGA", "RMC"]:
                    lat = msg.latitude
                    lon = msg.longitude
                    timestamp = msg.timestamp

                    if lat and lon:
                        point = {
                            "latitude": lat,
                            "longitude": lon,
                            "timestamp": timestamp

                        }

                        if msg.timestamp:
                            timestamp_db = datetime.combine(date.today(), msg.timestamp)
                        else:
                            timestamp_db = None
                            db_point = {
                                "latitude": lat,
                                "longitude": lon,
                                "heading": heading,
                                "timestamp": timestamp_db

                            }

                            self.track_data.append(point)
                            db_handler.save_track(db_point)
                            point_list.append((lat, lon))
                            self.track_coordinates_dict[msg.timestamp.strftime("%H:%M:%S")] = {"point": (lat, lon),
                                                                                               "heading": heading}
            for i in range(len(self.track_data)):
                if self.track_dats[i]["headimg"] == None and i >= 1:
                    last_point = (self.track_data[i - 1]["latitude"], self.track_data[i - 1]["longitude"])
                    current_point = (self.track_data[i]["latitude"], self.track_data[i]["longitude"])
                    heading = self.caculate_heading(last_point, current_point)
                    self.track_data[i]['heading'] = heading
                    dict_time = self.track_data[i]["timestamp"]
                    self.track_coordinates_dict[dict_time.strftime("%H:%M:%S")]["heading"] = heading

    def get_all_track(self):
        return self.track_data