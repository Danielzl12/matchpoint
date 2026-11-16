"""HU10 Registrar resultado de un evento · HU11 Pagar premios a los ganadores. Responsable: Juan Sebastián Barreto."""
from flask import Blueprint, abort, flash, redirect, render_template, request

from .db import get_db, transaccion
from .ledger import liquidar
from .reglas import OPCIONES, ErrorNegocio, cargar_evento, estado_evento
from .seguridad import admin_requerido

bp = Blueprint("resultados", __name__)


@bp.route("/admin/eventos/<int:evento_id>/resultado", methods=["GET", "POST"])
@admin_requerido
def registrar(evento_id):
    db = get_db()
    if cargar_evento(db, evento_id) is None:
        abort(404)

    if request.method == "POST":
        resultado = request.form.get("resultado", "")
        try:
            with transaccion(db):
                ev = cargar_evento(db, evento_id)
                if ev["estado"] == "cancelado":
                    raise ErrorNegocio("Este evento fue cancelado.")
                if ev["estado"] == "finalizado":
                    raise ErrorNegocio("Este evento ya tiene resultado. Para cambiarlo usa «Corregir resultado».")
                if estado_evento(ev) == "abierto":
                    raise ErrorNegocio("El evento todavía no ha cerrado: no se puede registrar el resultado.")
                if resultado not in OPCIONES[ev["tipo"]]:
                    raise ErrorNegocio("Elige un resultado válido para este evento.")
                db.execute(
                    "UPDATE eventos SET estado = 'finalizado', resultado = ?, version = 1, "
                    "premios_repartidos = 1 WHERE id = ?",
                    (resultado, evento_id),
                )
                ganadores = liquidar(db, ev, resultado, 1)
        except ErrorNegocio as error:
            flash(str(error), "error")
        else:
            flash(f"Resultado registrado. Se pagó premio a {ganadores} ganador(es).", "ok")
            return redirect("/admin/eventos")

    ev = dict(cargar_evento(db, evento_id))
    return render_template("resultados/registrar.html", ev=ev, opciones=OPCIONES[ev["tipo"]])
