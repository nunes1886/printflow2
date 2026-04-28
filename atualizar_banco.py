import sqlite3

def atualizar_banco():
    # Conecta ao banco de dados de produção
    conn = sqlite3.connect('printflow.db')
    cursor = conn.cursor()

    print("Iniciando atualização do banco de dados...")

    try:
        # Adicionando as colunas do CHAT 2.0
        cursor.execute("ALTER TABLE mensagens ADD COLUMN tipo_chat VARCHAR(20) DEFAULT 'global'")
        cursor.execute("ALTER TABLE mensagens ADD COLUMN destinatario VARCHAR(100)")
        cursor.execute("ALTER TABLE mensagens ADD COLUMN setor_id INTEGER")
        cursor.execute("ALTER TABLE mensagens ADD COLUMN lida BOOLEAN DEFAULT 0")
        print("✅ Colunas do Chat 2.0 adicionadas com sucesso!")
    except Exception as e:
        print("⚠️ Aviso Chat:", e)

    try:
        # Criando a tabela para o DASHBOARD (Log de Produção)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS log_producao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER,
            card_titulo VARCHAR(100),
            setor_nome VARCHAR(50),
            data_movimentacao VARCHAR(20)
        )
        """)
        print("✅ Tabela do Log de Produção (Dashboard) criada com sucesso!")
    except Exception as e:
        print("⚠️ Aviso Dashboard:", e)

    conn.commit()
    conn.close()
    print("Atualização finalizada!")

if __name__ == '__main__':
    atualizar_banco()