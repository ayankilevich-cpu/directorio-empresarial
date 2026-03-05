import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "directorio.db")

COLUMNS = [
    "empresa", "cargo", "nombre", "direccion",
    "codigo_postal", "ciudad", "telefono",
    "email", "web", "actividad", "seccion",
]


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.execute(
        """
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
    )
    conn.commit()
    conn.close()


def insert_rows(rows: list[dict]):
    conn = _connect()
    placeholders = ", ".join("?" for _ in COLUMNS)
    col_names = ", ".join(COLUMNS)
    for row in rows:
        values = tuple(row.get(col, "") for col in COLUMNS)
        conn.execute(
            f"INSERT INTO directorio ({col_names}) VALUES ({placeholders})",
            values,
        )
    conn.commit()
    conn.close()


def get_all_rows() -> list[dict]:
    conn = _connect()
    cursor = conn.execute("SELECT * FROM directorio ORDER BY id")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def delete_row(row_id: int):
    conn = _connect()
    conn.execute("DELETE FROM directorio WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()


def clear_all():
    conn = _connect()
    conn.execute("DELETE FROM directorio")
    conn.commit()
    conn.close()
