from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from .nmea_reader import NMEAReader
from .track_reader import TrackReader
from .comparator import Comparator
from .db import MongoDBHandler
import os

from fastapi.responses import FileResponse
from services.report_generator import generate_excel_report  # 따로 관리 가능

app = FastAPI()
app.state.path = []       # 전체 경로
app.state.failures = []   # 실패 위치
app.state.path = []       # 전체 경로
app.state.failures = []   # 실패 위치

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



nmea_reader = NMEAReader()
track_reader = TrackReader()
comparator = Comparator(track_reader.track_data)
db_handler = MongoDBHandler()

# 주행 세션 데이터
session_results = {
    "start_time": None,
    "end_time": None,
    "failures": [],
    "total_count": 0
}

@app.get("/next-location")
async def get_next_location():
    global session_results

    data = nmea_reader.get_next_data()
    if data:
        if session_results["start_time"] is None:
            session_results["start_time"] = str(data["timestamp"])

        session_results["total_count"] += 1
        comparison = comparator.compare(data)

        if not comparison["pass"]:
            session_results["failures"].append({
                "current": data,
                "reason": comparison["reason"]
            })

        return {
            "current": data,
            "comparison": comparison
        }
    else:
        return {"current": None, "comparison": None}

@app.get("/track")
async def get_track():
    return track_reader.get_all_track()

@app.post("/save-result")
async def save_result(data: dict):
    global session_results
    session_results["end_time"] = str(nmea_reader.get_current_timestamp())

    report = {
        "start_time": session_results["start_time"],
        "end_time": session_results["end_time"],
        "total_count": session_results["total_count"],
        "fail_count": len(session_results["failures"]),
        "fail_rate": (len(session_results["failures"]) / session_results["total_count"]) * 100 if session_results["total_count"] else 0,
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
    return reports

@app.get("/report/{report_id}")
async def get_report(report_id: str):
    report = db_handler.fetch_report_by_id(report_id)
    return report

@app.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    contents = await file.read()
    save_path = f"backend/videos/{file.filename}"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(contents)
    return {"filename": file.filename}

@app.get("/video/{filename}")
async def get_video(filename: str):
    path = f"backend/videos/{filename}"
    file_like = open(path, mode="rb")
    return StreamingResponse(file_like, media_type="video/mp4")



@app.get("/generate-excel")
def generate_excel():
    return FileResponse(
        path=generate_excel_report(app.state.path, app.state.failures),
        filename="report.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
