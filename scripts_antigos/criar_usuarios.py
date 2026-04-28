import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = 'printflow.db'

def adicionar_usuarios():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Senhas criptografadas (para segurança igual ao app)
    senha_admin = generate_password_hash('admin')
    senha_joao = generate_password_hash('1234')

    usuarios = [
        # (username, senha, funcao)
        ('admin', senha_admin, 'admin'),
        ('joao', senha_joao, 'colaborador')
    ]

    try:
        cursor.executemany('''
            INSERT INTO usuarios (username, senha, funcao) 
            VALUES (?, ?, ?)
        ''', usuarios)
        conn.commit()
        print("Usuários 'admin' e 'joao' criados com sucesso!")
    except sqlite3.IntegrityError:
        print("Os usuários já existem no banco.")
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    adicionar_usuarios()