import datetime
import os
import pynmea2


class NMEAReader:
    def __init__(self):
        self.file_path = r"../nmea/sample.nmea"
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"{self.file_path} not found")
        self.file = open(self.file_path, 'r')

    def file_nmea_in_log_reverse(self, file_path, target):
        with open(file_path, 'rb') as f:
            f.seek(0, 2)
            buffer = bytearray()
            file_size = f.tell()
            while file_size > 0:
                read_size = min(1024, file_size)
                file_size -= read_size
                f.seek(file_size)
                chunk = f.read(read_size)
                buffer = chunk + buffer
                while b'\n' in buffer:
                    last_newline = buffer.rindex(b'\n')
                    line = buffer[last_newline + 1:].strip()
                    buffer = buffer[:last_newline]
                    if line.startswith(b'$') and target.encode() in line:
                        return line.decode(), True
            if buffer:
                line = buffer.strip()
                if line.startswith(b"$") and target.encode() in line:
                    return line.decode()
        return None, False


def get_next_data(self):
    import time

    GPGGA_last_line, GPGGA_is_find = self.find_nmea_in_log_reverse(self.file_path, '$GPGGA')
    GPRMC_last_line, GPRMC_is_find = self.find_nmea_in_log_reverse(self.file_path, '$GPRMC')
    GPVTG_last_line, GPVTG_is_find = self.find_nmea_in_log_reverse(self.file_path, '$GPVTG')
    GPGSA_last_line, GPGSA_is_find = self.find_nmea_in_log_reverse(self.file_path, '$GPGSA')
    GPGSV_last_line, GPGSV_is_find = self.find_nmea_in_log_reverse(self.file_path, '$GPGSV')

    if GPGSV_is_find:
        current_GPGSV_line = GPGSV_last_line
        GPGSV_msg = pynmea2.parse(GPGSV_last_line)
        GPGSV_num_sv_in_view = GPGSV_msg.num_sv_in_view
        GPGSV_sv_prn_num = [GPGSV_msg.sv_prn_num_1, GPGSV_msg.sv_prn_num_2, GPGSV_msg.sv_prn_num_3,
                            GPGSV_msg.sv_prn_num_4]
        GPGSV_elevation = [GPGSV_msg.elevation_deg_1, GPGSV_msg.elevation_deg_2, GPGSV_msg.elevation_deg_3,
                           GPGSV_msg.elevation_deg_4]
        GPGSV_snr = [GPGSV_msg.snr_1, GPGSV_msg.snr_2, GPGSV_msg.snr_3, GPGSV_msg.snr_4]

    if GPGSA_is_find:
        current_GPGSA_line = GPGSA_last_line
        GPGSA_msg = pynmea2.parse(GPGSA_last_line)
        GPGSA_mode = GPGSA_msg.mode
        GPGSA_pdop = GPGSA_msg.pdop
        GPGSA_hdop = GPGSA_msg.hdop
        GPGSA_vdop = GPGSA_msg.vdop

    if GPVTG_is_find:
        current_GPVTG_line = GPVTG_last_line
        GPVTG_msg = pynmea2.parse(GPVTG_last_line)
        GPVTG_speed_kmh = GPVTG_msg.spd_over_gnd_kmph
        GPVTG_track_true = GPVTG_msg.true_track
        GPVTG_track_magnetic = GPVTG_msg.msg_track
        GPVTG_speed_knots = GPVTG_msg.spd_over_grnd_kts
    if GPRMC_is_find:
        current_GPRMC_line = GPRMC_last_line
        GPRMC_msg = pynmea2.parse(GPRMC_last_line)
        GPRMC_utc_time = GPRMC_msg.timestamp
        heading = GPRMC_msg.true_course
        GPRMC_status = GPRMC_msg.status
        GPRMC_latitude = GPRMC_msg.latitude
        GPRMC_longitude = GPRMC_msg.longitude
        GPRMC_speed_knots = GPRMC_msg.spd_over_grnd


if GPGGA_is_find:
    current_GPGGA_line = GPGGA_last_line
    GPGGA_msg = pynmea2.parse(GPGGA_last_line)
    current_lat = GPGGA_msg.latitude
    current_lon = GPGGA_msg.longitude
    utc_time = GPGGA_msg.timestamp
    GPGGA_gps_quality = GPGGA_msg.gps_qual
    GPGGA_num_sats = GPGGA_msg.num_sats
    GPGGA_altitude = GPGGA_msg.altitude

if utf_tume =None and current_lat == 0 and current_lon == 0:
    current_lon = None
    current_lat = None
if utc_time:
    utc_time_db = datetime.dstetime.combine(dstetime.date.today(), utc_time)
else:
    utc_time_db = None
result = {
    "real_time": datetime.datetime.now(),
    "timestamp": utc_time,
    "timestamp_db": utc_time_db,
    "latitude": current_lat
    "longitude": current_lon,
    "spd_over_gnd": GPVTG_speed_kmh,
    "true_course": heading,
    "current_GPGGA_line": current_GPGGA_line,
    "current_GPRMC_line": current_GPRMC_line,
    "current_GPVTG_line": current_GPVTG_line,
    "current_GPGSA_line": current_GPGSA_line,
    "current_GPGSV_line": current_GPGSV_line,
}
return result


def get_current_timestamp(self):
    return getattr(self, "last_timestamp", None)