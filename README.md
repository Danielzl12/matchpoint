# MatchPoint

Plataforma web de torneos y pronósticos deportivos con créditos virtuales (sin dinero real). Caso Nexo Digital Labs · Equipo 3 · Sprint 2.

## Enlaces

| Recurso | URL |
|---|---|
| Aplicación en línea | https://matchpoint-red.vercel.app |
| Código fuente | https://github.com/Danielzl12/matchpoint |
| Tablero de Trello (sprint y retrospectiva Starfish) | https://trello.com/b/LtNyZnp8/matchpoint |
| Wiki (backlog, sprints y canvas de equipo) | https://github.com/Danielzl12/matchpoint/wiki |
| Video de la retrospectiva | https://github.com/Danielzl12/matchpoint/blob/main/docs/Retrospectiva-Sprint-2.mp4 |

## Equipo

| Integrante | Rol |
|---|---|
| Daniel Zuluaga | Product Owner |
| Karla Nicole Martín | Scrum Master |
| Dana Valentina Quevedo | Desarrollo |
| Juan Sebastián Barreto | Desarrollo |

## Qué permite hacer

- **Administrador:** crear torneos y equipos, programar eventos, registrar resultados, cancelar eventos, corregir resultados y saldos, y consultar reportes.
- **Participante:** registrarse, iniciar sesión, ver torneos y eventos, hacer un pronóstico con créditos, y consultar su saldo, su historial y sus pronósticos.
- **Premios:** al registrar el resultado, los créditos se pagan automáticamente a quienes acertaron.

## Acceso de demostración

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `admin123` | Administrador |
| `ana`, `luis`, `sofia` | `clave123` | Participante (100 créditos) |

También se puede crear una cuenta nueva desde «Registrarme».

## Historias de usuario del Sprint 2

| HU | Historia | Responsable |
|---|---|---|
| 01 | Crear torneo y equipos | Daniel Zuluaga |
| 02 | Programar evento | Daniel Zuluaga |
| 03 | Registrarse | Daniel Zuluaga |
| 04 | Iniciar sesión | Daniel Zuluaga |
| 05 | Ver torneos y eventos | Karla Nicole Martín |
| 06 | Hacer un pronóstico | Karla Nicole Martín |
| 07 | Asignar créditos | Karla Nicole Martín |
| 08 | Consultar saldo e historial | Juan Sebastián Barreto |
| 09 | Ver mis pronósticos | Juan Sebastián Barreto |
| 10 | Registrar resultado | Juan Sebastián Barreto |
| 11 | Pagar premios | Juan Sebastián Barreto |
| 12 | Cancelar evento y devolver créditos | Dana Valentina Quevedo |
| 13 | Corregir resultado | Dana Valentina Quevedo |
| 14 | Corregir saldo con motivo | Dana Valentina Quevedo |
| 15 | Reportes | Dana Valentina Quevedo |

## Reglas de negocio asumidas

- Cada evento cuesta 10 créditos y paga 20 por defecto; el administrador puede cambiarlos al programarlo.
- Un torneo necesita mínimo 2 equipos distintos.
- Cada usuario hace un solo pronóstico por evento.
- Un evento solo se puede cancelar mientras no tenga resultado.
- El saldo nunca queda negativo y los movimientos de créditos no se pueden editar ni borrar: las correcciones se registran como movimientos nuevos.

## Tecnología

Python y Flask, base de datos Postgres (Supabase) y despliegue en Vercel.
