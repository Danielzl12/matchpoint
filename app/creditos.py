"""HU07 Asignar créditos a un usuario. Responsable: Karla Nicole Martín."""
import re
from uuid import uuid4

from flask import Blueprint, flash, redirect, render_template, request

from .db import get_db, transaccion
from .ledger import registrar_movimiento
from .reglas import entero
from .seguridad import admin_requerido

bp = Blueprint("creditos", __name__)

MAXIMO = 100000


@bp.route("/admin/creditos", methods=["GET", "POST"])
@admin_requerido
def asignar():
    db = get_db()
    if request.method == "POST":
        usuario_id = entero(request.form.get("usuario_id"))
        monto = entero(request.form.get("monto"))
        destino = db.execute(
            "SELECT * FROM usuarios WHERE id = ? AND rol = 'usuario'", (usuario_id,)
        ).fetchone()
        if destino is None:
            flash("Elige un usuario de la lista.", "error")
        elif monto is None or not 0 < monto <= MAXIMO:
            flash(f"El monto debe ser un número entre 1 y {MAXIMO}.", "error")
        elif request.form.get("accion") == "confirmar":
            referencia = request.form.get("referencia", "")
            if not re.fullmatch(r"asig:[0-9a-f]{32}", referencia):
                flash("La confirmación no es válida. Vuelve a intentarlo.", "error")
            else:
                with transaccion(db):
                    nuevo = registrar_movimiento(
                        db, destino["id"], "asignacion", monto, "Asignación del administrador", referencia
                    )
                if nuevo:
                    flash(f"Se asignaron {monto} créditos a {destino['nombre']}.", "ok")
                else:
                    flash("Esa asignación ya se había aplicado; no se repitió.", "error")
                return redirect("/admin/creditos")
        else:
            # Paso intermedio: el administrador confirma antes de aplicar.
            return render_template(
                "creditos/confirmar.html", destino=destino, monto=monto, referencia=f"asig:{uuid4().hex}"
            )

    usuarios = db.execute("SELECT * FROM usuarios WHERE rol = 'usuario' ORDER BY nombre").fetchall()
    return render_template("creditos/asignar.html", usuarios=usuarios)
