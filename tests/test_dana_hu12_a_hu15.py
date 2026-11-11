"""Dana: HU12 cancelar · HU13 corregir resultado · HU14 corregir saldo · HU15 reportes."""
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


def finalizar(db, ev, resultado):
    """Deja el evento finalizado y paga premios directamente (no depende del módulo de otra persona)."""
    from app.db import transaccion
    from app.ledger import liquidar
    from app.reglas import cargar_evento

    with transaccion(db):
        db.execute("UPDATE eventos SET estado = 'finalizado', resultado = ?, version = 1 WHERE id = ?", (resultado, ev))
        liquidar(db, cargar_evento(db, ev), resultado, 1)


def admin_de(client):
    c = client.application.test_client(); entrar(c, "admin"); return c


def test_hu12_cancelar_devuelve_creditos(client, db, escenario):
    ev = evento_con_pronosticos(client, db, escenario, [("ana", "empate"), ("luis", "empate")], abierto=True)
    admin = admin_de(client)
    assert "¿Cancelar" in admin.get(f"/admin/eventos/{ev}/cancelar").text
    admin.post(f"/admin/eventos/{ev}/cancelar")
    admin.post(f"/admin/eventos/{ev}/cancelar")  # repetir no devuelve doble
    for u in ("ana", "luis"):
        assert saldo(db, escenario[u]) == 100 == suma(db, escenario[u])
    assert db.execute("SELECT COUNT(*) FROM movimientos WHERE tipo='devolucion'").fetchone()[0] == 2


def test_hu12_no_cancela_evento_finalizado(client, db, escenario):
    ev = evento_con_pronosticos(client, db, escenario, [("ana", "local")])
    admin = admin_de(client)
    finalizar(db, ev, "local")
    assert "ya tiene resultado" in admin.post(f"/admin/eventos/{ev}/cancelar", follow_redirects=True).text


def test_hu13_corregir_resultado_recalcula(client, db, escenario):
    ev = evento_con_pronosticos(client, db, escenario, [("ana", "local"), ("luis", "visitante")])
    admin = admin_de(client)
    finalizar(db, ev, "local")
    assert saldo(db, escenario["ana"]) == 110 and saldo(db, escenario["luis"]) == 90
    admin.post(f"/admin/eventos/{ev}/corregir-resultado", data={"resultado": "visitante"})
    assert saldo(db, escenario["ana"]) == 90
    assert saldo(db, escenario["luis"]) == 110
    for u in ("ana", "luis"):
        assert saldo(db, escenario[u]) == suma(db, escenario[u])
    h = db.execute("SELECT * FROM resultados_historial").fetchall()
    assert len(h) == 1 and h[0]["resultado_anterior"] == "local" and h[0]["resultado_nuevo"] == "visitante"
    # corregir de nuevo al original también funciona (versiones distintas, sin choques de referencia)
    admin.post(f"/admin/eventos/{ev}/corregir-resultado", data={"resultado": "local"})
    assert saldo(db, escenario["ana"]) == 110 and saldo(db, escenario["luis"]) == 90


def test_hu13_aborta_si_el_ganador_ya_gasto_el_premio(client, db, escenario):
    ev = evento_con_pronosticos(client, db, escenario, [("ana", "local")])
    admin = admin_de(client)
    finalizar(db, ev, "local")
    db.execute("UPDATE usuarios SET saldo = 5 WHERE id = ?", (escenario["ana"],))  # simula que gastó
    r = admin.post(f"/admin/eventos/{ev}/corregir-resultado", data={"resultado": "visitante"})
    assert "ya gastó" in r.text
    assert db.execute("SELECT resultado FROM eventos WHERE id=?", (ev,)).fetchone()[0] == "local"


def test_hu14_ajuste_con_motivo_sin_borrar_original(client, db, escenario):
    admin = admin_de(client)
    import re
    ref = re.search(r'name="referencia" value="([^"]+)"', admin.get("/admin/saldos/corregir").text).group(1)
    base = {"usuario_id": escenario["ana"], "monto": 15, "referencia": ref}
    assert "motivo es obligatorio" in admin.post("/admin/saldos/corregir", data={**base, "motivo": " "}).text
    admin.post("/admin/saldos/corregir", data={**base, "motivo": "Error de carga"})
    admin.post("/admin/saldos/corregir", data={**base, "motivo": "Error de carga"})  # reenvío
    assert saldo(db, escenario["ana"]) == 115 == suma(db, escenario["ana"])
    assert db.execute("SELECT COUNT(*) FROM movimientos WHERE usuario_id=?", (escenario["ana"],)).fetchone()[0] == 2


def test_hu14_descuento_no_deja_saldo_negativo(client, db, escenario):
    admin = admin_de(client)
    import re
    ref = re.search(r'name="referencia" value="([^"]+)"', admin.get("/admin/saldos/corregir").text).group(1)
    r = admin.post("/admin/saldos/corregir", data={"usuario_id": escenario["ana"], "monto": -999, "motivo": "x", "referencia": ref})
    assert "negativo" in r.text and saldo(db, escenario["ana"]) == 100


def test_hu15_reportes_marcan_diferencias(client, db, escenario):
    admin = admin_de(client)
    html = admin.get("/admin/reportes").text
    assert "Liga" in html and "ana" in html and "con diferencia" not in html
    db.execute("UPDATE usuarios SET saldo = saldo + 7 WHERE id = ?", (escenario["luis"],))  # alguien tocó el saldo a mano
    html = admin.get("/admin/reportes").text
    assert "1 usuario(s) con diferencia" in html and 'class="alerta"' in html


def test_hu15_solo_admin(client, escenario):
    entrar(client, "ana")
    assert client.get("/admin/reportes").status_code == 403
