# Quién sube qué (Sprint 2)

Repositorio: https://github.com/Danielzl12/matchpoint (hoy está vacío: solo tiene la wiki).

**Regla de oro:** cada persona sube **solo sus archivos**. Nadie edita `app/__init__.py` ni los archivos de otra persona, así Git no da conflictos.

## Orden

1. **Daniel** sube la base (Commit 0) → todos hacen `git pull`.
2. **Daniel** sube su parte (HU 01–04).
3. **Karla, Juan y Dana** suben la suya (en cualquier orden entre ellos).

> Las pruebas de Karla, Juan y Dana inician sesión con el módulo de Daniel, y las de Dana reutilizan una función del archivo de Juan. Para que `pytest` pase completo, conviene que los cuatro estén subidos.

## Commit 0 — Base compartida · Daniel

Sube todo lo que **no** está en las listas de abajo:

```
README.md   requirements.txt   .gitignore   run.py   seed.py
docs/REPARTO.md   docs/RETROSPECTIVA.md
app/__init__.py   app/db.py   app/ledger.py   app/reglas.py   app/seguridad.py
app/static/style.css   app/templates/base.html   app/templates/error.html
tests/__init__.py   tests/conftest.py
```

```bash
git clone https://github.com/Danielzl12/matchpoint.git && cd matchpoint
# copiar aquí los archivos del Commit 0
git add .
git commit -m "Base del proyecto: Flask, SQLite, libro de movimientos y documentación"
git push origin main
```

## Daniel Zuluaga — HU 01, 02, 03, 04

| Archivo |
|---|
| `app/auth.py` |
| `app/torneos.py` |
| `app/templates/auth/` (login.html, registro.html) |
| `app/templates/torneos/` (admin_torneos.html, admin_eventos.html) |
| `tests/test_daniel_hu01_a_hu04.py` |

```bash
git checkout -b hu01-04-daniel
git add app/auth.py app/torneos.py app/templates/auth app/templates/torneos tests/test_daniel_hu01_a_hu04.py
git commit -m "HU01-04: torneos, eventos, registro e inicio de sesión"
git push -u origin hu01-04-daniel      # luego Pull Request hacia main
```

## Karla Nicole Martín — HU 05, 06, 07

| Archivo |
|---|
| `app/participar.py` |
| `app/creditos.py` |
| `app/templates/participar/` (lista.html, pronosticar.html) |
| `app/templates/creditos/` (asignar.html, confirmar.html) |
| `tests/test_karla_hu05_a_hu07.py` |

```bash
git pull origin main
git checkout -b hu05-07-karla
git add app/participar.py app/creditos.py app/templates/participar app/templates/creditos tests/test_karla_hu05_a_hu07.py
git commit -m "HU05-07: ver eventos, hacer pronósticos y asignar créditos"
git push -u origin hu05-07-karla
```

## Juan Sebastián Barreto — HU 08, 09, 10, 11

| Archivo |
|---|
| `app/consultas.py` |
| `app/resultados.py` |
| `app/templates/consultas/` (saldo.html, pronosticos.html) |
| `app/templates/resultados/` (registrar.html) |
| `tests/test_juan_hu08_a_hu11.py` |

```bash
git pull origin main
git checkout -b hu08-11-juan
git add app/consultas.py app/resultados.py app/templates/consultas app/templates/resultados tests/test_juan_hu08_a_hu11.py
git commit -m "HU08-11: saldo, mis pronósticos, resultados y pago de premios"
git push -u origin hu08-11-juan
```

## Dana Quevedo — HU 12, 13, 14, 15

| Archivo |
|---|
| `app/correcciones.py` |
| `app/reportes.py` |
| `app/templates/correcciones/` (cancelar.html, resultado.html, ajuste.html) |
| `app/templates/reportes/` (reportes.html) |
| `tests/test_dana_hu12_a_hu15.py` |

```bash
git pull origin main
git checkout -b hu12-15-dana
git add app/correcciones.py app/reportes.py app/templates/correcciones app/templates/reportes tests/test_dana_hu12_a_hu15.py
git commit -m "HU12-15: cancelar eventos, corregir resultados y saldos, reportes"
git push -u origin hu12-15-dana
```

## Al final (todos)

- [ ] Los 4 Pull Requests unidos a `main`.
- [ ] `python -m pytest` pasa en `main`.
- [ ] Enlace del tablero de Trello pegado en `docs/RETROSPECTIVA.md`.
- [ ] La URL del repositorio es la que se publica en la entrega (punto 1). Si piden el enlace de la retro como URL aparte (punto 3), usar el del tablero de Trello.
