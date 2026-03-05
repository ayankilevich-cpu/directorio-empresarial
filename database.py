import sqlite3
import os

import requests as _requests

COLUMNS = [
    "empresa", "cargo", "nombre", "direccion",
    "codigo_postal", "ciudad", "telefono",
    "email", "web", "actividad", "seccion",
]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS directorio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa TEXT,
    cargo TEXT,
    nombre TEXT,
    direccion TEXT,
    codigo_postal TEXT,
    ciudad TEXT,
    telefono TEXT,
    email TEXT,
    web TEXT,
    actividad TEXT,
    seccion TEXT,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


# ── Configuración Turso ─────────────────────────────────────────

def _get_turso_config():
    """Devuelve (url, token) si están configurados, o (None, None)."""
    try:
        import streamlit as st
        url = st.secrets.get("TURSO_DATABASE_URL", "")
        token = st.secrets.get("TURSO_AUTH_TOKEN", "")
        if url and token:
            return url, token
    except Exception:
        pass
    url = os.environ.get("TURSO_DATABASE_URL", "")
    token = os.environ.get("TURSO_AUTH_TOKEN", "")
    if url and token:
        return url, token
    return None, None


def _use_turso() -> bool:
    url, _ = _get_turso_config()
    return url is not None


def _turso_http_url():
    url, _ = _get_turso_config()
    return url.replace("libsql://", "https://")


def _turso_execute(statements: list[dict]) -> list[dict]:
    """Ejecuta sentencias SQL en Turso vía HTTP Pipeline API."""
    _, token = _get_turso_config()
    http_url = f"{_turso_http_url()}/v2/pipeline"

    body = {
        "requests": [
            {"type": "execute", "stmt": stmt}
            for stmt in statements
        ] + [{"type": "close"}]
    }

    resp = _requests.post(
        http_url,
        json=body,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def _turso_query(sql: str, args: list | None = None) -> list[dict]:
    """Ejecuta una sentencia y devuelve los resultados."""
    stmt = {"sql": sql}
    if args:
        stmt["args"] = [{"type": "text", "value": str(v)} for v in args]
    return _turso_execute([stmt])


# ── SQLite local (fallback) ─────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "directorio.db")


def _connect_local():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── API pública ─────────────────────────────────────────────────

def init_db():
    if _use_turso():
        _turso_query(CREATE_TABLE_SQL)
    else:
        conn = _connect_local()
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()
        conn.close()


def insert_rows(rows: list[dict]):
    col_names = ", ".join(COLUMNS)
    placeholders = ", ".join("?" for _ in COLUMNS)
    sql = f"INSERT INTO directorio ({col_names}) VALUES ({placeholders})"

    if _use_turso():
        stmts = []
        for row in rows:
            values = [row.get(col, "") for col in COLUMNS]
            stmts.append({
                "sql": sql,
                "args": [{"type": "text", "value": str(v)} for v in values],
            })
        _turso_execute(stmts)
    else:
        conn = _connect_local()
        for row in rows:
            values = tuple(row.get(col, "") for col in COLUMNS)
            conn.execute(sql, values)
        conn.commit()
        conn.close()


def get_all_rows() -> list[dict]:
    sql = "SELECT * FROM directorio ORDER BY id"

    if _use_turso():
        results = _turso_query(sql)
        if not results or "response" not in results[0]:
            return []
        resp = results[0]["response"]["result"]
        cols = [c["name"] for c in resp["cols"]]
        return [
            dict(zip(cols, [cell["value"] if cell["type"] != "null" else "" for cell in row]))
            for row in resp["rows"]
        ]
    else:
        conn = _connect_local()
        cursor = conn.execute(sql)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows


def delete_row(row_id: int):
    sql = "DELETE FROM directorio WHERE id = ?"
    if _use_turso():
        _turso_query(sql, [row_id])
    else:
        conn = _connect_local()
        conn.execute(sql, (row_id,))
        conn.commit()
        conn.close()


def clear_all():
    sql = "DELETE FROM directorio"
    if _use_turso():
        _turso_query(sql)
    else:
        conn = _connect_local()
        conn.execute(sql)
        conn.commit()
        conn.close()
