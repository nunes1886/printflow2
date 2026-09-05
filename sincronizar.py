from app import app, db, Card, HistoricoCard

with app.app_context():
    cards = Card.query.all()
    adicionados = 0
    for c in cards:
        # Verifica se o card antigo já tem histórico no setor atual
        existe = HistoricoCard.query.filter_by(card_id=c.id, setor_id=c.setor_id).first()
        if not existe:
            db.session.add(HistoricoCard(card_id=c.id, setor_id=c.setor_id))
            adicionados += 1
    db.session.commit()
    print(f"Sucesso! {adicionados} pedidos antigos foram sincronizados no histórico.")