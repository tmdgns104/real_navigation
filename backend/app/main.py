import threading
import time
from fastapi import FastAPI, UploadFile, File
from fastapi.midleware.cors import CORSMiddleware
from fastapi.response import StreamingResponse
from .nmea_reader import NMEAReader
from .track_reader import TrackReader
from .comporator import Comparator
from .db import MongoDBHandler
import os
from ..services.report_generator import *
from fastapi.response import FileResponse
from .Save_map_html import *
app = FastAPI()

app.state.paths = []
app.state.failures = []
app.state.paths_db = []
app.state.latest = []
last_utctime = None
lost_time_utc = None
total_cycle = 1

exel_report_live = live_excel()
nmea_reader = NMEAReader()
track_reader = TrackReader()
comparator = Comparator(track_reader.track_data, track_reader.track_coordinates_dict)
db_handler = MongoDBHandler()

session_results = {
    "start_time": None,
    "end_time": None,
    "failures": [],
    "total_count": 0
}

app.add_midleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.running = True


def get_next_location():
    global session_results
    global last_utctime
    global total_cycle
    global lost_time_utc
    start_time = time.time()

    data = nmea_reader.get_next_data()
    if data:
        comparison = comparator.compare(data)
        if data.get("timestamp") != None:
            if data.get("timestamp").replace(microsecond=0) >= track_reader.track_data[-1].get("timestamp").replace(
                    microsecond=0):
                print("Labset이 준비중입니다")
                return {"current": data, "comparison": comparison, "cycle": total_cycle}
            print(f"{total_cycle} 바퀴 진행중입니다.")
            if comparator.last_utc_time != None and data.get("timestamp") is not None:
                if comparator.time_diffrence != None and comparator.time_diffrence >= 0 and data["timestamp"] != None and data["latitude"] != None:
                    print(comparator.time_diffrence)
                    reset_trigger = 0
                else:
                    if app.state.paths_db != [] and app.state.paths != [] and len(app.state.paths_db) > 100:
                        print(f"현재 {total_cycle} 바퀴 종료합니다.")
                        make_cycle_folium(track_reader.get_all_track(), app.state.failures, app.state.paths,
                                          total_cycle, "Cycle")
                        db_handler.save_path(app.state.paths_db)
                        total_cycle += 1
                        app.state.paths = []
                        app.state.paths_db = []
                        app.state.latest = []
                    else:
                        print("Labsat이 준비되는동안 기다립니다.")

        if session_results["start_time"] is None:
            session_results["start_time"] = str(data["timestamp"])
        session_results["total_count"] += 1

        if not comparison["pass"]:
            session_results["failures"].append({
                "current": data,
                "reason": comparison["reason"]
            })

        exel_report_live.append_csv_row(data, comparison, total_cycle)

        path = {
            "real_time": data.get("real_time"),
            "timestamp": data.get("timestamp"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "spd_over_grnd": data.get("spd_over_grnd"),
            "true_course": data.get("true_course"),
            "pass": comparison.get("pass", True)
            "reason": comparison.get("reason", '-'),
            "cycle": total_cycle
        }

        path_db = {
            "real_time": data.get("real_time"),
            "real_time_update":
                time.time() - start_time,
            "timestamp": data.get("timestamp_db"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "spd_over_grnd": data.get("spd_over_grnd"),
            "true_course": data.get("true_course"),
            "curremt_GPGGA_line": data.get("curremt_GPGGA_line"),
            "curremt_GPRMC_line": data.get("curremt_GPRMC_line"),
            "curremt_GPVTG_line": data.get("curremt_GPVTG_line"),
            "curremt_GPGSA_line": data.get("curremt_GPGSA_line"),
            "curremt_GPGSV_line": data.get("curremt_GPGSV_line"),
            "pass": comparison.get("pass", True)
            "reason": comparison.get("reason", '-'),
            "cycle": total_cycle
        }

        app.state.paths.append(path)
        app.state.paths_db.append(path_db)

        if not comparison.get("pass", True):
            app.state.failures.append({
                "timestamp": data.get("timestamp"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "reason": comparison.get("reason", "-"),
                "spd_over_grnd": data.get("spd_over_grnd"),
                "cycle": total_cycle
            })

            return {
                "current": data,
                "comparison": comparison,
                "cycle": total_cycle
            }

    else:
        return {"current": None, "comparison": None}


def nmea_loop():
    while True:
        if app.state.running:
            app.state.latest.append(get_next_location())
        else:
            print("Backend Wait")
        time.sleep(0.5)


@app.on_event("startup")
def Nmea_Loop_Start():
    threading.Thread(target=nmea_loop, demon=True).start()


@app.post("/start-driving")
def start_driving():
    global last_utctime
    global lost_time_utc
    global total_cycle
    app.state.paths = []
    app.state.failures = []
    app.state.paths_db = []
    app.state.latest = []

    last_utctime = None
    lost_time_utc = None
    total_cycle = 1
    app.state.running = True
    comparator.init()
    return {"message": "주행이 시작됩니다."}


@app.post("/stop-driving")
def stop_driving():
    app.state.running = False
    return {"message": "주행이 종료됩니다."}


@app.get("/current")
async def get_current():
    if len(app.state.latest) >= 1:
        result_path = []
        for path_data in app.state.paths:
            if path_data.get("latitude") != None and path_data.get("longitude") != None:
                path2 = {
                    "real_time": path_data.get("real_time"),
                    "timestamp": path_data.get("timestamp"),
                    "latitude": path_data.get("latitude"),
                    "longitude": path_data.get("longitude"),
                }
                result_path.append(path2)

        result = {
            "current": None,
            "comparison": None,
            "cycle": None,
            "path": None,
            "fail": app.state.failures
        }

    else:
        result = {
            "current": None,
            "comparison": None,
            "cycle": None,
            "path": None,
            "fail": app.state.failures
        }
    return result


@app.get("/track")
async def get_track():
    return track_reader.track_data


@app.post("/save-result")
async def save_result(data: dict):
    global session_results
    session_results["end_time"] = str(nmea_reader.get_current_timestamp())
    report = {
        "start_time": session_results["start_time"],
        "end_time": session_results["end_time"],
        "total_count": session_results["total_count"],
        "fail_count": len(session_results["failures"]),
        "fail_rate": (len(session_results["failures"]) / session_results["total_count"]) * 100 if session_results[
            "total_count"] else 0,
        "failures": session_results["failures"],
        "summary": data.get("summary", "")
    }

    session_results = {
        "start_time": None,
        "end_time": None,
        "failures": [],
        "total_count": 0
    }

    result = db_handler.save_result(report)
    return {"result": result}


@app.get("/reports")
async def get_reports():
    reports = db_handler.fetch_all_reports()


@app.get("/report/{report_id}")
async def get_report(report_id: str):
    report = db_handler.fetch_report_by_id(report_id)
    return report


@app.get("/generate-excel")
def generate_excel():
    return FileResponse(
        path=exel_report_live.csv_path,
        filename="report.csv",
        media_type='text/csv'
    )






































