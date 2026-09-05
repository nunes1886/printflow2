import sqlite3
import os

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'printflow.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE eventos ADD COLUMN visibilidade VARCHAR(200) DEFAULT 'todos'")
    conn.commit()
    print("Sucesso: Coluna 'visibilidade' adicionada à tabela eventos!")
except sqlite3.OperationalError as e:
    print("Aviso do banco de dados:", e)

conn.close()