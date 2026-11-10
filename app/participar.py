"""HU05 Ver torneos y eventos · HU06 Hacer un pronóstico. Responsable: Karla Nicole Martín."""
import sqlite3

from flask import Blueprint, abort, flash, redirect, render_template, request

from .db import get_db, transaccion
from .ledger import SaldoInsuficiente, registrar_movimiento
from .reglas import OPCIONES, SELECT_EVENTO, ErrorNegocio, cargar_evento, estado_evento
from .seguridad import login_requerido, usuario_actual

bp = Blueprint("participar", __name__)


@bp.route("/torneos")
@login_requerido
def lista():
    db = get_db()
    eventos = [dict(e) for e in db.execute(SELECT_EVENTO + " ORDER BY t.nombre, e.inicio").fetchall()]
    mios = {
        f["evento_id"]
        for f in db.execute(
            "SELECT evento_id FROM pronosticos WHERE usuario_id = ? AND estado <> 'anulado'",
            (usuario_actual()["id"],),
        )
    }
    return render_template("participar/lista.html", eventos=eventos, mios=mios)


@bp.route("/eventos/<int:evento_id>/pronosticar", methods=["GET", "POST"])
@login_requerido
def pronosticar(evento_id):
    db = get_db()
    usuario = usuario_actual()
    ev = cargar_evento(db, evento_id)
    if ev is None:
        abort(404)

    if request.method == "POST":
        opcion = request.form.get("opcion", "")
        try:
            with transaccion(db):
                ev = cargar_evento(db, evento_id)
                if estado_evento(ev) != "abierto":
                    raise ErrorNegocio("Este evento ya cerró: no se aceptan más pronósticos.")
                if opcion not in OPCIONES[ev["tipo"]]:
                    raise ErrorNegocio("Elige una de las opciones del evento.")
                try:
                    pronostico_id = db.execute(
                        "INSERT INTO pronosticos (usuario_id, evento_id, opcion, costo, creado_en) "
                        "VALUES (?, ?, ?, ?, datetime('now', 'localtime'))",
                        (usuario["id"], evento_id, opcion, ev["costo"]),
                    ).lastrowid
                except sqlite3.IntegrityError:
                    raise ErrorNegocio("Ya hiciste tu pronóstico para este evento.") from None
                registrar_movimiento(
                    db, usuario["id"], "participacion", -ev["costo"],
                    f"Pronóstico {ev['local']} vs {ev['visitante']}", f"pron:{pronostico_id}",
                )
        except ErrorNegocio as error:
            flash(str(error), "error")
        except SaldoInsuficiente:
            flash("No tienes créditos suficientes para este pronóstico.", "error")
        else:
            flash("¡Pronóstico registrado!", "ok")
            return redirect("/mis-pronosticos")

    ya = db.execute(
        "SELECT 1 FROM pronosticos WHERE usuario_id = ? AND evento_id = ?", (usuario["id"], evento_id)
    ).fetchone()
    return render_template(
        "participar/pronosticar.html", ev=dict(ev), opciones=OPCIONES[ev["tipo"]], ya=bool(ya)
    )
