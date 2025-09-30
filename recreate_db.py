import os
import sqlite3
from database import DB_PATH

def drop_and_recreate():
    # Intentar eliminar las tablas existentes
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Eliminar tablas si existen
        cur.execute("DROP TABLE IF EXISTS boleta_items")
        cur.execute("DROP TABLE IF EXISTS boleta")
        cur.execute("DROP TABLE IF EXISTS boletas")
        
        # Crear tabla boleta
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
        
        # Crear tabla boleta_items
        cur.execute("""
            CREATE TABLE boleta_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                boleta_id INTEGER NOT NULL REFERENCES boleta(id) ON DELETE CASCADE,
                descripcion TEXT,
                tipo TEXT,
                prendas INTEGER DEFAULT 0,
                kilos REAL DEFAULT 0,
                lavado TEXT,
                secado TEXT,
                p_unit REAL DEFAULT 0,
                importe REAL DEFAULT 0,
                perfumado INTEGER DEFAULT 0
            )
        """)
        
        # Crear tabla boletas (compatibilidad)
        cur.execute("""
            CREATE TABLE boletas (
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
        """)
        
        # Crear índices
        cur.execute("CREATE INDEX idx_boleta_fecha ON boleta(fecha)")
        cur.execute("CREATE INDEX idx_boleta_cliente ON boleta(cliente)")
        cur.execute("CREATE INDEX idx_bitems_boleta ON boleta_items(boleta_id)")
        cur.execute("CREATE INDEX idx_boletas_fecha ON boletas(fecha)")
        cur.execute("CREATE INDEX idx_boletas_cliente ON boletas(cliente)")
        
        conn.commit()
        print("Base de datos recreada exitosamente con todas las tablas y columnas.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    drop_and_recreate()