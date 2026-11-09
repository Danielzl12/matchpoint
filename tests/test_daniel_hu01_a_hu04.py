"""Daniel: HU01 torneo · HU02 evento · HU03 registro · HU04 login."""
from .conftest import crear_torneo, crear_usuario, entrar, hora


def test_hu03_registro_y_luego_login(client):
    r = client.post("/registro", data={"nombre": "Ana", "identificador": "ana", "clave": "secreta1"}, follow_redirects=True)
    assert "Cuenta creada" in r.text
    assert "Torneos y eventos" in entrar(client, "ana", "secreta1").text


def test_hu03_identificador_repetido(client):
    datos = {"nombre": "Ana", "identificador": "ana", "clave": "secreta1"}
    client.post("/registro", data=datos)
    r = client.post("/registro", data={**datos, "identificador": "ANA"})
    assert "ya existe" in r.text


def test_hu04_credenciales_incorrectas(client, db):
    crear_usuario(db, "ana")
    assert "incorrectos" in entrar(client, "ana", "mala").text
    assert "incorrectos" in entrar(client, "nadie").text


def test_hu04_rutas_requieren_sesion(client):
    assert client.get("/mi-saldo").headers["Location"].endswith("/login")


def test_hu01_admin_crea_torneo_y_omite_repetidos(client, db, escenario):
    entrar(client, "admin")
    r = client.post(
        "/admin/torneos",
        data={"nombre": "Copa", "tipo_defecto": "1X2", "equipo": ["Rojos", "rojos", "Azules"]},
        follow_redirects=True,
    )
    assert "creado con 2 equipos" in r.text and "repetidos" in r.text
    assert db.execute("SELECT COUNT(*) FROM equipos WHERE torneo_id = (SELECT id FROM torneos WHERE nombre='Copa')").fetchone()[0] == 2


def test_hu01_usuario_normal_no_puede(client, escenario):
    entrar(client, "ana")
    assert client.get("/admin/torneos").status_code == 403
    assert client.post("/admin/torneos", data={"nombre": "X", "equipo": ["a", "b"]}).status_code == 403


def test_hu01_requiere_dos_equipos(client, escenario):
    entrar(client, "admin")
    r = client.post("/admin/torneos", data={"nombre": "Solo", "equipo": ["a", "A"]})
    assert "al menos 2 equipos" in r.text


def evento_form(escenario, **cambios):
    a, b, _ = escenario["equipos"]
    datos = {"torneo_id": escenario["torneo"], "local_id": a, "visitante_id": b, "tipo": "1X2",
             "inicio": hora(days=2).replace(" ", "T")[:16], "cierre": hora(days=1).replace(" ", "T")[:16]}
    datos.update(cambios)
    return datos


def test_hu02_programar_evento(client, db, escenario):
    entrar(client, "admin")
    r = client.post("/admin/eventos", data=evento_form(escenario), follow_redirects=True)
    assert "Evento programado" in r.text and "abierto" in r.text


def test_hu02_cierre_debe_ser_antes_del_inicio(client, escenario):
    entrar(client, "admin")
    f = evento_form(escenario)
    r = client.post("/admin/eventos", data={**f, "cierre": f["inicio"]})
    assert "anterior al inicio" in r.text


def test_hu02_torneo_inexistente_y_equipos_ajenos(client, db, escenario):
    entrar(client, "admin")
    assert "torneo que exista" in client.post("/admin/eventos", data=evento_form(escenario, torneo_id=999)).text
    _, otros = crear_torneo(db, "Otro", ("X", "Y"))
    assert "pertenecer" in client.post("/admin/eventos", data=evento_form(escenario, local_id=otros[0])).text


def test_hu02_ganador_directo_sin_empate(client, db, escenario):
    entrar(client, "admin")
    client.post("/admin/eventos", data=evento_form(escenario, tipo="ganador"))
    from app.reglas import OPCIONES
    assert "empate" not in OPCIONES["ganador"]
