import os
from copy import deepcopy
from datetime import datetime
from uuid import uuid4

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
except ModuleNotFoundError:
    MongoClient = None
    PyMongoError = Exception
    ServerSelectionTimeoutError = Exception


class MongoDBHandler:
    """Repository for driving sessions and validation data.

    If MongoDB is unavailable, this class falls back to in-memory storage so the
    portfolio demo can still run. Check `is_connected` to know whether writes
    are persistent.
    """

    def __init__(self, uri=None, db_name=None):
        self.uri = uri or os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.db_name = db_name or os.getenv("MONGO_DB_NAME", "driving_db")
        self.client = None
        self.db = None
        self.is_connected = False
        self.memory = {
            "sessions": [],
            "raw_nmea": [],
            "drive_points": [],
            "failures": [],
            "reports": [],
            "tracks": [],
        }
        self._connect()

    def _connect(self):
        if MongoClient is None:
            return
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=700)
            self.client.admin.command("ping")
            self.db = self.client[self.db_name]
            self.is_connected = True
            self._ensure_indexes()
        except (PyMongoError, ServerSelectionTimeoutError):
            self.client = None
            self.db = None
            self.is_connected = False

    def _ensure_indexes(self):
        self.db.sessions.create_index("session_id", unique=True)
        self.db.raw_nmea.create_index([("session_id", 1), ("cycle", 1), ("timestamp", 1)])
        self.db.drive_points.create_index([("session_id", 1), ("cycle", 1), ("timestamp", 1)])
        self.db.failures.create_index([("session_id", 1), ("cycle", 1), ("timestamp", 1)])
        self.db.reports.create_index([("session_id", 1), ("cycle", 1), ("created_at", 1)])

    def _insert_one(self, collection, document):
        doc = deepcopy(document)
        doc.setdefault("_id", str(uuid4()))
        if self.is_connected:
            self.db[collection].insert_one(doc)
        else:
            self.memory[collection].append(doc)
        return doc

    def _insert_many(self, collection, documents):
        docs = [deepcopy(document) for document in documents]
        for doc in docs:
            doc.setdefault("_id", str(uuid4()))
        if not docs:
            return {"inserted_count": 0}
        if self.is_connected:
            result = self.db[collection].insert_many(docs)
            return {"inserted_count": len(result.inserted_ids)}
        self.memory[collection].extend(docs)
        return {"inserted_count": len(docs)}

    def _find_many(self, collection, query=None):
        query = query or {}
        if self.is_connected:
            return list(self.db[collection].find(query, {"_id": 0}))
        return [
            deepcopy(document)
            for document in self.memory[collection]
            if all(document.get(key) == value for key, value in query.items())
        ]

    def create_session(self, mode):
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + str(uuid4())[:8]
        document = {
            "session_id": session_id,
            "mode": mode,
            "started_at": datetime.now(),
            "ended_at": None,
            "status": "running",
            "total_cycles": 0,
            "total_points": 0,
            "fail_count": 0,
        }
        self._insert_one("sessions", document)
        return session_id

    def update_session(self, session_id, **fields):
        fields["updated_at"] = datetime.now()
        if self.is_connected:
            self.db.sessions.update_one({"session_id": session_id}, {"$set": fields})
        else:
            for document in self.memory["sessions"]:
                if document.get("session_id") == session_id:
                    document.update(deepcopy(fields))
                    break
        return {"session_id": session_id, **fields}

    def save_raw_nmea(self, document):
        return self._insert_one("raw_nmea", document)

    def save_drive_point(self, document):
        return self._insert_one("drive_points", document)

    def save_failure(self, document):
        return self._insert_one("failures", document)

    def save_report_metadata(self, document):
        return self._insert_one("reports", document)

    def save_result(self, report):
        saved = {
            **deepcopy(report),
            "created_at": datetime.now(),
            "type": "session_summary",
        }
        return self._insert_one("reports", saved)

    def fetch_all_reports(self):
        return self._find_many("reports")

    def fetch_report_by_id(self, report_id):
        reports = self._find_many("reports", {"_id": report_id})
        return reports[0] if reports else None

    def save_path(self, paths):
        return self._insert_many("drive_points", paths)

    def save_track(self, track):
        return self._insert_one("tracks", track)
