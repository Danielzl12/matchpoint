"""MatchPoint: plataforma de torneos, pronósticos y créditos virtuales (Flask + SQLite)."""
import os
from importlib import import_module

from flask import Flask, redirect, render_template

from . import db as basedatos
from .reglas import describir_opcion, estado_evento
from .seguridad import usuario_actual

# Cada integrante agrega su archivo. Si todavía no existe, la app arranca igual.
MODULOS = [
    "auth",          # Daniel: HU03, HU04
    "torneos",       # Daniel: HU01, HU02
    "participar",    # Karla:  HU05, HU06
    "creditos",      # Karla:  HU07
    "consultas",     # Juan:   HU08, HU09
    "resultados",    # Juan:   HU10, HU11
    "correcciones",  # Dana:   HU12, HU13, HU14
    "reportes",      # Dana:   HU15
]


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(
        SECRET_KEY=os.environ.get("MATCHPOINT_SECRET", "cambiar-en-produccion"),
        DATABASE=os.environ.get("MATCHPOINT_DB", os.path.join(app.instance_path, "matchpoint.db")),
    )
    if config:
        app.config.update(config)

    basedatos.init_db(app.config["DATABASE"])
    app.teardown_appcontext(basedatos.cerrar_db)

    app.jinja_env.filters["estado"] = estado_evento
    app.jinja_env.filters["describir"] = describir_opcion
    app.jinja_env.filters["fecha"] = lambda texto: (texto or "")[:16]
    app.context_processor(lambda: {"usuario": usuario_actual()})

    for nombre in MODULOS:
        try:
            modulo = import_module(f"{__name__}.{nombre}")
        except ModuleNotFoundError as error:
            if error.name != f"{__name__}.{nombre}":
                raise
            continue
        app.register_blueprint(modulo.bp)

    @app.route("/")
    def inicio():
        return redirect("/torneos" if usuario_actual() else "/login")

    @app.errorhandler(403)
    def sin_permiso(_):
        return render_template("error.html", mensaje="No tienes permiso para hacer esto."), 403

    @app.errorhandler(404)
    def no_existe(_):
        return render_template("error.html", mensaje="No encontramos esa página."), 404

    return app
