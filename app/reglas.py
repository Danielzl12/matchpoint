"""Reglas y utilidades compartidas (fechas, estados de evento, consultas comunes)."""
from datetime import datetime

# Opciones de pronóstico según el tipo de evento (HU02).
OPCIONES = {"1X2": ["local", "empate", "visitante"], "ganador": ["local", "visitante"]}
NOMBRE_TIPO = {"1X2": "Local / Empate / Visitante", "ganador": "Ganador directo"}

SELECT_EVENTO = """
SELECT e.*, t.nombre AS torneo, l.nombre AS local, v.nombre AS visitante
FROM eventos e
JOIN torneos t ON t.id = e.torneo_id
JOIN equipos l ON l.id = e.local_id
JOIN equipos v ON v.id = e.visitante_id
"""


class ErrorNegocio(Exception):
    """Regla de negocio no cumplida. El mensaje se le muestra tal cual al usuario."""


def ahora_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalizar_fecha(texto):
    """'2026-11-20T18:00' -> '2026-11-20 18:00:00'. Devuelve None si no es una fecha válida."""
    try:
        return datetime.fromisoformat((texto or "").strip()).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def entero(texto):
    try:
        return int(str(texto).strip())
    except (TypeError, ValueError):
        return None


def cargar_evento(db, evento_id):
    return db.execute(SELECT_EVENTO + " WHERE e.id = ?", (evento_id,)).fetchone()


def estado_evento(ev):
    """abierto | cerrado | finalizado | cancelado."""
    if ev["estado"] in ("cancelado", "finalizado"):
        return ev["estado"]
    return "abierto" if ahora_str() < ev["cierre"] else "cerrado"


def describir_opcion(opcion, local, visitante):
    return {"local": f"Gana {local}", "empate": "Empate", "visitante": f"Gana {visitante}"}[opcion]
