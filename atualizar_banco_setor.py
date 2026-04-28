import sqlite3

def atualizar():
    conn = sqlite3.connect('printflow.db')
    try:
        conn.execute("ALTER TABLE setores ADD COLUMN mostrar_no_kanban BOOLEAN DEFAULT 1")
        print("✅ Coluna 'mostrar_no_kanban' adicionada com sucesso!")
    except Exception as e:
        print(f"Aviso: {e}")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    atualizar()