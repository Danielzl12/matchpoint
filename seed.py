"""Datos de demostración para probar y grabar el review:  python seed.py"""
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from app import create_app
from app.db import conectar, transaccion
from app.ledger import registrar_movimiento


def hora(delta):
    return (datetime.now() + delta).strftime("%Y-%m-%d %H:%M:%S")


def main():
    app = create_app()
    db = conectar(app.config["DATABASE"])
    if db.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]:
        print("La base ya tiene datos. Borra instance/matchpoint.db para empezar de cero.")
        return

    with transaccion(db):
        db.execute(
            "INSERT INTO usuarios (identificador, nombre, clave_hash, rol) VALUES (?, ?, ?, 'admin')",
            ("admin", "Administrador", generate_password_hash("admin123")),
        )
        ids = {}
        for ident, nombre in [("ana", "Ana Pérez"), ("luis", "Luis Gómez"), ("sofia", "Sofía Ruiz")]:
            cur = db.execute(
                "INSERT INTO usuarios (identificador, nombre, clave_hash) VALUES (?, ?, ?)",
                (ident, nombre, generate_password_hash("clave123")),
            )
            ids[ident] = cur.lastrowid
            registrar_movimiento(db, cur.lastrowid, "asignacion", 100, "Créditos iniciales", f"seed:{ident}")

        torneo = db.execute(
            "INSERT INTO torneos (nombre, tipo_defecto) VALUES ('Liga Campus 2026', '1X2')"
        ).lastrowid
        eq = {}
        for nombre in ["Tigres", "Águilas", "Lobos", "Halcones"]:
            eq[nombre] = db.execute(
                "INSERT INTO equipos (torneo_id, nombre) VALUES (?, ?)", (torneo, nombre)
            ).lastrowid

        # Evento abierto: se puede pronosticar ahora.
        db.execute(
            "INSERT INTO eventos (torneo_id, local_id, visitante_id, inicio, cierre, tipo) VALUES (?,?,?,?,?,'1X2')",
            (torneo, eq["Tigres"], eq["Águilas"], hora(timedelta(days=2)), hora(timedelta(days=1))),
        )
        # Evento ya cerrado, con dos pronósticos: sirve para probar resultado y premios.
        cerrado = db.execute(
            "INSERT INTO eventos (torneo_id, local_id, visitante_id, inicio, cierre, tipo) VALUES (?,?,?,?,?,'1X2')",
            (torneo, eq["Lobos"], eq["Halcones"], hora(timedelta(hours=-1)), hora(timedelta(hours=-2))),
        ).lastrowid
        for ident, opcion in [("ana", "local"), ("luis", "visitante")]:
            p = db.execute(
                "INSERT INTO pronosticos (usuario_id, evento_id, opcion, costo, creado_en) VALUES (?,?,?,10,?)",
                (ids[ident], cerrado, opcion, hora(timedelta(hours=-3))),
            ).lastrowid
            registrar_movimiento(db, ids[ident], "participacion", -10, "Pronóstico Lobos vs Halcones", f"pron:{p}")

    print("Listo. Usuarios de prueba:")
    print("  admin / admin123   (administrador)")
    print("  ana, luis, sofia / clave123   (100 créditos cada uno)")


if __name__ == "__main__":
    main()
