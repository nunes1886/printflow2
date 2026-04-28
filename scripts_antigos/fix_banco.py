from app import app, db

print("--- INICIANDO CORREÇÃO DO BANCO DE DADOS ---")

with app.app_context():
    try:
        # Isso força o SQLAlchemy a olhar o código e criar o que falta no banco
        db.create_all()
        print("Sucesso! Tabelas novas (usuario_setores) foram criadas.")
    except Exception as e:
        print(f"Erro ao criar tabelas: {e}")

print("--- FIM ---")
print("Pode fechar esta janela e iniciar o sistema normalmente pelo .bat")
input("Pressione ENTER para sair...")