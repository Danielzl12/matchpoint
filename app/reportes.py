"""HU15 Reportes: torneos, participación y saldos (con diferencias). Responsable: Dana Valentina Quevedo."""
from flask import Blueprint, render_template

from .db import get_db
from .seguridad import admin_requerido

bp = Blueprint("reportes", __name__)


@bp.route("/admin/reportes")
@admin_requerido
def reportes():
    db = get_db()
    torneos = db.execute(
        "SELECT t.nombre, COUNT(DISTINCT e.id) AS eventos, "
        "COUNT(DISTINCT CASE WHEN e.estado = 'finalizado' THEN e.id END) AS finalizados, "
        "COUNT(p.id) AS pronosticos "
        "FROM torneos t LEFT JOIN eventos e ON e.torneo_id = t.id "
        "LEFT JOIN pronosticos p ON p.evento_id = e.id AND p.estado <> 'anulado' "
        "GROUP BY t.id ORDER BY t.nombre"
    ).fetchall()
    participacion = db.execute(
        "SELECT u.nombre, u.identificador, "
        "COUNT(p.id) AS pronosticos, "
        "COALESCE(SUM(p.estado = 'acertado'), 0) AS aciertos, "
        "COALESCE(SUM(p.estado = 'fallado'), 0) AS fallos "
        "FROM usuarios u LEFT JOIN pronosticos p ON p.usuario_id = u.id AND p.estado <> 'anulado' "
        "WHERE u.rol = 'usuario' GROUP BY u.id ORDER BY pronosticos DESC, u.nombre"
    ).fetchall()
    # Saldo guardado vs suma real del historial: si no coinciden, algo se tocó fuera del libro.
    saldos = db.execute(
        "SELECT u.nombre, u.identificador, u.saldo, COALESCE(SUM(m.monto), 0) AS historial, "
        "u.saldo - COALESCE(SUM(m.monto), 0) AS diferencia "
        "FROM usuarios u LEFT JOIN movimientos m ON m.usuario_id = u.id "
        "WHERE u.rol = 'usuario' GROUP BY u.id ORDER BY u.nombre"
    ).fetchall()
    return render_template(
        "reportes/reportes.html",
        torneos=torneos,
        participacion=participacion,
        saldos=saldos,
        con_diferencia=sum(1 for s in saldos if s["diferencia"] != 0),
    )
