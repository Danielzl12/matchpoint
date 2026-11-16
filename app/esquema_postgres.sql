-- Esquema de MatchPoint para Postgres (Supabase). Es idempotente: se puede correr más de una vez.
-- La app lo aplica sola si no existen las tablas; también puedes pegarlo en el SQL Editor de Supabase.
CREATE EXTENSION IF NOT EXISTS citext WITH SCHEMA public;

CREATE TABLE IF NOT EXISTS usuarios (
    id             INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    identificador  public.citext NOT NULL UNIQUE,
    nombre         TEXT NOT NULL,
    clave_hash     TEXT NOT NULL,
    rol            TEXT NOT NULL DEFAULT 'usuario' CHECK (rol IN ('usuario', 'admin')),
    saldo          INTEGER NOT NULL DEFAULT 0 CHECK (saldo >= 0)
);

CREATE TABLE IF NOT EXISTS torneos (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre        public.citext NOT NULL UNIQUE,
    tipo_defecto  TEXT NOT NULL DEFAULT '1X2' CHECK (tipo_defecto IN ('1X2', 'ganador'))
);

CREATE TABLE IF NOT EXISTS equipos (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    torneo_id  INTEGER NOT NULL REFERENCES torneos(id),
    nombre     public.citext NOT NULL,
    UNIQUE (torneo_id, nombre)
);

CREATE TABLE IF NOT EXISTS eventos (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    torneo_id           INTEGER NOT NULL REFERENCES torneos(id),
    local_id            INTEGER NOT NULL REFERENCES equipos(id),
    visitante_id        INTEGER NOT NULL REFERENCES equipos(id),
    inicio              TEXT NOT NULL,
    cierre              TEXT NOT NULL,
    tipo                TEXT NOT NULL CHECK (tipo IN ('1X2', 'ganador')),
    costo               INTEGER NOT NULL DEFAULT 10 CHECK (costo > 0),
    premio              INTEGER NOT NULL DEFAULT 20 CHECK (premio > 0),
    estado              TEXT NOT NULL DEFAULT 'programado'
                        CHECK (estado IN ('programado', 'finalizado', 'cancelado')),
    resultado           TEXT CHECK (resultado IN ('local', 'empate', 'visitante')),
    version             INTEGER NOT NULL DEFAULT 1,
    premios_repartidos  INTEGER NOT NULL DEFAULT 0,
    CHECK (cierre < inicio),
    CHECK (local_id <> visitante_id)
);

CREATE TABLE IF NOT EXISTS pronosticos (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id),
    evento_id   INTEGER NOT NULL REFERENCES eventos(id),
    opcion      TEXT NOT NULL CHECK (opcion IN ('local', 'empate', 'visitante')),
    costo       INTEGER NOT NULL,
    estado      TEXT NOT NULL DEFAULT 'pendiente'
                CHECK (estado IN ('pendiente', 'acertado', 'fallado', 'anulado')),
    creado_en   TEXT NOT NULL,
    UNIQUE (usuario_id, evento_id)
);

-- Libro mayor: solo se agregan filas. Las correcciones son movimientos nuevos.
CREATE TABLE IF NOT EXISTS movimientos (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id),
    tipo        TEXT NOT NULL
                CHECK (tipo IN ('asignacion', 'participacion', 'premio', 'devolucion', 'ajuste', 'reversion')),
    monto       INTEGER NOT NULL CHECK (monto <> 0),
    detalle     TEXT NOT NULL DEFAULT '',
    referencia  TEXT NOT NULL UNIQUE,
    creado_en   TEXT NOT NULL
);

CREATE OR REPLACE FUNCTION movimientos_inmutable() RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    RAISE EXCEPTION 'El libro de movimientos no se puede modificar ni borrar';
END;
$$;

DROP TRIGGER IF EXISTS movimientos_no_cambios ON movimientos;
CREATE TRIGGER movimientos_no_cambios BEFORE UPDATE OR DELETE ON movimientos
    FOR EACH ROW EXECUTE FUNCTION movimientos_inmutable();

CREATE TABLE IF NOT EXISTS resultados_historial (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    evento_id           INTEGER NOT NULL REFERENCES eventos(id),
    resultado_anterior  TEXT NOT NULL,
    resultado_nuevo     TEXT NOT NULL,
    admin_id            INTEGER NOT NULL REFERENCES usuarios(id),
    creado_en           TEXT NOT NULL
);

-- Seguridad: Supabase expone las tablas de "public" por su API REST con la llave pública.
-- Con RLS activo y sin políticas, esa API no puede leer ni escribir nada. La app entra
-- por conexión directa (usuario postgres), que no se ve afectado.
ALTER TABLE usuarios             ENABLE ROW LEVEL SECURITY;
ALTER TABLE torneos              ENABLE ROW LEVEL SECURITY;
ALTER TABLE equipos              ENABLE ROW LEVEL SECURITY;
ALTER TABLE eventos              ENABLE ROW LEVEL SECURITY;
ALTER TABLE pronosticos          ENABLE ROW LEVEL SECURITY;
ALTER TABLE movimientos          ENABLE ROW LEVEL SECURITY;
ALTER TABLE resultados_historial ENABLE ROW LEVEL SECURITY;
