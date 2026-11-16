"""HU08 Consultar mi saldo e historial · HU09 Ver mis pronósticos. Responsable: Juan Sebastián Barreto."""
from flask import Blueprint, render_template

from .db import get_db
from .ledger import suma_movimientos
from .seguridad import login_requerido, usuario_actual

bp = Blueprint("consultas", __name__)


@bp.route("/mi-saldo")
@login_requerido
def saldo():
    db = get_db()
    uid = usuario_actual()["id"]  # siempre el usuario de la sesión: nadie ve datos ajenos
    movimientos = db.execute(
        "SELECT * FROM movimientos WHERE usuario_id = ? ORDER BY id DESC", (uid,)
    ).fetchall()
    return render_template("consultas/saldo.html", movimientos=movimientos, total=suma_movimientos(db, uid))


@bp.route("/mis-pronosticos")
@login_requerido
def pronosticos():
    filas = get_db().execute(
        "SELECT p.id, p.opcion, p.costo, p.estado, p.creado_en, e.premio, e.resultado, e.tipo, "
        "t.nombre AS torneo, l.nombre AS local, v.nombre AS visitante "
        "FROM pronosticos p "
        "JOIN eventos e ON e.id = p.evento_id "
        "JOIN torneos t ON t.id = e.torneo_id "
        "JOIN equipos l ON l.id = e.local_id "
        "JOIN equipos v ON v.id = e.visitante_id "
        "WHERE p.usuario_id = ? ORDER BY p.id DESC",
        (usuario_actual()["id"],),
    ).fetchall()
    return render_template("consultas/pronosticos.html", pronosticos=filas)
