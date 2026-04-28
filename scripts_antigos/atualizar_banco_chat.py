import sqlite3

# Adiciona a tabela de mensagens ao banco existente
def adicionar_tabela_chat():
    conn = sqlite3.connect('printflow.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mensagens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT NOT NULL,
        texto TEXT NOT NULL,
        data_envio TEXT NOT NULL
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Tabela de Chat criada com sucesso!")

if __name__ == "__main__":
    adicionar_tabela_chat()