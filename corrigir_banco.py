import sqlite3

def corrigir_banco():
    conn = sqlite3.connect('printflow.db')
    cursor = conn.cursor()

    print("🔧 Iniciando correção do banco de dados...")

    # 1. Renomeia a coluna 'usuario' para 'remetente' mantendo as mensagens antigas
    try:
        cursor.execute("ALTER TABLE mensagens RENAME COLUMN usuario TO remetente")
        print("✅ Coluna 'usuario' renomeada para 'remetente' com sucesso!")
    except Exception as e:
        print(f"⚠️ Aviso ao renomear: {e}")

    # 2. Cria a coluna para suportar o envio de imagens/prints no chat
    try:
        cursor.execute("ALTER TABLE mensagens ADD COLUMN imagem_path TEXT")
        print("✅ Coluna 'imagem_path' adicionada com sucesso!")
    except Exception as e:
        print(f"⚠️ Aviso na imagem: {e}")

    conn.commit()
    conn.close()
    print("🚀 Correção finalizada! Pode iniciar o servidor.")

if __name__ == '__main__':
    corrigir_banco()