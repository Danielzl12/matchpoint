"""HU01 Crear torneo y equipos · HU02 Programar evento. Responsable: Daniel Zuluaga."""
import sqlite3

from flask import Blueprint, flash, redirect, render_template, request

from .db import get_db, transaccion
from .reglas import OPCIONES, SELECT_EVENTO, NOMBRE_TIPO, entero, normalizar_fecha
from .seguridad import admin_requerido

bp = Blueprint("torneos", __name__)


@bp.route("/admin/torneos", methods=["GET", "POST"])
@admin_requerido
def admin_torneos():
    db = get_db()
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        tipo = request.form.get("tipo_defecto", "1X2")
        if tipo not in OPCIONES:
            tipo = "1X2"
        vistos, equipos, repetidos = set(), [], []
        for crudo in request.form.getlist("equipo"):
            equipo = crudo.strip()
            if not equipo:
                continue
            if equipo.lower() in vistos:
                repetidos.append(equipo)
                continue
            vistos.add(equipo.lower())
            equipos.append(equipo)

        if not nombre:
            flash("Escribe el nombre del torneo.", "error")
        elif len(equipos) < 2:
            flash("Agrega al menos 2 equipos distintos.", "error")
        else:
            try:
                with transaccion(db):
                    torneo_id = db.execute(
                        "INSERT INTO torneos (nombre, tipo_defecto) VALUES (?, ?)", (nombre, tipo)
                    ).lastrowid
                    for equipo in equipos:
                        db.execute(
                            "INSERT INTO equipos (torneo_id, nombre) VALUES (?, ?)", (torneo_id, equipo)
                        )
            except sqlite3.IntegrityError:
                flash("Ya existe un torneo con ese nombre.", "error")
            else:
                if repetidos:
                    flash("No se agregaron equipos repetidos: " + ", ".join(repetidos) + ".", "error")
                flash(f"Torneo «{nombre}» creado con {len(equipos)} equipos.", "ok")
                return redirect("/admin/torneos")

    torneos = db.execute(
        "SELECT t.*, (SELECT GROUP_CONCAT(nombre, ', ') FROM equipos WHERE torneo_id = t.id) AS equipos "
        "FROM torneos t ORDER BY t.id DESC"
    ).fetchall()
    return render_template("torneos/admin_torneos.html", torneos=torneos, tipos=NOMBRE_TIPO)


@bp.route("/admin/eventos", methods=["GET", "POST"])
@admin_requerido
def admin_eventos():
    db = get_db()
    if request.method == "POST":
        mensaje, datos = _validar_evento(db, request.form)
        if mensaje:
            flash(mensaje, "error")
        else:
            db.execute(
                "INSERT INTO eventos (torneo_id, local_id, visitante_id, inicio, cierre, tipo, costo, premio) "
                "VALUES (:torneo_id, :local_id, :visitante_id, :inicio, :cierre, :tipo, :costo, :premio)",
                datos,
            )
            flash("Evento programado.", "ok")
            return redirect("/admin/eventos")

    torneos = db.execute("SELECT * FROM torneos ORDER BY nombre").fetchall()
    equipos = db.execute("SELECT * FROM equipos ORDER BY nombre").fetchall()
    eventos = [dict(e) for e in db.execute(SELECT_EVENTO + " ORDER BY e.id DESC").fetchall()]
    return render_template(
        "torneos/admin_eventos.html", torneos=torneos, equipos=equipos, eventos=eventos, tipos=NOMBRE_TIPO
    )


def _validar_evento(db, form):
    """Devuelve (mensaje_de_error, None) o (None, datos_limpios)."""
    torneo_id = entero(form.get("torneo_id"))
    local_id = entero(form.get("local_id"))
    visitante_id = entero(form.get("visitante_id"))
    tipo = form.get("tipo", "")
    inicio = normalizar_fecha(form.get("inicio"))
    cierre = normalizar_fecha(form.get("cierre"))
    costo = entero(form.get("costo") or 10)
    premio = entero(form.get("premio") or 20)

    if torneo_id is None or not db.execute("SELECT 1 FROM torneos WHERE id = ?", (torneo_id,)).fetchone():
        return ("Elige un torneo que exista.", None)
    if local_id is None or visitante_id is None:
        return ("Elige los dos equipos.", None)
    if local_id == visitante_id:
        return ("El equipo local y el visitante deben ser distintos.", None)
    for equipo_id in (local_id, visitante_id):
        if not db.execute(
            "SELECT 1 FROM equipos WHERE id = ? AND torneo_id = ?", (equipo_id, torneo_id)
        ).fetchone():
            return ("Los equipos deben pertenecer al torneo elegido.", None)
    if tipo not in OPCIONES:
        return ("Elige el tipo de pronóstico.", None)
    if not inicio or not cierre:
        return ("Indica la fecha de inicio y la hora de cierre.", None)
    if cierre >= inicio:
        return ("La hora de cierre debe ser anterior al inicio del evento.", None)
    if costo is None or costo <= 0 or premio is None or premio <= 0:
        return ("El costo y el premio deben ser números mayores que 0.", None)
    return (
        None,
        dict(torneo_id=torneo_id, local_id=local_id, visitante_id=visitante_id, inicio=inicio,
             cierre=cierre, tipo=tipo, costo=costo, premio=premio),
    )
