from app import app, db

print("--- CRIANDO TABELA DE ANOTAÇÕES ---")

# Definição da nova tabela (igual vai estar no app.py)
class Comentario(db.Model):
    __tablename__ = 'comentarios'
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey('cards.id'), nullable=False)
    usuario = db.Column(db.String(100))
    texto = db.Column(db.Text)
    data = db.Column(db.DateTime, default=None) # Data hora automática

with app.app_context():
    db.create_all()
    print("✅ Sucesso! Tabela 'comentarios' criada.")

print("--- FIM ---")
input("Pressione ENTER para sair...")