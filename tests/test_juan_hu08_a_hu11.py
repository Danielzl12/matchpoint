"""Juan: HU08 saldo · HU09 mis pronósticos · HU10 resultado · HU11 premios."""
from .conftest import crear_evento, entrar, hora, saldo, suma


def evento_con_pronosticos(client, db, esc, apuestas, abierto=False):
    """Crea un evento y los pronósticos directamente en la base (no depende del módulo de otra persona)."""
    from app.db import transaccion
    from app.ledger import registrar_movimiento

    a, b, _ = esc["equipos"]
    if abierto:
        ev = crear_evento(db, esc["torneo"], a, b)
    else:  # ya cerró
        ev = crear_evento(db, esc["torneo"], a, b, cierre=hora(minutes=-1), inicio=hora(hours=1))
    with transaccion(db):
        for ident, opcion in apuestas:
            pid = db.execute(
                "INSERT INTO pronosticos (usuario_id, evento_id, opcion, costo, creado_en) "
                "VALUES (?, ?, ?, 10, datetime('now', 'localtime'))",
                (esc[ident], ev, opcion),
            ).lastrowid
            registrar_movimiento(db, esc[ident], "participacion", -10, "Pronóstico de prueba", f"pron:{pid}")
    return ev


def test_hu08_saldo_es_la_suma_y_solo_lo_propio(client, db, escenario):
    entrar(client, "ana")
    html = client.get("/mi-saldo").text
    assert "100 créditos" in html and "inicial" in html
    # el movimiento de luis no aparece en la vista de ana
    assert html.count("<tr>") == 2


def test_hu09_estados_pendiente_acertado_fallado(client, db, escenario):
    ev = evento_con_pronosticos(client, db, escenario, [("ana", "local"), ("luis", "visitante")])
    c = client.application.test_client(); entrar(c, "ana")
    assert "pendiente" in c.get("/mis-pronosticos").text
    admin = client.application.test_client(); entrar(admin, "admin")
    admin.post(f"/admin/eventos/{ev}/resultado", data={"resultado": "local"})
    assert "acertado" in c.get("/mis-pronosticos").text
    c2 = client.application.test_client(); entrar(c2, "luis")
    assert "fallado" in c2.get("/mis-pronosticos").text


def test_hu10_solo_con_evento_cerrado(client, db, escenario):
    a, b, _ = escenario["equipos"]
    ev = crear_evento(db, escenario["torneo"], a, b)  # sigue abierto
    entrar(client, "admin")
    r = client.post(f"/admin/eventos/{ev}/resultado", data={"resultado": "local"})
    assert "todavía no ha cerrado" in r.text
    assert db.execute("SELECT estado FROM eventos WHERE id=?", (ev,)).fetchone()[0] == "programado"


def test_hu10_solo_admin(client, db, escenario):
    ev = evento_con_pronosticos(client, db, escenario, [])
    entrar(client, "ana")
    assert client.post(f"/admin/eventos/{ev}/resultado", data={"resultado": "local"}).status_code == 403


def test_hu11_ganador_cobra_una_vez(client, db, escenario):
    ev = evento_con_pronosticos(client, db, escenario, [("ana", "local"), ("luis", "visitante")])
    entrar(client, "admin")
    client.post(f"/admin/eventos/{ev}/resultado", data={"resultado": "local"})
    assert saldo(db, escenario["ana"]) == 110  # 100 - 10 + 20
    assert saldo(db, escenario["luis"]) == 90
    r = client.post(f"/admin/eventos/{ev}/resultado", data={"resultado": "local"})  # repetir
    assert "ya tiene resultado" in r.text
    assert saldo(db, escenario["ana"]) == 110 == suma(db, escenario["ana"])


def test_hu11_liquidar_es_idempotente(db, client, escenario):
    from app.db import transaccion
    from app.ledger import liquidar
    from app.reglas import cargar_evento
    ev = evento_con_pronosticos(client, db, escenario, [("ana", "local")])
    with transaccion(db):
        assert liquidar(db, cargar_evento(db, ev), "local", 1) == 1
        assert liquidar(db, cargar_evento(db, ev), "local", 1) == 0
    assert saldo(db, escenario["ana"]) == 110
