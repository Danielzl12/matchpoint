"""Libro mayor de créditos (append-only). Base compartida: todos los módulos que mueven créditos lo usan."""
import sqlite3

from .reglas import ahora_str


class SaldoInsuficiente(Exception):
    """El movimiento dejaría el saldo del usuario en negativo."""


def registrar_movimiento(db, usuario_id, tipo, monto, detalle, referencia):
    """Escribe un movimiento y actualiza el saldo del usuario.

    - Llamar SIEMPRE dentro de `with transaccion(db):`.
    - Idempotente: si ya existe un movimiento con esa `referencia`, no hace nada y devuelve False.
    - Si el saldo quedaría negativo lanza SaldoInsuficiente (la transacción se revierte entera).
    """
    if db.execute("SELECT 1 FROM movimientos WHERE referencia = ?", (referencia,)).fetchone():
        return False
    db.execute(
        "INSERT INTO movimientos (usuario_id, tipo, monto, detalle, referencia, creado_en) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (usuario_id, tipo, monto, detalle, referencia, ahora_str()),
    )
    try:
        db.execute("UPDATE usuarios SET saldo = saldo + ? WHERE id = ?", (monto, usuario_id))
    except sqlite3.IntegrityError:
        raise SaldoInsuficiente() from None
    return True


def liquidar(db, ev, resultado, version):
    """Marca pronósticos como acertado/fallado y paga el premio a cada ganador UNA sola vez.

    La referencia `premio:<pronostico>:v<version>` hace que repetir la llamada no cobre doble.
    Devuelve cuántos premios se pagaron. Llamar dentro de `with transaccion(db):`.
    """
    pagados = 0
    pronosticos = db.execute(
        "SELECT * FROM pronosticos WHERE evento_id = ? AND estado <> 'anulado'", (ev["id"],)
    ).fetchall()
    for p in pronosticos:
        if p["opcion"] == resultado:
            db.execute("UPDATE pronosticos SET estado = 'acertado' WHERE id = ?", (p["id"],))
            if registrar_movimiento(
                db, p["usuario_id"], "premio", ev["premio"],
                f"Premio {ev['local']} vs {ev['visitante']}", f"premio:{p['id']}:v{version}",
            ):
                pagados += 1
        else:
            db.execute("UPDATE pronosticos SET estado = 'fallado' WHERE id = ?", (p["id"],))
    return pagados


def suma_movimientos(db, usuario_id):
    return db.execute(
        "SELECT COALESCE(SUM(monto), 0) FROM movimientos WHERE usuario_id = ?", (usuario_id,)
    ).fetchone()[0]
