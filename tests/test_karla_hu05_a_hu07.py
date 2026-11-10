"""Karla: HU05 listar · HU06 pronosticar · HU07 asignar créditos."""
import threading

from app.db import conectar, transaccion
from app.ledger import SaldoInsuficiente, registrar_movimiento

from .conftest import crear_evento, entrar, hora, saldo, suma


def test_hu05_lista_eventos_con_estado(client, db, escenario):
    a, b, c = escenario["equipos"]
    crear_evento(db, escenario["torneo"], a, b)
    crear_evento(db, escenario["torneo"], b, c, cierre=hora(hours=-1), inicio=hora(hours=1))
    entrar(client, "ana")
    html = client.get("/torneos").text
    assert "Liga" in html and "abierto" in html and "cerrado" in html and "A vs B" in html


def test_hu06_pronostico_descuenta_y_registra(client, db, escenario):
    a, b, _ = escenario["equipos"]
    ev = crear_evento(db, escenario["torneo"], a, b)
    entrar(client, "ana")
    r = client.post(f"/eventos/{ev}/pronosticar", data={"opcion": "local"}, follow_redirects=True)
    assert "Pronóstico registrado" in r.text
    assert saldo(db, escenario["ana"]) == 90 == suma(db, escenario["ana"])


def test_hu06_no_acepta_despues_del_cierre(client, db, escenario):
    a, b, _ = escenario["equipos"]
    ev = crear_evento(db, escenario["torneo"], a, b, cierre=hora(minutes=-5), inicio=hora(hours=1))
    entrar(client, "ana")
    r = client.post(f"/eventos/{ev}/pronosticar", data={"opcion": "local"})
    assert "ya cerró" in r.text and saldo(db, escenario["ana"]) == 100


def test_hu06_sin_creditos_suficientes(client, db, escenario):
    a, b, _ = escenario["equipos"]
    ev = crear_evento(db, escenario["torneo"], a, b, costo=500)
    entrar(client, "ana")
    r = client.post(f"/eventos/{ev}/pronosticar", data={"opcion": "local"})
    assert "créditos suficientes" in r.text
    assert saldo(db, escenario["ana"]) == 100
    assert db.execute("SELECT COUNT(*) FROM pronosticos").fetchone()[0] == 0  # nada quedó a medias


def test_hu06_doble_clic_cobra_una_sola_vez(client, db, escenario):
    a, b, _ = escenario["equipos"]
    ev = crear_evento(db, escenario["torneo"], a, b)
    entrar(client, "ana")
    client.post(f"/eventos/{ev}/pronosticar", data={"opcion": "local"})
    r = client.post(f"/eventos/{ev}/pronosticar", data={"opcion": "local"})
    assert "Ya hiciste" in r.text and saldo(db, escenario["ana"]) == 90


def test_hu06_concurrencia_no_gasta_dos_veces(app, db, escenario):
    a, b, _ = escenario["equipos"]
    ev = crear_evento(db, escenario["torneo"], a, b)
    resultados = []

    def clic():
        cliente = app.test_client()
        entrar(cliente, "ana")
        resultados.append(cliente.post(f"/eventos/{ev}/pronosticar", data={"opcion": "empate"}).status_code)

    hilos = [threading.Thread(target=clic) for _ in range(5)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert saldo(db, escenario["ana"]) == 90
    assert db.execute("SELECT COUNT(*) FROM pronosticos").fetchone()[0] == 1


def test_hu07_asignar_con_confirmacion(client, db, escenario):
    entrar(client, "admin")
    paso1 = client.post("/admin/creditos", data={"usuario_id": escenario["ana"], "monto": 50})
    assert "Confirmar" in paso1.text and saldo(db, escenario["ana"]) == 100  # todavía no se aplicó
    import re
    ref = re.search(r'name="referencia" value="([^"]+)"', paso1.text).group(1)
    datos = {"usuario_id": escenario["ana"], "monto": 50, "referencia": ref, "accion": "confirmar"}
    client.post("/admin/creditos", data=datos)
    client.post("/admin/creditos", data=datos)  # reenvío: no duplica
    assert saldo(db, escenario["ana"]) == 150 == suma(db, escenario["ana"])


def test_hu07_monto_invalido_y_permisos(client, escenario):
    entrar(client, "admin")
    assert "entre 1" in client.post("/admin/creditos", data={"usuario_id": escenario["ana"], "monto": -5}).text
    entrar(client, "ana")
    assert client.get("/admin/creditos").status_code == 403


def test_ledger_idempotente_y_no_negativo(db, escenario):
    uid = escenario["ana"]
    with transaccion(db):
        assert registrar_movimiento(db, uid, "ajuste", 5, "x", "dup") is True
        assert registrar_movimiento(db, uid, "ajuste", 5, "x", "dup") is False
    assert saldo(db, uid) == 105
    try:
        with transaccion(db):
            registrar_movimiento(db, uid, "ajuste", -9999, "x", "neg")
    except SaldoInsuficiente:
        pass
    assert saldo(db, uid) == 105 == suma(db, uid)


def test_ledger_no_se_puede_borrar_ni_editar(db, escenario):
    import sqlite3
    for sql in ("UPDATE movimientos SET monto = 1", "DELETE FROM movimientos"):
        try:
            db.execute(sql)
            raise AssertionError("debía fallar")
        except sqlite3.DatabaseError:
            pass
