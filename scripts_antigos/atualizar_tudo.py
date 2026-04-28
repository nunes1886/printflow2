from app import app, db
from sqlalchemy import text

print("--- INICIANDO ATUALIZAÇÃO GERAL DO BANCO DE DADOS (v4.4) ---")

with app.app_context():
    # 1. Cria tabelas novas que não existem (Comentarios, Usuario_Setores, etc)
    db.create_all()
    print("✅ Tabelas novas verificadas/criadas.")

    # 2. Verifica e adiciona coluna 'acesso_estoque' se faltar
    try:
        with db.engine.connect() as conn:
            # Tenta selecionar a coluna para ver se existe
            conn.execute(text("SELECT acesso_estoque FROM usuarios LIMIT 1"))
            print("ℹ️ Coluna 'acesso_estoque' já existe.")
    except:
        # Se der erro, é porque não existe. Cria a coluna.
        print("⚠️ Coluna 'acesso_estoque' ausente. Criando...")
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN acesso_estoque BOOLEAN DEFAULT 0"))
            conn.commit()
        print("✅ Coluna 'acesso_estoque' adicionada com sucesso.")

print("--- FIM DA ATUALIZAÇÃO ---")
print("Pode fechar e iniciar o sistema.")
input("Pressione ENTER para sair...")