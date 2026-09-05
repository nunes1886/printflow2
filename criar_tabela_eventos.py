import sqlite3
import os

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'printflow.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS eventos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo VARCHAR(100) NOT NULL,
        inicio VARCHAR(50) NOT NULL,
        fim VARCHAR(50),
        cor VARCHAR(20) DEFAULT '#0079bf',
        criado_por VARCHAR(100),
        visibilidade VARCHAR(200) DEFAULT 'todos'
    )
    ''')
    conn.commit()
    print("Sucesso: Tabela 'eventos' criada ou verificada com sucesso!")
except Exception as e:
    print("Erro ao criar tabela:", e)

conn.close()