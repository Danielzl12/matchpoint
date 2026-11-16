"""Base de datos: esquema, conexión y transacciones. Base compartida (la mantiene el PO).

Dos destinos con la misma interfaz (db.execute("... ?", params), filas con nombre e índice):
  - SQLite  -> desarrollo local y pruebas (por defecto).
  - Postgres (Supabase) -> producción en Vercel; se activa con DATABASE_URL.
"""
import os
import re
import sqlite3
from contextlib import contextmanager

from flask import current_app, g

try:  # solo hace falta cuando se usa Postgres
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

# Para `except IntegrityError:` / `except ErrorBD:` sin importar el motor.
IntegrityError = (sqlite3.IntegrityError,) + ((psycopg.errors.IntegrityError,) if psycopg else ())
ErrorBD = (sqlite3.DatabaseError,) + ((psycopg.DatabaseError,) if psycopg else ())
ESQUEMA_POSTGRES = os.path.join(os.path.dirname(__file__), "esquema_postgres.sql")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    identificador  TEXT NOT NULL UNIQUE COLLATE NOCASE,
    nombre         TEXT NOT NULL,
    clave_hash     TEXT NOT NULL,
    rol            TEXT NOT NULL DEFAULT 'usuario' CHECK (rol IN ('usuario', 'admin')),
    saldo          INTEGER NOT NULL DEFAULT 0 CHECK (saldo >= 0)   -- nunca negativo
);

CREATE TABLE IF NOT EXISTS torneos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    tipo_defecto  TEXT NOT NULL DEFAULT '1X2' CHECK (tipo_defecto IN ('1X2', 'ganador'))
);

CREATE TABLE IF NOT EXISTS equipos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    torneo_id  INTEGER NOT NULL REFERENCES torneos(id),
    nombre     TEXT NOT NULL COLLATE NOCASE,
    UNIQUE (torneo_id, nombre)                                     -- sin equipos repetidos
);

CREATE TABLE IF NOT EXISTS eventos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    torneo_id           INTEGER NOT NULL REFERENCES torneos(id),
    local_id            INTEGER NOT NULL REFERENCES equipos(id),
    visitante_id        INTEGER NOT NULL REFERENCES equipos(id),
    inicio              TEXT NOT NULL,
    cierre              TEXT NOT NULL,
    tipo                TEXT NOT NULL CHECK (tipo IN ('1X2', 'ganador')),
    costo               INTEGER NOT NULL DEFAULT 10 CHECK (costo > 0),
    premio              INTEGER NOT NULL DEFAULT 20 CHECK (premio > 0),
    estado              TEXT NOT NULL DEFAULT 'programado'
                        CHECK (estado IN ('programado', 'finalizado', 'cancelado')),
    resultado           TEXT CHECK (resultado IN ('local', 'empate', 'visitante')),
    version             INTEGER NOT NULL DEFAULT 1,               -- sube con cada corrección de resultado
    premios_repartidos  INTEGER NOT NULL DEFAULT 0,
    CHECK (cierre < inicio),
    CHECK (local_id <> visitante_id)
);

CREATE TABLE IF NOT EXISTS pronosticos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id),
    evento_id   INTEGER NOT NULL REFERENCES eventos(id),
    opcion      TEXT NOT NULL CHECK (opcion IN ('local', 'empate', 'visitante')),
    costo       INTEGER NOT NULL,
    estado      TEXT NOT NULL DEFAULT 'pendiente'
                CHECK (estado IN ('pendiente', 'acertado', 'fallado', 'anulado')),
    creado_en   TEXT NOT NULL,
    UNIQUE (usuario_id, evento_id)                                 -- un pronóstico por evento
);

-- Libro mayor: solo se agregan filas. Las correcciones son movimientos nuevos.
CREATE TABLE IF NOT EXISTS movimientos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id),
    tipo        TEXT NOT NULL
                CHECK (tipo IN ('asignacion', 'participacion', 'premio', 'devolucion', 'ajuste', 'reversion')),
    monto       INTEGER NOT NULL CHECK (monto <> 0),               -- + entra, - sale
    detalle     TEXT NOT NULL DEFAULT '',
    referencia  TEXT NOT NULL UNIQUE,                              -- llave de idempotencia
    creado_en   TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS movimientos_no_update BEFORE UPDATE ON movimientos
BEGIN SELECT RAISE(ABORT, 'El libro de movimientos no se puede modificar'); END;

CREATE TRIGGER IF NOT EXISTS movimientos_no_delete BEFORE DELETE ON movimientos
BEGIN SELECT RAISE(ABORT, 'El libro de movimientos no se puede borrar'); END;

CREATE TABLE IF NOT EXISTS resultados_historial (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    evento_id           INTEGER NOT NULL REFERENCES eventos(id),
    resultado_anterior  TEXT NOT NULL,
    resultado_nuevo     TEXT NOT NULL,
    admin_id            INTEGER NOT NULL REFERENCES usuarios(id),
    creado_en           TEXT NOT NULL
);
"""


class Fila(dict):
    """Fila de Postgres que se comporta como sqlite3.Row: fila["col"], fila[0], dict(fila)."""

    def __getitem__(self, clave):
        if isinstance(clave, int):
            return list(self.values())[clave]
        return super().__getitem__(clave)


def _fabrica_filas(cursor):
    nombres = [c.name for c in cursor.description] if cursor.description else []
    return lambda valores: Fila(zip(nombres, valores))


def _traducir(sql):
    """SQL escrito para SQLite -> Postgres. Devuelve (sql, pide_id)."""
    sql = sql.replace("%", "%%")
    sql = re.sub(r"(?<![:\w]):(\w+)", r"%(\1)s", sql)  # :nombre -> %(nombre)s
    sql = sql.replace("?", "%s")
    sql = re.sub(r"GROUP_CONCAT\(", "string_agg(", sql, flags=re.I)
    sql = sql.replace(
        "datetime('now', 'localtime')",
        "to_char(now() AT TIME ZONE 'America/Bogota', 'YYYY-MM-DD HH24:MI:SS')",
    )
    pide_id = sql.lstrip().upper().startswith("INSERT") and "RETURNING" not in sql.upper()
    if pide_id:
        sql = sql.rstrip().rstrip(";") + " RETURNING id"
    return sql, pide_id


class CursorPG:
    def __init__(self, cursor, pide_id):
        self._cur = cursor
        self.rowcount = cursor.rowcount
        self.lastrowid = None
        if pide_id:
            fila = cursor.fetchone()
            self.lastrowid = fila["id"] if fila else None

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def __iter__(self):
        return iter(self._cur)


class ConexionPG:
    """Envuelve psycopg para que el resto de la app use la misma interfaz que con SQLite."""

    def __init__(self, url):
        # autocommit + prepare_threshold=None: compatible con el pooler de Supabase (puerto 6543).
        self._c = psycopg.connect(url, autocommit=True, prepare_threshold=None, row_factory=_fabrica_filas)

    def execute(self, sql, params=()):
        sql, pide_id = _traducir(sql)
        return CursorPG(self._c.execute(sql, params), pide_id)

    def ejecutar_script(self, sql):
        self._c.execute(sql)

    def close(self):
        self._c.close()


def es_postgres(destino):
    return str(destino).startswith(("postgres://", "postgresql://"))


def conectar(destino):
    """Abre una conexión nueva (ruta de SQLite o URL de Postgres).
    Autocommit: las transacciones se controlan con `transaccion`."""
    if es_postgres(destino):
        return ConexionPG(destino)
    db = sqlite3.connect(destino, timeout=10, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 10000")
    return db


def init_db(destino):
    if es_postgres(destino):
        db = conectar(destino)
        try:
            if db.execute("SELECT to_regclass('public.usuarios') AS t").fetchone()["t"] is None:
                with open(ESQUEMA_POSTGRES, encoding="utf-8") as f:
                    db.ejecutar_script(f.read())
        finally:
            db.close()
        return
    carpeta = os.path.dirname(destino)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    db = conectar(destino)
    db.execute("PRAGMA journal_mode = WAL")
    db.executescript(ESQUEMA)
    db.close()


def get_db():
    if "db" not in g:
        g.db = conectar(current_app.config["DATABASE"])
    return g.db


def cerrar_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@contextmanager
def transaccion(db):
    """Todo o nada. BEGIN IMMEDIATE bloquea a otros escritores, así dos clics o dos
    usuarios a la vez no pueden gastar el mismo saldo ni pagar dos veces un premio."""
    if isinstance(db, ConexionPG):
        db.execute("BEGIN")
        db.execute("SELECT pg_advisory_xact_lock(7355)")  # un solo escritor a la vez, como BEGIN IMMEDIATE
    else:
        db.execute("BEGIN IMMEDIATE")
    try:
        yield db
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
