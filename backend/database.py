
"""SQLite history with automatic backward-compatible sensor column migration."""
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

DEFAULT_DB = Path(__file__).parent / "data" / "fuel.db"

SENSOR_COLUMNS = [
    "tcs_red", "tcs_green", "tcs_blue", "tcs_clear",
    "bmp_pressure",
    "ads_a0", "ads_a1", "ads_a2", "ads_a3",
    "ads_v0", "ads_v1", "ads_v2", "ads_v3",
    "hx711_raw",
]

COLUMNS = [
    "id", "received_at", "device_timestamp", "device_id", "source",
    "sequence", "fuel_type", "temperature", "dielectric",
    *SENSOR_COLUMNS,
    "prediction", "probability_adulterated", "uncertain",
    "model_version", "warnings"
]


def db_path() -> Path:
    return Path(os.getenv("DB_PATH", DEFAULT_DB))


def _connect():
    p = db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(p)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with closing(_connect()) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS readings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            received_at TEXT NOT NULL,
            device_timestamp TEXT,
            device_id TEXT NOT NULL,
            source TEXT NOT NULL,
            sequence INTEGER,
            fuel_type TEXT NOT NULL,
            temperature REAL NOT NULL,
            dielectric REAL NOT NULL,
            prediction TEXT NOT NULL,
            probability_adulterated REAL NOT NULL,
            uncertain INTEGER NOT NULL,
            model_version TEXT NOT NULL,
            warnings TEXT NOT NULL
        )""")

        existing = {
            row["name"]
            for row in c.execute("PRAGMA table_info(readings)").fetchall()
        }

        for col in SENSOR_COLUMNS:
            if col not in existing:
                c.execute(f"ALTER TABLE readings ADD COLUMN {col} REAL")

        c.execute("CREATE INDEX IF NOT EXISTS idx_received ON readings(received_at)")
        c.commit()


def _row(r) -> dict:
    d = dict(r)
    d["uncertain"] = bool(d["uncertain"])
    d["warnings"] = json.loads(d["warnings"])
    return d


def insert(rec: dict) -> int:
    fields = [
        "received_at", "device_timestamp", "device_id", "source",
        "sequence", "fuel_type", "temperature", "dielectric",
        *SENSOR_COLUMNS,
        "prediction", "probability_adulterated", "uncertain",
        "model_version", "warnings"
    ]

    values = []
    for field in fields:
        if field == "uncertain":
            values.append(int(rec[field]))
        elif field == "warnings":
            values.append(json.dumps(rec[field]))
        else:
            values.append(rec.get(field))

    placeholders = ",".join(["?"] * len(fields))
    columns_sql = ",".join(fields)

    with closing(_connect()) as c:
        cur = c.execute(
            f"INSERT INTO readings({columns_sql}) VALUES({placeholders})",
            values
        )
        c.commit()
        return cur.lastrowid


def _where(source, fuel_type, prediction, search):
    cl, args = [], []

    for col, v in (("source", source), ("fuel_type", fuel_type)):
        if v:
            cl.append(f"{col}=?")
            args.append(v)

    if prediction:
        cl.append("prediction LIKE ?")
        args.append(f"{prediction}%")

    if search:
        cl.append(
            "(device_id LIKE ? OR prediction LIKE ? OR fuel_type LIKE ?)"
        )
        args += [f"%{search}%"] * 3

    return (" WHERE " + " AND ".join(cl)) if cl else "", args


def latest(source=None):
    w, a = _where(source, None, None, None)

    with closing(_connect()) as c:
        r = c.execute(
            f"SELECT * FROM readings{w} ORDER BY id DESC LIMIT 1",
            a
        ).fetchone()

    return _row(r) if r else None


def history(limit=100, offset=0, source=None, fuel_type=None,
            prediction=None, search=None):

    w, a = _where(source, fuel_type, prediction, search)

    with closing(_connect()) as c:
        total = c.execute(
            f"SELECT COUNT(*) FROM readings{w}", a
        ).fetchone()[0]

        rows = c.execute(
            f"SELECT * FROM readings{w} ORDER BY id DESC LIMIT ? OFFSET ?",
            a + [limit, offset]
        ).fetchall()

    return total, [_row(r) for r in rows]
