import sqlite3
from database import DB_PATH

def recreate_tables():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Eliminar tablas existentes
    cur.execute("DROP TABLE IF EXISTS boleta_items")
    cur.execute("DROP TABLE IF EXISTS boleta")
    cur.execute("DROP TABLE IF EXISTS boletas")
    
    # Crear tablas con nueva estructura
    cur.execute("""
        CREATE TABLE boletas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            tipo_item TEXT NOT NULL,
            cantidad REAL DEFAULT 0,
            lavado TEXT DEFAULT 'normal',
            perfumado INTEGER DEFAULT 0,
            precio REAL NOT NULL,
            fecha TEXT NOT NULL,
            metodo_pago TEXT DEFAULT 'efectivo',
            estado TEXT DEFAULT 'registrado'
        )
    """)
    
    cur.execute("""
        CREATE TABLE boleta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT,
            cliente TEXT NOT NULL,
            direccion TEXT,
            telefono TEXT,
            fecha TEXT NOT NULL,
            entrega_fecha TEXT,
            entrega_hora TEXT,
            metodo_pago TEXT DEFAULT 'efectivo',
            estado TEXT DEFAULT 'registrado',
            a_cuenta REAL DEFAULT 0,
            saldo REAL DEFAULT 0,
            total REAL DEFAULT 0,
            notas TEXT
        )
    """)
    
    cur.execute("""
        CREATE TABLE boleta_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            boleta_id INTEGER NOT NULL REFERENCES boleta(id) ON DELETE CASCADE,
            descripcion TEXT,
            tipo TEXT,
            cantidad REAL DEFAULT 0,
            lavado TEXT,
            perfumado INTEGER DEFAULT 0,
            p_unit REAL DEFAULT 0,
            importe REAL DEFAULT 0
        )
    """)
    
    # Recrear índices
    cur.execute("CREATE INDEX idx_boleta_fecha ON boleta(fecha)")
    cur.execute("CREATE INDEX idx_boleta_cliente ON boleta(cliente)")
    cur.execute("CREATE INDEX idx_bitems_boleta ON boleta_items(boleta_id)")
    cur.execute("CREATE INDEX idx_boletas_fecha ON boletas(fecha)")
    cur.execute("CREATE INDEX idx_boletas_cliente ON boletas(cliente)")
    
    conn.commit()
    conn.close()
    print("Base de datos recreada exitosamente")

if __name__ == "__main__":
    recreate_tables()