# MatchPoint

Plataforma de torneos, pronósticos y créditos virtuales (sin dinero real). Proyecto del caso Nexo Digital Labs — Equipo 3, Sprint 2.

**Equipo:** Daniel Zuluaga (PO) · Karla Nicole Martín (SM) · Dana Valentina Quevedo y Juan Sebastián Barreto (desarrollo).

## Cómo correrlo

```bash
python -m venv .venv
source .venv/bin/activate          # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
python seed.py                     # datos de prueba (opcional)
python run.py                      # abre http://127.0.0.1:5000
python -m pytest                   # pruebas automáticas
```

Usuarios de prueba (si corriste `seed.py`): `admin / admin123` (administrador) y `ana`, `luis`, `sofia` / `clave123`.

## Historias de usuario y responsables (Sprint 2)

| HU | Qué hace | Archivo | Responsable |
|---|---|---|---|
| 01 | Crear torneo y equipos | `app/torneos.py` | Daniel Zuluaga |
| 02 | Programar evento | `app/torneos.py` | Daniel Zuluaga |
| 03 | Registrarse | `app/auth.py` | Daniel Zuluaga |
| 04 | Iniciar sesión | `app/auth.py` | Daniel Zuluaga |
| 05 | Ver torneos y eventos | `app/participar.py` | Karla Nicole Martín |
| 06 | Hacer un pronóstico | `app/participar.py` | Karla Nicole Martín |
| 07 | Asignar créditos | `app/creditos.py` | Karla Nicole Martín |
| 08 | Consultar saldo e historial | `app/consultas.py` | Juan Sebastián Barreto |
| 09 | Ver mis pronósticos | `app/consultas.py` | Juan Sebastián Barreto |
| 10 | Registrar resultado | `app/resultados.py` | Juan Sebastián Barreto |
| 11 | Pagar premios | `app/resultados.py` + `app/ledger.py` | Juan Sebastián Barreto |
| 12 | Cancelar evento y devolver créditos | `app/correcciones.py` | Dana Quevedo |
| 13 | Corregir resultado | `app/correcciones.py` | Dana Quevedo |
| 14 | Corregir saldo con motivo | `app/correcciones.py` | Dana Quevedo |
| 15 | Reportes | `app/reportes.py` | Dana Quevedo |

## Cómo está hecho

- **Python + Flask + SQLite.** No necesita instalar ninguna base de datos.
- **Libro de movimientos que solo crece** (`movimientos`): nada se edita ni se borra (lo bloquean triggers de la base). Las correcciones son movimientos nuevos.
- **Cada movimiento tiene una `referencia` única:** si un botón se pulsa dos veces, el segundo intento no cobra ni paga otra vez.
- **Saldo nunca negativo** (restricción en la base) y operaciones en transacción: o se hace todo o no se hace nada.
- **Un módulo por persona** para que Git no genere conflictos al unir el trabajo.

## Reglas que asumimos (no estaban definidas en las historias)

- Cada evento tiene costo (10 por defecto) y premio (20 por defecto) en créditos; el administrador puede cambiarlos al programarlo.
- Un torneo necesita mínimo 2 equipos distintos.
- Cada usuario hace un solo pronóstico por evento.
- Un evento se puede cancelar mientras no tenga resultado.
- Si al corregir un resultado un ganador anterior ya gastó el premio, la corrección se rechaza con un mensaje claro.

## Documentación

- `docs/REPARTO.md` — quién sube qué y en qué orden.
- `docs/RETROSPECTIVA.md` — técnica de retrospectiva (Starfish), guion de la sesión y resultados.
