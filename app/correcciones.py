"""HU12 Cancelar evento y devolver créditos · HU13 Corregir resultado · HU14 Corregir saldo con motivo.
Responsable: Dana Valentina Quevedo."""
import re
from uuid import uuid4

from flask import Blueprint, abort, flash, redirect, render_template, request

from .db import get_db, transaccion
from .ledger import SaldoInsuficiente, liquidar, registrar_movimiento
from .reglas import OPCIONES, ErrorNegocio, cargar_evento
from .seguridad import admin_requerido
from .reglas import entero

bp = Blueprint("correcciones", __name__)


@bp.route("/admin/eventos/<int:evento_id>/cancelar", methods=["GET", "POST"])
@admin_requerido
def cancelar(evento_id):
    db = get_db()
    if cargar_evento(db, evento_id) is None:
        abort(404)

    if request.method == "POST":  # el POST es la confirmación del administrador
        try:
            with transaccion(db):
                ev = cargar_evento(db, evento_id)
                if ev["estado"] == "cancelado":
                    raise ErrorNegocio("Este evento ya estaba cancelado.")
                if ev["estado"] == "finalizado":
                    raise ErrorNegocio("No se puede cancelar un evento que ya tiene resultado.")
                devueltos = 0
                for p in db.execute(
                    "SELECT * FROM pronosticos WHERE evento_id = ? AND estado <> 'anulado'", (evento_id,)
                ).fetchall():
                    registrar_movimiento(
                        db, p["usuario_id"], "devolucion", p["costo"],
                        f"Devolución: evento cancelado {ev['local']} vs {ev['visitante']}", f"dev:{p['id']}",
                    )
                    db.execute("UPDATE pronosticos SET estado = 'anulado' WHERE id = ?", (p["id"],))
                    devueltos += 1
                db.execute("UPDATE eventos SET estado = 'cancelado' WHERE id = ?", (evento_id,))
        except ErrorNegocio as error:
            flash(str(error), "error")
        else:
            flash(f"Evento cancelado. Se devolvieron los créditos a {devueltos} participante(s).", "ok")
        return redirect("/admin/eventos")

    ev = dict(cargar_evento(db, evento_id))
    cantidad = db.execute(
        "SELECT COUNT(*) FROM pronosticos WHERE evento_id = ? AND estado <> 'anulado'", (evento_id,)
    ).fetchone()[0]
    return render_template("correcciones/cancelar.html", ev=ev, cantidad=cantidad)


@bp.route("/admin/eventos/<int:evento_id>/corregir-resultado", methods=["GET", "POST"])
@admin_requerido
def corregir_resultado(evento_id):
    db = get_db()
    if cargar_evento(db, evento_id) is None:
        abort(404)

    if request.method == "POST":
        nuevo = request.form.get("resultado", "")
        try:
            with transaccion(db):
                ev = cargar_evento(db, evento_id)
                if ev["estado"] != "finalizado":
                    raise ErrorNegocio("Solo se puede corregir el resultado de un evento finalizado.")
                if nuevo not in OPCIONES[ev["tipo"]]:
                    raise ErrorNegocio("Elige un resultado válido para este evento.")
                if nuevo == ev["resultado"]:
                    raise ErrorNegocio("Ese ya es el resultado registrado.")
                anterior, version = ev["resultado"], ev["version"]

                # 1) Quitar los premios pagados con el resultado anterior (movimientos nuevos, no se borra nada).
                for p in db.execute(
                    "SELECT * FROM pronosticos WHERE evento_id = ? AND estado = 'acertado'", (evento_id,)
                ).fetchall():
                    try:
                        registrar_movimiento(
                            db, p["usuario_id"], "reversion", -ev["premio"],
                            f"Reversión de premio por corrección: {ev['local']} vs {ev['visitante']}",
                            f"rev:{p['id']}:v{version}",
                        )
                    except SaldoInsuficiente:
                        raise ErrorNegocio(
                            "No se puede corregir: un ganador anterior ya gastó el premio y quedaría con saldo negativo."
                        ) from None

                # 2) Guardar el resultado anterior y volver a repartir premios con el nuevo.
                db.execute(
                    "INSERT INTO resultados_historial (evento_id, resultado_anterior, resultado_nuevo, admin_id, creado_en) "
                    "VALUES (?, ?, ?, ?, datetime('now', 'localtime'))",
                    (evento_id, anterior, nuevo, _admin_id()),
                )
                db.execute(
                    "UPDATE eventos SET resultado = ?, version = ? WHERE id = ?", (nuevo, version + 1, evento_id)
                )
                ganadores = liquidar(db, ev, nuevo, version + 1)
        except ErrorNegocio as error:
            flash(str(error), "error")
        else:
            flash(f"Resultado corregido. Premios recalculados: {ganadores} ganador(es).", "ok")
            return redirect("/admin/eventos")

    ev = dict(cargar_evento(db, evento_id))
    historial = db.execute(
        "SELECT * FROM resultados_historial WHERE evento_id = ? ORDER BY id DESC", (evento_id,)
    ).fetchall()
    return render_template(
        "correcciones/resultado.html", ev=ev, opciones=OPCIONES[ev["tipo"]], historial=historial
    )


def _admin_id():
    from .seguridad import usuario_actual

    return usuario_actual()["id"]


@bp.route("/admin/saldos/corregir", methods=["GET", "POST"])
@admin_requerido
def corregir_saldo():
    db = get_db()
    referencia = f"ajuste:{uuid4().hex}"
    if request.method == "POST":
        usuario_id = entero(request.form.get("usuario_id"))
        monto = entero(request.form.get("monto"))
        motivo = request.form.get("motivo", "").strip()
        referencia = request.form.get("referencia", "")
        destino = db.execute(
            "SELECT * FROM usuarios WHERE id = ? AND rol = 'usuario'", (usuario_id,)
        ).fetchone()
        if destino is None:
            flash("Elige un usuario de la lista.", "error")
        elif not monto:
            flash("Indica un monto distinto de 0 (negativo para descontar).", "error")
        elif not motivo:
            flash("El motivo es obligatorio.", "error")
        elif not re.fullmatch(r"ajuste:[0-9a-f]{32}", referencia):
            flash("El formulario venció. Vuelve a intentarlo.", "error")
        else:
            try:
                with transaccion(db):
                    nuevo = registrar_movimiento(
                        db, destino["id"], "ajuste", monto, f"Corrección: {motivo}", referencia
                    )
            except SaldoInsuficiente:
                flash("El descuento dejaría el saldo del usuario en negativo.", "error")
            else:
                flash(
                    "Corrección registrada." if nuevo else "Esta corrección ya estaba registrada.",
                    "ok" if nuevo else "error",
                )
                return redirect("/admin/saldos/corregir")
        referencia = f"ajuste:{uuid4().hex}"

    usuarios = db.execute("SELECT * FROM usuarios WHERE rol = 'usuario' ORDER BY nombre").fetchall()
    ajustes = db.execute(
        "SELECT m.*, u.nombre FROM movimientos m JOIN usuarios u ON u.id = m.usuario_id "
        "WHERE m.tipo = 'ajuste' ORDER BY m.id DESC LIMIT 20"
    ).fetchall()
    return render_template("correcciones/ajuste.html", usuarios=usuarios, ajustes=ajustes, referencia=referencia)
