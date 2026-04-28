import sqlite3

def atualizar():
    conn = sqlite3.connect('printflow.db')
    cursor = conn.cursor()
    print("🔧 Preparando tabela de Status...")
    try:
        cursor.execute("ALTER TABLE status ADD COLUMN ordem INTEGER DEFAULT 0")
        print("✅ Coluna 'ordem' adicionada aos Status!")
    except Exception as e:
        print(f"⚠️ Aviso: {e}")
    
    # Inicializa a ordem baseada no ID atual para os status que já existem
    cursor.execute("SELECT id FROM status")
    rows = cursor.fetchall()
    for row in rows:
        cursor.execute("UPDATE status SET ordem = ? WHERE id = ?", (row[0], row[0]))
    
    conn.commit()
    conn.close()
    print("🚀 Banco pronto!")

if __name__ == '__main__':
    atualizar()