from app import app, db
from sqlalchemy import text

print("--- ATUALIZANDO BANCO DE DADOS (PERMISSÃO ESTOQUE) ---")

with app.app_context():
    try:
        # Comando SQL direto para criar a coluna nova na tabela existente
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN acesso_estoque BOOLEAN DEFAULT 0"))
            conn.commit()
        print("✅ Sucesso! Coluna 'acesso_estoque' criada.")
    except Exception as e:
        print(f"⚠️ Aviso (pode ser ignorado se a coluna já existir): {e}")

print("--- FIM ---")
input("Pressione ENTER para sair...")