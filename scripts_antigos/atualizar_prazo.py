import sqlite3
import os

# Caminho do banco
db_path = os.path.join(os.path.dirname(__file__), 'printflow.db')

if not os.path.exists(db_path):
    print("ERRO: Banco de dados não encontrado!")
    exit()

print(f"Conectando ao banco: {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("Tentando adicionar coluna 'prazo' na tabela 'cards'...")
    # O comando ALTER TABLE adiciona uma coluna nova
    cursor.execute("ALTER TABLE card ADD COLUMN prazo TEXT") 
    print("✅ Sucesso! Coluna 'prazo' criada.")
except sqlite3.OperationalError as e:
    # Se der erro dizendo que a tabela é "cards" (plural) ou "card" (singular), o script avisa
    try:
        cursor.execute("ALTER TABLE cards ADD COLUMN prazo TEXT")
        print("✅ Sucesso! Coluna 'prazo' criada na tabela 'cards'.")
    except sqlite3.OperationalError as e2:
        if "duplicate column name" in str(e) or "duplicate column name" in str(e2):
            print("⚠️ A coluna 'prazo' já existe. Tudo certo, não precisa fazer nada!")
        else:
            print(f"❌ Erro ao alterar banco: {e}")

conn.commit()
conn.close()
input("\nPressione Enter para sair...")