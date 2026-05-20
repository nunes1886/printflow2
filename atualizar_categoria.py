import sqlite3

try:
    conn = sqlite3.connect('printflow.db')
    c = conn.cursor()
    # Adiciona a nova coluna com um valor padrão
    c.execute("ALTER TABLE materiais ADD COLUMN categoria VARCHAR(50) DEFAULT 'Geral / Outros'")
    conn.commit()
    conn.close()
    print("Sucesso! Coluna 'categoria' adicionada ao banco de dados.")
except Exception as e:
    print(f"Aviso: {e} (A coluna já deve existir).")