import sqlite3
from pathlib import Path

DB_PATH = str(Path(__file__).with_name("lavanderia.db"))

def _conn():
    return sqlite3.connect(DB_PATH)

def crear_bd():
    """Crea la BD original (boletas) y además el nuevo esquema (boleta + boleta_items)."""
    with _conn() as conn:
        cur = conn.cursor()

        # ===== Esquema ORIGINAL (lo mantenemos para compatibilidad) =====
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS boletas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente TEXT NOT NULL,
                tipo_item TEXT NOT NULL,
                kilos REAL DEFAULT 0,
                cantidad INTEGER DEFAULT 0,
                servicio TEXT DEFAULT 'normal',
                perfumado INTEGER DEFAULT 0,
                precio REAL NOT NULL,
                fecha TEXT NOT NULL,
                metodo_pago TEXT DEFAULT 'efectivo',
                estado TEXT DEFAULT 'registrado'
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_boletas_fecha ON boletas(fecha)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_boletas_cliente ON boletas(cliente)")

        # ===== NUEVO ESQUEMA (Cabecera + Items) =====
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS boleta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT,                  -- opcional: correlativo impreso (N° 007601)
                cliente TEXT NOT NULL,
                direccion TEXT,
                telefono TEXT,
                fecha TEXT NOT NULL,          -- fecha de emisión
                entrega_fecha TEXT,           -- fecha prometida
                entrega_hora TEXT,            -- hora prometida (ej. '17:00')
                metodo_pago TEXT DEFAULT 'efectivo',
                estado TEXT DEFAULT 'registrado',
                a_cuenta REAL DEFAULT 0,      -- pago parcial
                saldo REAL DEFAULT 0,
                total REAL DEFAULT 0,         -- total de la boleta (suma items)
                notas TEXT                    -- observaciones (ej. 'Martes 5 pm')
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_boleta_fecha ON boleta(fecha)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_boleta_cliente ON boleta(cliente)")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS boleta_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                boleta_id INTEGER NOT NULL REFERENCES boleta(id) ON DELETE CASCADE,
                descripcion TEXT,             -- 'Frazadas', 'Edredón', 'Kilos', etc.
                tipo TEXT,                    -- kilos | edredon | terno | otro
                prendas INTEGER DEFAULT 0,    -- nº de prendas (para terno/edredón)
                kilos REAL DEFAULT 0,         -- para servicio por kilos
                lavado TEXT,                  -- 'Normal', 'Seco', 'A mano'...
                secado TEXT,                  -- 'Secadora', 'Tendedero'...
                p_unit REAL DEFAULT 0,        -- precio unitario (por kilo o por prenda)
                importe REAL DEFAULT 0,       -- subtotal del item
                perfumado INTEGER DEFAULT 0   -- si está perfumado (1) o no (0)
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bitems_boleta ON boleta_items(boleta_id)")
        conn.commit()

# ====== API ORIGINAL (se mantiene tal cual para tu app actual) ======
def insertar_boleta(cliente, tipo_item, cantidad, lavado, perfumado, precio, metodo_pago, estado, fecha):
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO boletas (cliente, tipo_item, cantidad, servicio, perfumado, precio, fecha, metodo_pago, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (cliente, tipo_item, cantidad, lavado, perfumado, precio, fecha, metodo_pago, estado),
        )
        conn.commit()

def obtener_boletas_paginado(limit=20, offset=0, cliente=None, fecha_desde=None, fecha_hasta=None):
    with _conn() as conn:
        cur = conn.cursor()
        q = (
            "SELECT id, cliente, tipo_item, kilos, cantidad, servicio, perfumado, precio, fecha, metodo_pago, estado "
            "FROM boletas"
        )
        params, conds = [], []
        if cliente:
            conds.append("cliente LIKE ?"); params.append(f"%{cliente}%")
        if fecha_desde:
            conds.append("date(substr(fecha,1,10)) >= date(?)"); params.append(fecha_desde)
        if fecha_hasta:
            conds.append("date(substr(fecha,1,10)) <= date(?)"); params.append(fecha_hasta)
        if conds: q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY fecha DESC, id DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        cur.execute(q, params)
        return cur.fetchall()

def contar_boletas(cliente=None, fecha_desde=None, fecha_hasta=None):
    with _conn() as conn:
        cur = conn.cursor()
        q = "SELECT COUNT(1) FROM boletas"
        params, conds = [], []
        if cliente:
            conds.append("cliente LIKE ?"); params.append(f"%{cliente}%")
        if fecha_desde:
            conds.append("date(substr(fecha,1,10)) >= date(?)"); params.append(fecha_desde)
        if fecha_hasta:
            conds.append("date(substr(fecha,1,10)) <= date(?)"); params.append(fecha_hasta)
        if conds: q += " WHERE " + " AND ".join(conds)
        cur.execute(q, params)
        return cur.fetchone()[0]

def total_periodo(cliente=None, fecha_desde=None, fecha_hasta=None):
    with _conn() as conn:
        cur = conn.cursor()
        q = "SELECT COALESCE(SUM(precio), 0) FROM boletas"
        params, conds = [], []
        if cliente:
            conds.append("cliente LIKE ?"); params.append(f"%{cliente}%")
        if fecha_desde:
            conds.append("date(substr(fecha,1,10)) >= date(?)"); params.append(fecha_desde)
        if fecha_hasta:
            conds.append("date(substr(fecha,1,10)) <= date(?)"); params.append(fecha_hasta)
        if conds: q += " WHERE " + " AND ".join(conds)
        cur.execute(q, params)
        return float(cur.fetchone()[0])

def obtener_boletas_todas():
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, cliente, tipo_item, kilos, cantidad, servicio, perfumado, precio, fecha, metodo_pago, estado "
            "FROM boletas ORDER BY fecha DESC, id DESC"
        )
        return cur.fetchall()

# ====== NUEVA API (Boleta con múltiples items) ======
def insertar_boleta_compuesta(cabecera: dict, items: list[dict]) -> int:
    """
    Inserta una boleta (cabecera) + sus items.
    cabecera: dict con keys: numero, cliente, direccion, telefono, fecha, entrega_fecha, entrega_hora,
                             metodo_pago, estado, a_cuenta, saldo, total, notas
    items: lista de dicts con keys: descripcion, tipo, prendas, kilos, lavado, secado, p_unit, importe
    Return: boleta_id (int)
    """
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO boleta (numero, cliente, direccion, telefono, fecha, entrega_fecha, entrega_hora,
                                metodo_pago, estado, a_cuenta, saldo, total, notas)
            VALUES (:numero, :cliente, :direccion, :telefono, :fecha, :entrega_fecha, :entrega_hora,
                    :metodo_pago, :estado, :a_cuenta, :saldo, :total, :notas)
            """,
            cabecera
        )
        boleta_id = cur.lastrowid

        for it in items:
            it = {**it, "boleta_id": boleta_id}
            cur.execute(
                """
                INSERT INTO boleta_items (boleta_id, descripcion, tipo, prendas, kilos, lavado, p_unit, importe, perfumado)
                VALUES (:boleta_id, :descripcion, :tipo, CASE WHEN :tipo = 'kilo' THEN 0 ELSE :cantidad END, CASE WHEN :tipo = 'kilo' THEN :cantidad ELSE 0 END, :lavado, :p_unit, :importe, :perfumado)
                """,
                it
            )
        conn.commit()
        return boleta_id

def obtener_boletas_cabecera(limit=20, offset=0, cliente=None, fecha_desde=None, fecha_hasta=None):
    with _conn() as conn:
        cur = conn.cursor()
        q = ("SELECT id, numero, cliente, fecha, entrega_fecha, entrega_hora, metodo_pago, estado, a_cuenta, saldo, total "
             "FROM boleta")
        params, conds = [], []
        if cliente:
            conds.append("cliente LIKE ?"); params.append(f"%{cliente}%")
        if fecha_desde:
            conds.append("date(substr(fecha,1,10)) >= date(?)"); params.append(fecha_desde)
        if fecha_hasta:
            conds.append("date(substr(fecha,1,10)) <= date(?)"); params.append(fecha_hasta)
        if conds: q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY date(substr(fecha,1,10)) DESC, id DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        cur.execute(q, params)
        return cur.fetchall()

def obtener_boleta_detalle(boleta_id: int):
    """Devuelve (cabecera, items[])"""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, numero, cliente, direccion, telefono, fecha, entrega_fecha, entrega_hora, "
            "metodo_pago, estado, a_cuenta, saldo, total, notas "
            "FROM boleta WHERE id = ?",
            (boleta_id,)
        )
        cab = cur.fetchone()

        cur.execute(
            """
            SELECT id, descripcion, tipo,
                   CASE WHEN tipo = 'kilo' THEN kilos ELSE prendas END as cantidad,
                   lavado, p_unit, importe, perfumado
            FROM boleta_items WHERE boleta_id = ? ORDER BY id ASC
            """,
            (boleta_id,)
        )
        items = cur.fetchall()
        return cab, items
