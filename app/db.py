"""Base de datos SQLite: esquema, conexión y transacciones. Base compartida (la mantiene el PO)."""
import os
import sqlite3
from contextlib import contextmanager

from flask import current_app, g

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


def conectar(ruta):
    """Abre una conexión nueva. Autocommit: las transacciones se controlan con `transaccion`."""
    db = sqlite3.connect(ruta, timeout=10, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 10000")
    return db


def init_db(ruta):
    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    db = conectar(ruta)
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
    db.execute("BEGIN IMMEDIATE")
    try:
        yield db
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
