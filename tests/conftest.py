from datetime import datetime, timedelta

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.db import conectar, transaccion
from app.ledger import registrar_movimiento


def hora(**delta):
    return (datetime.now() + timedelta(**delta)).strftime("%Y-%m-%d %H:%M:%S")


@pytest.fixture()
def app(tmp_path):
    return create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True})


@pytest.fixture()
def db(app):
    conexion = conectar(app.config["DATABASE"])
    yield conexion
    conexion.close()


@pytest.fixture()
def client(app):
    return app.test_client()


def nuevo_cliente(app):
    return app.test_client()


def crear_usuario(db, ident, rol="usuario", saldo=0, clave="clave123"):
    with transaccion(db):
        uid = db.execute(
            "INSERT INTO usuarios (identificador, nombre, clave_hash, rol) VALUES (?, ?, ?, ?)",
            (ident, ident.title(), generate_password_hash(clave), rol),
        ).lastrowid
        if saldo:
            registrar_movimiento(db, uid, "asignacion", saldo, "inicial", f"test:{ident}")
    return uid


def entrar(cliente, ident, clave="clave123"):
    return cliente.post("/login", data={"identificador": ident, "clave": clave}, follow_redirects=True)


def crear_torneo(db, nombre="Liga", equipos=("A", "B", "C")):
    with transaccion(db):
        tid = db.execute("INSERT INTO torneos (nombre) VALUES (?)", (nombre,)).lastrowid
        ids = [
            db.execute("INSERT INTO equipos (torneo_id, nombre) VALUES (?, ?)", (tid, n)).lastrowid
            for n in equipos
        ]
    return tid, ids


def crear_evento(db, torneo, local, visitante, cierre=None, inicio=None, tipo="1X2", costo=10, premio=20):
    cierre = cierre or hora(hours=1)
    inicio = inicio or hora(hours=2)
    return db.execute(
        "INSERT INTO eventos (torneo_id, local_id, visitante_id, inicio, cierre, tipo, costo, premio) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (torneo, local, visitante, inicio, cierre, tipo, costo, premio),
    ).lastrowid


@pytest.fixture()
def escenario(app, db):
    """admin, ana (100), luis (100), torneo con 3 equipos."""
    datos = {
        "admin": crear_usuario(db, "admin", rol="admin"),
        "ana": crear_usuario(db, "ana", saldo=100),
        "luis": crear_usuario(db, "luis", saldo=100),
    }
    datos["torneo"], datos["equipos"] = crear_torneo(db)
    return datos


def saldo(db, uid):
    return db.execute("SELECT saldo FROM usuarios WHERE id = ?", (uid,)).fetchone()[0]


def suma(db, uid):
    return db.execute("SELECT COALESCE(SUM(monto),0) FROM movimientos WHERE usuario_id = ?", (uid,)).fetchone()[0]
