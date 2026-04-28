import sqlite3
import os

# Nome do banco
DB_NAME = 'printflow.db'

def criar_banco():
    # Remove o banco antigo se existir para garantir a estrutura nova
    # (Cuidado: isso apaga todos os dados ao rodar este script!)
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"Banco antigo {DB_NAME} removido.")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Tabela de Usuários
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        senha TEXT NOT NULL,
        funcao TEXT NOT NULL
    )
    ''')

    # 2. Tabela de Setores
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS setores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        ordem INTEGER NOT NULL
    )
    ''')

    # 3. Tabela de Status
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cor TEXT DEFAULT '#CCCCCC'
    )
    ''')

    # 4. Tabela de Cards (ATUALIZADA COM OS NOVOS CAMPOS)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        descricao TEXT,
        cliente TEXT,
        imagem_path TEXT,
        data_criacao TEXT,
        setor_id INTEGER,
        status_id INTEGER,
        created_by TEXT,               -- Novo campo: Quem criou
        is_archived INTEGER DEFAULT 0, -- Novo campo: Se está arquivado (0=Não, 1=Sim)
        FOREIGN KEY(setor_id) REFERENCES setores(id),
        FOREIGN KEY(status_id) REFERENCES status(id)
    )
    ''')
    
    # 5. Tabela de Mensagens (Caso não tenha sido criada antes via SQLAlchemy)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mensagens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        texto TEXT,
        data_envio TEXT
    )
    ''')

    conn.commit()
    print(f"Banco de dados {DB_NAME} recriado com nova estrutura.")
    return conn

def popular_dados_iniciais(conn):
    cursor = conn.cursor()

    # --- Criar Admin Padrão ---
    # Senha hash gerada para 'admin' (padrão scrypt do werkzeug pode variar, 
    # mas aqui vamos inserir um admin simples para o primeiro login funcionar via app.py se a lógica lá permitir criar,
    # ou você cria o primeiro usuário rodando o app.py que tem aquela verificação no final __main__)
    # Vou deixar o app.py criar o admin para garantir o hash correto da senha.

    # --- Popular Setores ---
    cursor.execute('SELECT count(*) FROM setores')
    if cursor.fetchone()[0] == 0:
        setores_padrao = [
            ("Atendimento", 1),
            ("Impressão 01", 2),
            ("Impressão 02", 3),
            ("Produção", 4),
            ("Expedição", 5)
        ]
        cursor.executemany('INSERT INTO setores (nome, ordem) VALUES (?, ?)', setores_padrao)
        print("Setores inseridos.")

    # --- Popular Status ---
    cursor.execute('SELECT count(*) FROM status')
    if cursor.fetchone()[0] == 0:
        status_padrao = [
            ("Fila", "blue"),
            ("Rodando", "green"),
            ("Aguardando encaixe", "orange"),
            ("Aguardando material", "red"),
            ("Impresso", "teal"),
            ("Expedição", "purple")
        ]
        cursor.executemany('INSERT INTO status (nome, cor) VALUES (?, ?)', status_padrao)
        print("Status inseridos.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    conexao = criar_banco()
    popular_dados_iniciais(conexao)
    print("Script concluído.")