import sqlite3
import os

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'printflow.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS historico_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id INTEGER NOT NULL,
        setor_id INTEGER NOT NULL,
        data_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE,
        FOREIGN KEY(setor_id) REFERENCES setores(id) ON DELETE CASCADE
    )
    ''')
    conn.commit()
    print("Sucesso: Tabela 'historico_cards' criada com sucesso para armazenar dados do Dashboard!")
except Exception as e:
    print("Erro ao criar tabela:", e)

conn.close()