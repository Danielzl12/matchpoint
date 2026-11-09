"""HU03 Registrarse · HU04 Iniciar sesión. Responsable: Daniel Zuluaga."""
import sqlite3

from flask import Blueprint, flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db

bp = Blueprint("auth", __name__)


@bp.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        ident = request.form.get("identificador", "").strip()
        nombre = request.form.get("nombre", "").strip()
        clave = request.form.get("clave", "")
        if not ident or not nombre:
            flash("Completa tu nombre y un identificador.", "error")
        elif len(clave) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "error")
        else:
            try:
                get_db().execute(
                    "INSERT INTO usuarios (identificador, nombre, clave_hash) VALUES (?, ?, ?)",
                    (ident, nombre, generate_password_hash(clave)),
                )
            except sqlite3.IntegrityError:
                flash("Ese identificador ya existe. Elige otro.", "error")
            else:
                flash("Cuenta creada. Ya puedes iniciar sesión.", "ok")
                return redirect("/login")
    return render_template("auth/registro.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ident = request.form.get("identificador", "").strip()
        clave = request.form.get("clave", "")
        fila = get_db().execute("SELECT * FROM usuarios WHERE identificador = ?", (ident,)).fetchone()
        if fila and check_password_hash(fila["clave_hash"], clave):
            session.clear()
            session["usuario_id"] = fila["id"]
            return redirect("/torneos")
        # Mismo mensaje para usuario inexistente y clave mala: no revela qué identificadores existen.
        flash("Identificador o contraseña incorrectos.", "error")
    return render_template("auth/login.html")


@bp.route("/salir")
def salir():
    session.clear()
    return redirect("/login")
