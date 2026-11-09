"""Sesión y permisos (HU04: cada usuario solo ve lo suyo; solo el administrador administra)."""
from functools import wraps

from flask import abort, flash, g, redirect, session

from .db import get_db


def usuario_actual():
    if "usuario" not in g:
        uid = session.get("usuario_id")
        g.usuario = (
            get_db().execute("SELECT * FROM usuarios WHERE id = ?", (uid,)).fetchone() if uid else None
        )
    return g.usuario


def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if usuario_actual() is None:
            flash("Inicia sesión para continuar.", "error")
            return redirect("/login")
        return vista(*args, **kwargs)

    return envoltura


def admin_requerido(vista):
    @wraps(vista)
    @login_requerido
    def envoltura(*args, **kwargs):
        if usuario_actual()["rol"] != "admin":
            abort(403)
        return vista(*args, **kwargs)

    return envoltura
