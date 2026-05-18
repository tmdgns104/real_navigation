import threading
import time
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .Save_map_html import make_cycle_folium
from .comporator import Comparator
from .db import MongoDBHandler
from .nmea_reader import NMEAReader
from .track_reader import TrackReader

try:
    from services.report_generator import live_excel
except ModuleNotFoundError:
    from backend.services.report_generator import live_excel


app = FastAPI(title="Real Navigation Validation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.paths = []
app.state.failures = []
app.state.paths_db = []
app.state.latest = None
app.state.running = False
app.state.saved_maps = []
app.state.session_id = None

total_cycle = 1
excel_report_live = live_excel()
nmea_reader = NMEAReader()
track_reader = TrackReader()
comparator = Comparator(track_reader.track_data, track_reader.track_coordinates_dict)
db_handler = MongoDBHandler()

session_results = {
    "start_time": None,
    "end_time": None,
    "failures": [],
    "total_count": 0,
}


def serialize_point(point):
    if not point:
        return point
    result = dict(point)
    for key in ("real_time", "timestamp", "timestamp_db", "created_at", "started_at", "ended_at", "updated_at"):
        value = result.get(key)
        if value is not None:
            result[key] = str(value)
    return result


def failure_types(comparison):
    types = []
    if comparison.get("length_pass") is False:
        types.append("distance")
    if comparison.get("heading_pass") is False:
        types.append("heading")
    if comparison.get("update_time_pass") is False:
        types.append("update_time")
    return types


def raw_lines_from_data(data):
    raw_fields = {
        "GPGGA": data.get("current_GPGGA_line"),
        "GPRMC": data.get("current_GPRMC_line"),
        "GPVTG": data.get("current_GPVTG_line"),
        "GPGSA": data.get("current_GPGSA_line"),
        "GPGSV": data.get("current_GPGSV_line"),
    }
    return [
        {"sentence_type": sentence_type, "raw_line": raw_line}
        for sentence_type, raw_line in raw_fields.items()
        if raw_line
    ]


def save_point_documents(data, comparison, path, real_time_update):
    session_id = app.state.session_id
    if not session_id:
        return

    base = {
        "session_id": session_id,
        "cycle": path["cycle"],
        "mode": nmea_reader.mode,
        "timestamp": str(data.get("timestamp")) if data.get("timestamp") is not None else None,
        "received_at": data.get("real_time"),
    }

    for raw in raw_lines_from_data(data):
        db_handler.save_raw_nmea({**base, **raw})

    drive_point = {
        **base,
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "speed_kmh": data.get("spd_over_grnd"),
        "heading": data.get("true_course"),
        "comparison_pass": comparison.get("pass", True),
        "failure_types": failure_types(comparison),
        "distance_m": comparison.get("length"),
        "distance_pass": comparison.get("length_pass"),
        "heading_diff_deg": comparison.get("heading"),
        "heading_pass": comparison.get("heading_pass"),
        "update_time_diff_sec": comparison.get("update_time"),
        "update_time_pass": comparison.get("update_time_pass"),
        "reason": comparison.get("reason", "-"),
        "real_time_update": real_time_update,
    }
    db_handler.save_drive_point(drive_point)

    if not comparison.get("pass", True):
        db_handler.save_failure(
            {
                **drive_point,
                "reason": comparison.get("reason", "-"),
            }
        )


def update_session_status(status="running", ended=False):
    if not app.state.session_id:
        return
    db_handler.update_session(
        app.state.session_id,
        status=status,
        ended_at=datetime.now() if ended else None,
        total_cycles=max(total_cycle - 1, 0),
        total_points=session_results["total_count"],
        fail_count=len(session_results["failures"]),
    )


def complete_cycle():
    global total_cycle

    if not app.state.paths:
        return None

    output_path = make_cycle_folium(
        track_reader.get_all_track(),
        app.state.failures,
        app.state.paths,
        total_cycle,
        "Cycle",
    )
    report_metadata = {
        "session_id": app.state.session_id,
        "cycle": total_cycle,
        "type": "folium_map",
        "path": output_path,
        "created_at": datetime.now(),
        "fail_count": len(app.state.failures),
        "point_count": len(app.state.paths),
    }
    db_handler.save_report_metadata(report_metadata)
    app.state.saved_maps.append(serialize_point(report_metadata))

    total_cycle += 1
    update_session_status("running")
    app.state.paths = []
    app.state.failures = []
    app.state.paths_db = []
    comparator.init()
    return output_path


def get_next_location():
    global session_results

    start_time = time.time()
    data = nmea_reader.get_next_data()
    if not data:
        return {"current": None, "comparison": None, "cycle": total_cycle}

    comparison = comparator.compare(data)
    real_time_update = time.time() - start_time

    if session_results["start_time"] is None:
        session_results["start_time"] = str(data.get("timestamp"))
    session_results["total_count"] += 1

    if not comparison.get("pass", True):
        session_results["failures"].append(
            {
                "current": serialize_point(data),
                "reason": comparison.get("reason", "-"),
                "failure_types": failure_types(comparison),
            }
        )

    excel_report_live.append_csv_row(data, comparison, total_cycle)

    path = {
        "real_time": data.get("real_time"),
        "timestamp": data.get("timestamp"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "spd_over_grnd": data.get("spd_over_grnd"),
        "true_course": data.get("true_course"),
        "pass": comparison.get("pass", True),
        "reason": comparison.get("reason", "-"),
        "cycle": total_cycle,
    }
    path_db = {
        **path,
        "real_time_update": real_time_update,
        "timestamp": data.get("timestamp_db"),
        "current_GPGGA_line": data.get("current_GPGGA_line"),
        "current_GPRMC_line": data.get("current_GPRMC_line"),
        "current_GPVTG_line": data.get("current_GPVTG_line"),
        "current_GPGSA_line": data.get("current_GPGSA_line"),
        "current_GPGSV_line": data.get("current_GPGSV_line"),
    }

    app.state.paths.append(path)
    app.state.paths_db.append(path_db)
    save_point_documents(data, comparison, path, real_time_update)

    if not comparison.get("pass", True):
        app.state.failures.append(
            {
                "timestamp": data.get("timestamp"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "reason": comparison.get("reason", "-"),
                "failure_types": failure_types(comparison),
                "spd_over_grnd": data.get("spd_over_grnd"),
                "true_course": data.get("true_course"),
                "cycle": total_cycle,
            }
        )

    completed_map = None
    if data.get("cycle_completed"):
        completed_map = complete_cycle()

    return {
        "current": serialize_point(data),
        "comparison": comparison,
        "cycle": path["cycle"],
        "cycle_completed": bool(data.get("cycle_completed")),
        "saved_map": completed_map,
    }


def nmea_loop():
    while True:
        if app.state.running:
            app.state.latest = get_next_location()
        time.sleep(0.5)


@app.on_event("startup")
def start_background_loop():
    threading.Thread(target=nmea_loop, daemon=True).start()


@app.post("/start-driving")
def start_driving(mode: str = Query("replay", pattern="^(replay|live)$")):
    global total_cycle, session_results, excel_report_live

    app.state.paths = []
    app.state.failures = []
    app.state.paths_db = []
    app.state.latest = None
    app.state.saved_maps = []
    app.state.running = True
    total_cycle = 1
    session_results = {
        "start_time": None,
        "end_time": None,
        "failures": [],
        "total_count": 0,
    }
    try:
        nmea_reader.set_mode(mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    comparator.init()
    excel_report_live = live_excel()
    app.state.session_id = db_handler.create_session(mode)
    mode_label = "replay" if mode == "replay" else "live"
    return {
        "message": f"Driving validation started in {mode_label} mode.",
        "mode": mode,
        "session_id": app.state.session_id,
        "mongo_connected": db_handler.is_connected,
    }


@app.post("/stop-driving")
def stop_driving():
    app.state.running = False
    if app.state.paths:
        complete_cycle()
    update_session_status("completed", ended=True)
    return {
        "message": "Driving validation stopped.",
        "mode": nmea_reader.mode,
        "session_id": app.state.session_id,
    }


@app.get("/current")
async def get_current():
    latest = app.state.latest or {"current": None, "comparison": None, "cycle": total_cycle}
    path = [
        serialize_point(
            {
                "real_time": item.get("real_time"),
                "timestamp": item.get("timestamp"),
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
            }
        )
        for item in app.state.paths
        if item.get("latitude") is not None and item.get("longitude") is not None
    ]

    return {
        "current": latest.get("current"),
        "comparison": latest.get("comparison"),
        "cycle": latest.get("cycle"),
        "cycle_completed": latest.get("cycle_completed", False),
        "saved_map": latest.get("saved_map"),
        "path": path,
        "fail": [serialize_point(item) for item in app.state.failures],
        "running": app.state.running,
        "mode": nmea_reader.mode,
        "session_id": app.state.session_id,
        "mongo_connected": db_handler.is_connected,
        "saved_maps": list(app.state.saved_maps),
    }


@app.get("/track")
async def get_track():
    return [serialize_point(item) for item in track_reader.track_data]


@app.post("/save-result")
async def save_result(data: dict):
    global session_results
    session_results["end_time"] = str(nmea_reader.get_current_timestamp())
    total_count = session_results["total_count"]
    fail_count = len(session_results["failures"])
    report = {
        "session_id": app.state.session_id,
        "start_time": session_results["start_time"],
        "end_time": session_results["end_time"],
        "total_count": total_count,
        "fail_count": fail_count,
        "fail_rate": (fail_count / total_count) * 100 if total_count else 0,
        "failures": session_results["failures"],
        "summary": data.get("summary", ""),
    }
    result = db_handler.save_result(report)
    session_results = {
        "start_time": None,
        "end_time": None,
        "failures": [],
        "total_count": 0,
    }
    return {"result": serialize_point(result)}


@app.get("/reports")
async def get_reports():
    return [serialize_point(report) for report in db_handler.fetch_all_reports()]


@app.get("/report/{report_id}")
async def get_report(report_id: str):
    return serialize_point(db_handler.fetch_report_by_id(report_id))


@app.get("/generate-excel")
def generate_excel():
    return FileResponse(
        path=excel_report_live.csv_path,
        filename="report.csv",
        media_type="text/csv",
    )
