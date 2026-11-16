# Despliegue: Vercel + Supabase

La app sigue siendo Flask. En local usa SQLite; en Vercel usa el Postgres de Supabase (Vercel no guarda archivos, un SQLite se borraría).

## Quién sube qué (un commit cada uno, tu nombre como único autor)

Orden: primero se unen los PR de Dana y Sebastián a `main`; luego estos commits, en una rama `despliegue`.

| Persona | Archivos | Mensaje del commit |
|---|---|---|
| Daniel (PO) | `app/db.py`, `app/esquema_postgres.sql`, `app/__init__.py`, `app/reglas.py`, `app/ledger.py`, `app/auth.py`, `app/torneos.py`, `seed.py`, `api/index.py`, `vercel.json`, `requirements.txt`, `requirements-dev.txt`, `.env.example`, `.gitignore`, `tests/conftest.py`, `docs/DESPLIEGUE.md` | `Despliegue: soporte Postgres (Supabase) y Vercel` |
| Karla | `app/participar.py`, `tests/test_karla_hu05_a_hu07.py` | `HU05-06: compatible con Postgres` |
| Dana | `app/reportes.py` | `HU15: reporte compatible con Postgres` |
| Sebastián | ningún archivo: sus módulos no cambian. Solo prueba su parte (lista abajo) | — |

## Pasos de Daniel (solo tú tocas Vercel y Supabase)

1. Supabase → tu proyecto → **Connect** → *Transaction pooler* (puerto 6543). Copia la cadena y pon tu clave.
2. Vercel → **Add New Project** → importa el repo `matchpoint` (raíz del repo, sin framework).
3. Vercel → *Settings → Environment Variables*:
   - `DATABASE_URL` = la cadena del paso 1
   - `MATCHPOINT_SECRET` = `python -c "import secrets; print(secrets.token_hex(32))"`
4. **Deploy**. Al primer ingreso la app crea sola las tablas (también puedes pegar `app/esquema_postgres.sql` en el SQL Editor de Supabase).
5. Datos de demo para el video (una sola vez, desde tu PC):
   `DATABASE_URL="<cadena>" MATCHPOINT_SECRET=x python seed.py`
   Crea `admin / admin123`. Cámbiale la clave o bórralo después del Review.
6. Pega la URL de Vercel en la wiki y en la entrega.

## Local (sin cambios)

`pip install -r requirements-dev.txt` · `python run.py` · `python -m pytest` (SQLite).
Contra Postgres: `TEST_DATABASE_URL=<url de una base de PRUEBA> python -m pytest` (vacía las tablas: nunca la de producción).

## Lista de verificación (a mano, en la URL de Vercel)

Crítico:
- [ ] `/login` carga y se ve el CSS.
- [ ] Registrar una cuenta nueva y entrar.
- [ ] Admin: crear torneo con 2+ equipos y programar un evento (hora de cierre en el futuro).
- [ ] Usuario con créditos: pronosticar → el saldo baja 10 y sale en el historial.
- [ ] Admin: registrar resultado cuando el evento cierre → el ganador sube 20.
- [ ] Admin: corregir resultado y corregir saldo con motivo.
- [ ] `/admin/reportes` muestra 0 diferencias de saldo.

Por persona: Daniel HU01–04 · Karla HU05–07 · Sebastián HU08–11 · Dana HU12–15 (cada uno recorre sus pantallas).

## Hecho y comprobado / No comprobado

Comprobado: 35 pruebas pasan en SQLite y en Postgres 16 local; el punto de entrada `api/index.py` responde (login, CSS); el libro de movimientos rechaza UPDATE/DELETE en Postgres.
No comprobado: el despliegue real en Vercel, la conexión al pooler de Supabase, el rendimiento con varios usuarios a la vez, la zona horaria vista desde un navegador real.
Supuestos: horas del evento en `America/Bogota` (se cambia con `MATCHPOINT_TZ`).
