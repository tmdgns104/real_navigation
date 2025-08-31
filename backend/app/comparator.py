from geopy.distance import geodesic

class Comparator:
    def __init__(self, position_tolerance=3.0, speed_tolerance=5.0, course_tolerance=10.0, altitude_tolerance=5.0):
        self.position_tolerance = position_tolerance  # meters
        self.speed_tolerance = speed_tolerance        # km/h
        self.course_tolerance = course_tolerance      # degrees
        self.altitude_tolerance = altitude_tolerance  # meters

    def compare(self, real, reference):
        if not reference:
            return {
                "position_ok": False,
                "speed_ok": False,
                "course_ok": False,
                "altitude_ok": False
            }

        result = {}

        # Position
        real_pos = (real.get("latitude"), real.get("longitude"))
        ref_pos = (reference.get("latitude"), reference.get("longitude"))
        if None not in real_pos and None not in ref_pos:
            distance = geodesic(real_pos, ref_pos).meters
            result["position_ok"] = distance <= self.position_tolerance
        else:
            result["position_ok"] = False

        # Speed
        if real.get("speed") is not None and reference.get("speed") is not None:
            result["speed_ok"] = abs(real["speed"] - reference["speed"]) <= self.speed_tolerance
        else:
            result["speed_ok"] = False

        # Course
        if real.get("course") is not None and reference.get("course") is not None:
            result["course_ok"] = abs(real["course"] - reference["course"]) <= self.course_tolerance
        else:
            result["course_ok"] = False

        # Altitude (옵션 - 실 데이터에 없으면 항상 True 처리 가능)
        result["altitude_ok"] = True

        return result
