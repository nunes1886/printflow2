import os
import time
import base64
import uuid 
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text

# --- CONFIGURAÇÃO ---
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave-super-secreta-printflow'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'printflow.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- CONTROLE DE VERSÃO ---
ULTIMA_ATUALIZACAO = time.time()
def atualizar_versao():
    global ULTIMA_ATUALIZACAO
    ULTIMA_ATUALIZACAO = time.time()

# --- RASTREAMENTO ONLINE ---
usuarios_online = {}

@app.before_request
def rastrear_atividade():
    if current_user.is_authenticated:
        usuarios_online[current_user.username] = datetime.now()

# --- TABELA DE ASSOCIAÇÃO (USUARIO <-> SETOR) ---
usuario_setores = db.Table('usuario_setores',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuarios.id'), primary_key=True),
    db.Column('setor_id', db.Integer, db.ForeignKey('setores.id'), primary_key=True)
)

# --- MODELOS ---

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    funcao = db.Column(db.String(20), nullable=False)
    
    acesso_estoque = db.Column(db.Boolean, default=False)
    
    acessos = db.relationship('Setor', secondary=usuario_setores, lazy='subquery',
        backref=db.backref('usuarios_permitidos', lazy=True))

    def get_id(self): return str(self.id)
    @property
    def is_admin(self): return self.funcao == 'admin'
    def check_password(self, password):
        try: return check_password_hash(self.senha, password)
        except: return self.senha == password
    def set_password(self, password): self.senha = generate_password_hash(password)

class Setor(db.Model):
    __tablename__ = 'setores'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    ordem = db.Column(db.Integer, nullable=False)
    mostrar_no_kanban = db.Column(db.Boolean, default=True)
    cards = db.relationship('Card', backref='setor_ref', lazy=True, order_by='Card.id')

class Status(db.Model):
    __tablename__ = 'status'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    cor = db.Column(db.String(20), default='#CCCCCC')
    ordem = db.Column(db.Integer, default=0) 

class Card(db.Model):
    __tablename__ = 'cards'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    cliente = db.Column(db.String(100), nullable=True)
    imagem_path = db.Column(db.Text, nullable=True)
    data_criacao = db.Column(db.String(50))
    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'))
    status_id = db.Column(db.Integer, db.ForeignKey('status.id'))
    status_ref = db.relationship('Status', lazy=True)
    created_by = db.Column(db.String(100))
    is_archived = db.Column(db.Boolean, default=False)
    prazo = db.Column(db.String(20))
    
    comentarios = db.relationship('Comentario', backref='card', lazy=True, cascade="all, delete-orphan")

class HistoricoCard(db.Model):
    __tablename__ = 'historico_cards'
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey('cards.id', ondelete='CASCADE'), nullable=False)
    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id', ondelete='CASCADE'), nullable=False)
    data_registro = db.Column(db.DateTime, default=datetime.now)

class Comentario(db.Model):
    __tablename__ = 'comentarios'
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey('cards.id'), nullable=False)
    usuario = db.Column(db.String(100))
    texto = db.Column(db.Text)
    data = db.Column(db.DateTime, default=datetime.now)

class Mensagem(db.Model):
    __tablename__ = 'mensagens'
    id = db.Column(db.Integer, primary_key=True)
    remetente = db.Column(db.String(100))
    texto = db.Column(db.Text, nullable=True) 
    imagem_path = db.Column(db.Text, nullable=True) 
    data_envio = db.Column(db.String(50))
    
    tipo_chat = db.Column(db.String(20), default='global')
    destinatario = db.Column(db.String(100), nullable=True) 
    setor_id = db.Column(db.Integer, nullable=True) 
    
    lida = db.Column(db.Boolean, default=False)

class Material(db.Model):
    __tablename__ = 'materiais'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50), default='Geral / Outros')
    unidade = db.Column(db.String(20), default='Unid')
    quantidade = db.Column(db.Float, default=0.0)
    minimo = db.Column(db.Float, default=5.0)
    historico = db.relationship('Movimentacao', backref='material', lazy=True, cascade="all, delete-orphan")

class Movimentacao(db.Model):
    __tablename__ = 'movimentacoes'
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materiais.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    usuario = db.Column(db.String(100))
    data = db.Column(db.DateTime, default=datetime.now)

class Evento(db.Model):
    __tablename__ = 'eventos'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    inicio = db.Column(db.String(50), nullable=False) 
    fim = db.Column(db.String(50), nullable=True)
    cor = db.Column(db.String(20), default='#0079bf')
    criado_por = db.Column(db.String(100))
    visibilidade = db.Column(db.String(200), default='todos')

@login_manager.user_loader
def load_user(user_id): return Usuario.query.get(int(user_id))

def salvar_imagem_base64(base64_string):
    if not base64_string: return None
    try:
        header, encoded = base64_string.split(",", 1)
        data = base64.b64decode(encoded)
        filename = f"{uuid.uuid4()}.png"
        folder = os.path.join(basedir, 'static', 'uploads')
        if not os.path.exists(folder): os.makedirs(folder)
        filepath = os.path.join(folder, filename)
        with open(filepath, "wb") as f: f.write(data)
        return filename
    except: 
        return None

def notificar_status_n8n(card, nome_coluna):
    url_n8n = "http://localhost:5678/webhook-test/atualizacao-pedido" 
    payload = {
        "cliente": card.cliente or "Cliente",
        "telefone": "5579999999999", 
        "pedido": str(card.id),
        "produto": card.titulo,
        "etapa_atual": nome_coluna
    }
    try: requests.post(url_n8n, json=payload, timeout=3)
    except Exception as e: print(f"Erro ao notificar n8n: {e}")

# --- ROTAS PRINCIPAIS ---

@app.route('/verificar_atualizacao')
@login_required
def verificar_atualizacao():
    if current_user.is_admin:
        ultimo_msg = Mensagem.query.order_by(Mensagem.id.desc()).first()
    else:
        ids_permitidos = [s.id for s in current_user.acessos]
        ultimo_msg = Mensagem.query.filter(
            (Mensagem.tipo_chat == 'global') |
            ((Mensagem.tipo_chat == 'direto') & ((Mensagem.remetente == current_user.username) | (Mensagem.destinatario == current_user.username))) |
            ((Mensagem.tipo_chat == 'setor') & (Mensagem.setor_id.in_(ids_permitidos)))
        ).order_by(Mensagem.id.desc()).first()
        
    msg_id = ultimo_msg.id if ultimo_msg else 0
    last_msg_texto = ultimo_msg.texto if ultimo_msg else ""
    last_msg_remetente = ultimo_msg.remetente if ultimo_msg else ""
    last_card = Card.query.order_by(Card.id.desc()).first()
    card_id = last_card.id if last_card else 0
    
    return jsonify({
        'timestamp': ULTIMA_ATUALIZACAO, 
        'chat_id': msg_id, 
        'last_card_id': card_id,
        'last_msg_texto': last_msg_texto,         
        'last_msg_remetente': last_msg_remetente  
    })

@app.route('/chat/contatos')
@login_required
def chat_contatos():
    usuarios = [u.username for u in Usuario.query.all() if u.username != current_user.username]
    
    if current_user.is_admin:
        setores_permitidos = Setor.query.filter_by(mostrar_no_kanban=False).order_by(Setor.ordem).all()
    else:
        setores_permitidos = [s for s in current_user.acessos if not s.mostrar_no_kanban]
        setores_permitidos = sorted(setores_permitidos, key=lambda s: s.ordem)
        
    setores = [{'id': s.id, 'nome': s.nome} for s in setores_permitidos]
    nao_lidas = {'global': False, 'setores': {}, 'direto': {}}
    
    if Mensagem.query.filter_by(tipo_chat='global', lida=False).filter(Mensagem.remetente != current_user.username).first():
        nao_lidas['global'] = True
        
    for s in setores_permitidos:
        if Mensagem.query.filter_by(tipo_chat='setor', setor_id=s.id, lida=False).filter(Mensagem.remetente != current_user.username).first():
            nao_lidas['setores'][str(s.id)] = True
            
    for u in usuarios:
        if Mensagem.query.filter_by(tipo_chat='direto', remetente=u, destinatario=current_user.username, lida=False).first():
            nao_lidas['direto'][u] = True

    agora = datetime.now()
    status_online = {}
    for u in usuarios:
        ultimo_acesso = usuarios_online.get(u)
        if ultimo_acesso and (agora - ultimo_acesso).total_seconds() < 300:
            status_online[u] = True
        else:
            status_online[u] = False

    return jsonify({'usuarios': usuarios, 'setores': setores, 'nao_lidas': nao_lidas, 'online': status_online})

@app.route('/chat/enviar', methods=['POST'])
@login_required
def enviar_mensagem():
    data = request.get_json()
    texto = data.get('texto')
    img_base64 = data.get('imagem_base64')
    tipo_chat = data.get('tipo_chat', 'global')
    setor_id = data.get('setor_id')
    
    if not texto and not img_base64: return jsonify({'error': 'Vazio'}), 400
    if tipo_chat == 'setor' and not current_user.is_admin:
        ids_permitidos = [str(s.id) for s in current_user.acessos]
        if str(setor_id) not in ids_permitidos:
            return jsonify({'error': 'Sem permissão para este setor'}), 403
    
    caminho_img = salvar_imagem_base64(img_base64) if img_base64 else None
    nova_msg = Mensagem(
        remetente=current_user.username,
        texto=texto,
        imagem_path=caminho_img,
        data_envio=datetime.now().strftime("%H:%M"),
        tipo_chat=tipo_chat,
        destinatario=data.get('destinatario'),
        setor_id=setor_id
    )
    db.session.add(nova_msg)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/chat/listar')
@login_required
def listar_mensagens():
    tipo = request.args.get('tipo', 'global')
    dest = request.args.get('destinatario')
    setor = request.args.get('setor_id')
    chat_aberto = request.args.get('aberto') == 'true' 
    
    query = Mensagem.query
    if tipo == 'global':
        query = query.filter_by(tipo_chat='global')
    elif tipo == 'direto':
        query = query.filter(db.or_(
            db.and_(Mensagem.remetente == current_user.username, Mensagem.destinatario == dest),
            db.and_(Mensagem.remetente == dest, Mensagem.destinatario == current_user.username)
        ))
    elif tipo == 'setor':
        if not current_user.is_admin:
            ids_permitidos = [str(s.id) for s in current_user.acessos]
            if str(setor) not in ids_permitidos: return jsonify([]) 
        query = query.filter_by(tipo_chat='setor', setor_id=setor)
        
    msgs = query.order_by(Mensagem.id.desc()).limit(50).all()
    msgs.reverse()
    
    alterou = False
    if chat_aberto:
        for m in msgs:
            if m.remetente != current_user.username and not m.lida:
                m.lida = True
                alterou = True
                
    if alterou: db.session.commit()
    
    return jsonify([{
        'id': m.id, 'remetente': m.remetente, 'texto': m.texto, 
        'imagem_path': m.imagem_path, 'hora': m.data_envio, 
        'eu_mesmo': m.remetente == current_user.username, 'lida': m.lida
    } for m in msgs])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = Usuario.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user)
            return redirect(url_for('index'))
        flash('Erro no login.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout(): 
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    todos_setores = Setor.query.order_by(Setor.ordem).all()
    lista_status = Status.query.order_by(Status.ordem).all() 
    setores_visiveis = []
    
    if current_user.is_admin:
        setores_visiveis = todos_setores
    else:
        if len(current_user.acessos) > 0:
            ids_permitidos = [s.id for s in current_user.acessos]
            setores_visiveis = [s for s in todos_setores if s.id in ids_permitidos]
        else:
            setores_visiveis = todos_setores

    setores_visiveis = [s for s in setores_visiveis if s.mostrar_no_kanban]

    for setor in setores_visiveis:
        setor.cards.sort(key=lambda card: (1 if not card.prazo else 0, card.prazo or ""))

    return render_template('index.html', setores=setores_visiveis, lista_status=lista_status, user=current_user)

@app.route('/usuarios')
@login_required
def usuarios():
    if not current_user.is_admin: return redirect(url_for('index'))
    users = Usuario.query.all()
    todos_setores = Setor.query.order_by(Setor.ordem).all()
    return render_template('usuarios.html', users=users, setores=todos_setores, user=current_user)

@app.route('/usuario/salvar', methods=['POST'])
@login_required
def salvar_usuario():
    if not current_user.is_admin: return "Negado", 403
    uid = request.form.get('id')
    nome = request.form.get('username')
    senha = request.form.get('password')
    is_admin_check = request.form.get('is_admin')
    acesso_estoque_check = request.form.get('acesso_estoque')
    setores_ids = request.form.getlist('acesso_setores') 
    nova_funcao = 'admin' if is_admin_check == 'on' else 'colaborador'
    
    if uid:
        u = Usuario.query.get(uid)
        u.username = nome
        u.funcao = nova_funcao
        u.acesso_estoque = (acesso_estoque_check == 'on')
        if senha: u.set_password(senha)
    else:
        if Usuario.query.filter_by(username=nome).first():
            flash('Usuário já existe.')
            return redirect(url_for('usuarios'))
        u = Usuario(username=nome, funcao=nova_funcao)
        u.set_password(senha if senha else '1234')
        u.acesso_estoque = (acesso_estoque_check == 'on')
        db.session.add(u)
    
    u.acessos = [] 
    for sid in setores_ids:
        setor = Setor.query.get(int(sid))
        if setor: u.acessos.append(setor)
            
    db.session.commit()
    return redirect(url_for('usuarios'))

@app.route('/usuario/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_usuario(id):
    if not current_user.is_admin or id == current_user.id: return jsonify({'error': 'Erro'}), 400
    db.session.delete(Usuario.query.get(id))
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/card/<int:card_id>')
@login_required
def get_card_data(card_id):
    c = Card.query.get_or_404(card_id)
    return jsonify({'id':c.id, 'titulo':c.titulo, 'descricao':c.descricao, 'cliente':c.cliente, 'setor_id':c.setor_id, 'status_id':c.status_id, 'imagem_path':c.imagem_path, 'created_by':c.created_by, 'prazo':c.prazo})

@app.route('/api/comentarios/<int:card_id>')
@login_required
def get_comentarios(card_id):
    comentarios = Comentario.query.filter_by(card_id=card_id).order_by(Comentario.data.asc()).all()
    return jsonify([{
        'usuario': c.usuario,
        'texto': c.texto,
        'data': c.data.strftime("%d/%m %H:%M")
    } for c in comentarios])

@app.route('/api/comentar', methods=['POST'])
@login_required
def comentar_card():
    data = request.get_json()
    if not data.get('texto'): return jsonify({'error': 'Vazio'}), 400
    c = Comentario(card_id=data.get('card_id'), usuario=current_user.username, texto=data.get('texto'))
    db.session.add(c)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/adicionar', methods=['POST'])
@login_required
def adicionar():
    if not current_user.is_admin: return "Negado", 403
    img = salvar_imagem_base64(request.form.get('imagem_base64'))
    s = Setor.query.order_by(Setor.ordem).first()
    st = Status.query.filter(Status.nome.ilike('Pendente')).first()
    if not st: st = Status.query.order_by(Status.ordem).first()
        
    c = Card(
        titulo=request.form.get('titulo'), 
        cliente=request.form.get('cliente'), 
        descricao=request.form.get('descricao'), 
        data_criacao=datetime.now().strftime("%d/%m %H:%M"), 
        setor_id=s.id, 
        status_id=st.id, 
        imagem_path=img, 
        created_by=current_user.username, 
        prazo=request.form.get('prazo')
    )
    db.session.add(c)
    db.session.commit()
    
    # Registra a entrada no setor inicial
    db.session.add(HistoricoCard(card_id=c.id, setor_id=s.id))
    db.session.commit()
    
    atualizar_versao()
    return redirect(url_for('index'))

@app.route('/editar', methods=['POST'])
@login_required
def editar():
    c = Card.query.get(request.form.get('id'))
    if c:
        novo_setor_id = int(request.form.get('setor_id')) if request.form.get('setor_id') else c.setor_id
        
        if c.setor_id != novo_setor_id:
            c.setor_id = novo_setor_id
            db.session.add(HistoricoCard(card_id=c.id, setor_id=novo_setor_id))
            
        if request.form.get('status_id'): c.status_id = int(request.form.get('status_id'))
        
        if current_user.is_admin:
            c.titulo = request.form.get('titulo')
            c.cliente = request.form.get('cliente')
            c.descricao = request.form.get('descricao')
            c.prazo = request.form.get('prazo')
            img = salvar_imagem_base64(request.form.get('imagem_base64'))
            if img: c.imagem_path = img
            
        db.session.commit()
        atualizar_versao()
    return redirect(url_for('index'))

@app.route('/mover', methods=['POST'])
@login_required
def mover():
    data = request.get_json()
    c = Card.query.get(data.get('id'))
    if c:
        if 'setor_id' in data:
            novo_setor_id = data.get('setor_id')
            if c.setor_id != novo_setor_id:
                c.setor_id = novo_setor_id
                db.session.add(HistoricoCard(card_id=c.id, setor_id=novo_setor_id))

        if 'status_id' in data: c.status_id = data.get('status_id')

        setor_destino = Setor.query.get(c.setor_id)
        if setor_destino:
            nome_setor = setor_destino.nome.strip()
            if nome_setor == "Produção":
                status_alvo = Status.query.filter_by(nome="Em acabamento").first()
                if status_alvo: c.status_id = status_alvo.id
            elif nome_setor == "Pronto para entrega":
                status_alvo = Status.query.filter_by(nome="Expedição").first()
                if status_alvo: c.status_id = status_alvo.id

        db.session.commit()
        atualizar_versao()
        if setor_destino: notificar_status_n8n(c, setor_destino.nome)
        return jsonify({'success': True})
    return jsonify({'error': 'Erro'}), 404

@app.route('/arquivar/<int:id>', methods=['POST'])
@login_required
def arquivar(id):
    if not current_user.is_admin: return jsonify({'error': 'Negado'}), 403
    c = Card.query.get(id)
    if c: 
        c.is_archived = True
        db.session.commit()
        atualizar_versao()
        return jsonify({'success': True})
    return jsonify({'error': 'Erro'}), 404

@app.route('/excluir/<int:id>', methods=['POST'])
@login_required
def excluir(id):
    if not current_user.is_admin: return jsonify({'error': 'Negado'}), 403
    db.session.delete(Card.query.get(id))
    db.session.commit()
    atualizar_versao()
    return jsonify({'success': True})

@app.route('/configuracoes')
@login_required
def configuracoes():
    if not current_user.is_admin: return redirect(url_for('index'))
    setores = Setor.query.order_by(Setor.ordem).all()
    lista_status = Status.query.order_by(Status.ordem).all() 
    upload_folder = os.path.join(app.root_path, 'static', 'uploads')
    total_size = 0
    total_files = 0
    if os.path.exists(upload_folder):
        for path, dirs, files in os.walk(upload_folder):
            for f in files:
                fp = os.path.join(path, f)
                total_size += os.path.getsize(fp)
                total_files += 1
    size_mb = round(total_size / (1024 * 1024), 2)
    return render_template('configuracoes.html', setores=setores, lista_status=lista_status, user=current_user, size_mb=size_mb, total_files=total_files)

@app.route('/setor/adicionar', methods=['POST'])
@login_required
def adicionar_setor():
    if not current_user.is_admin: return "Negado", 403
    u = Setor.query.order_by(Setor.ordem.desc()).first()
    mostrar = request.form.get('mostrar_no_kanban') == 'on'
    novo_setor = Setor(nome=request.form.get('nome'), ordem=(u.ordem + 1) if u else 1, mostrar_no_kanban=mostrar)
    db.session.add(novo_setor)
    db.session.commit()
    atualizar_versao()
    return redirect(url_for('configuracoes'))

@app.route('/setor/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_setor(id):
    s = Setor.query.get(id)
    if s and not s.cards: 
        db.session.delete(s)
        db.session.commit()
        atualizar_versao()
    return redirect(url_for('configuracoes'))

@app.route('/setor/editar/<int:id>', methods=['POST'])
@login_required
def editar_setor_config(id):
    if not current_user.is_admin: return "Negado", 403
    s = Setor.query.get(id)
    if s:
        s.nome = request.form.get('nome')
        s.mostrar_no_kanban = request.form.get('mostrar_no_kanban') == 'on'
        db.session.commit()
        atualizar_versao()
    return redirect(url_for('configuracoes'))

@app.route('/setor/reordenar/<int:id>/<string:direcao>', methods=['POST'])
@login_required
def reordenar_setor(id, direcao):
    if not current_user.is_admin: return "Negado", 403
    s_atual = Setor.query.get(id)
    if not s_atual: return redirect(url_for('configuracoes'))
    
    if direcao == 'subir':
        s_alvo = Setor.query.filter(Setor.ordem < s_atual.ordem).order_by(Setor.ordem.desc()).first()
    else:
        s_alvo = Setor.query.filter(Setor.ordem > s_atual.ordem).order_by(Setor.ordem.asc()).first()
        
    if s_alvo:
        s_atual.ordem, s_alvo.ordem = s_alvo.ordem, s_atual.ordem
        db.session.commit()
        atualizar_versao()
    return redirect(url_for('configuracoes'))

@app.route('/status/editar/<int:id>', methods=['POST'])
@login_required
def editar_status_config(id):
    if not current_user.is_admin: return "Negado", 403
    st = Status.query.get(id)
    if st:
        st.nome = request.form.get('nome')
        st.cor = request.form.get('cor')
        db.session.commit()
        atualizar_versao()
    return redirect(url_for('configuracoes'))

@app.route('/status/ordenar_alfa', methods=['POST'])
@login_required
def ordenar_status_alfa():
    if not current_user.is_admin: return "Negado", 403
    lista = Status.query.order_by(Status.nome).all()
    for idx, st in enumerate(lista): st.ordem = idx + 1
    db.session.commit()
    atualizar_versao()
    return redirect(url_for('configuracoes'))

@app.route('/status/adicionar', methods=['POST'])
@login_required
def adicionar_status():
    if not current_user.is_admin: return "Negado", 403
    u = Status.query.order_by(Status.ordem.desc()).first()
    db.session.add(Status(nome=request.form.get('nome'), cor=request.form.get('cor'), ordem=(u.ordem+1) if u else 1))
    db.session.commit()
    return redirect(url_for('configuracoes'))

@app.route('/status/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_status(id):
    s = Status.query.get(id)
    if s: 
        db.session.delete(s)
        db.session.commit()
    return redirect(url_for('configuracoes'))

@app.route('/chat/limpar', methods=['POST'])
@login_required
def limpar_chat():
    if not current_user.is_admin: return jsonify({'error':'Negado'}), 403
    data = request.get_json()
    tipo = data.get('tipo', 'global')
    dest = data.get('dest')

    query = Mensagem.query
    if tipo == 'global': query = query.filter_by(tipo_chat='global')
    elif tipo == 'direto':
        query = query.filter(db.or_(
            db.and_(Mensagem.remetente == current_user.username, Mensagem.destinatario == dest),
            db.and_(Mensagem.remetente == dest, Mensagem.destinatario == current_user.username)
        ))
    elif tipo == 'setor': query = query.filter_by(tipo_chat='setor', setor_id=dest)

    query.delete(synchronize_session=False)
    db.session.commit()
    atualizar_versao() 
    return jsonify({'success':True})

@app.route('/chat/excluir_msg/<int:id>', methods=['POST'])
@login_required
def excluir_msg(id):
    msg = Mensagem.query.get(id)
    if msg and (msg.remetente == current_user.username or current_user.is_admin):
        db.session.delete(msg)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Negado'}), 403

@app.route('/chat/editar_msg/<int:id>', methods=['POST'])
@login_required
def editar_msg(id):
    msg = Mensagem.query.get(id)
    data = request.get_json()
    novo_texto = data.get('texto')
    if msg and msg.remetente == current_user.username and novo_texto:
        msg.texto = novo_texto + " (editado)"
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Negado'}), 403

@app.route('/api/arquivados')
@login_required
def api_arquivados():
    cards = Card.query.filter_by(is_archived=True).order_by(Card.id.desc()).limit(50).all()
    return jsonify([{'id':c.id, 'titulo':c.titulo, 'cliente':c.cliente, 'data':c.data_criacao} for c in cards])

@app.route('/desarquivar/<int:card_id>', methods=['POST'])
@login_required
def desarquivar_card(card_id):
    if not current_user.is_admin: return jsonify({'error':'Negado'}), 403
    c = Card.query.get(card_id)
    if c: 
        c.is_archived = False
        db.session.commit()
        atualizar_versao()
        return jsonify({'success':True})
    return jsonify({'error':'Erro'}), 404

@app.route('/api/limpar_imagens', methods=['POST'])
@login_required
def limpar_imagens():
    if current_user.funcao != 'admin': return jsonify({'error': 'Não autorizado'}), 403
    dias = int(request.json.get('dias', 60)) 
    data_limite_obj = datetime.now() - timedelta(days=dias)
    cards_arquivados = Card.query.filter_by(is_archived=True).all()
    imagens_apagadas = 0
    espaco_liberado = 0
    upload_folder = os.path.join(app.root_path, 'static', 'uploads')
    for card in cards_arquivados:
        try:
            if card.imagem_path:
                caminho_arquivo = os.path.join(upload_folder, card.imagem_path)
                if os.path.exists(caminho_arquivo):
                    timestamp_arquivo = os.path.getmtime(caminho_arquivo)
                    data_arquivo = datetime.fromtimestamp(timestamp_arquivo)
                    if data_arquivo < data_limite_obj:
                        tamanho = os.path.getsize(caminho_arquivo)
                        os.remove(caminho_arquivo)
                        card.imagem_path = None
                        imagens_apagadas += 1
                        espaco_liberado += tamanho
        except Exception as e: print(f"Erro ao limpar card {card.id}: {e}")
    db.session.commit()
    mb_liberados = round(espaco_liberado / (1024 * 1024), 2)
    return jsonify({'success': True, 'qtd': imagens_apagadas, 'mb': mb_liberados})

@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin: return redirect(url_for('index'))
    start_date = request.args.get('start', '')
    end_date = request.args.get('end', '')
    setor_id = request.args.get('setor', '')
    cliente_busca = request.args.get('cliente', '').strip()

    s_date_obj = datetime.strptime(start_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0) if start_date else None
    e_date_obj = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59) if end_date else None

    hist_query = HistoricoCard.query
    if s_date_obj: hist_query = hist_query.filter(HistoricoCard.data_registro >= s_date_obj)
    if e_date_obj: hist_query = hist_query.filter(HistoricoCard.data_registro <= e_date_obj)
    historico = hist_query.all()

    all_cards = Card.query.all()
    filtered_cards = []
    current_year = datetime.now().year

    for c in all_cards:
        keep = True
        if c.data_criacao:
            try:
                card_date = datetime.strptime(f"{c.data_criacao} {current_year}", "%d/%m %H:%M %Y")
                if s_date_obj and card_date < s_date_obj: keep = False
                if e_date_obj and card_date > e_date_obj: keep = False
            except: pass
        
        if setor_id:
            passou_pelo_setor = any(h.card_id == c.id and str(h.setor_id) == setor_id for h in historico)
            esta_no_setor = str(c.setor_id) == setor_id
            if not (passou_pelo_setor or esta_no_setor):
                keep = False
                
        # FILTRO DE CLIENTE (Não diferencia maiúsculas de minúsculas)
        if cliente_busca:
            if not c.cliente or cliente_busca.lower() not in c.cliente.lower():
                keep = False

        if keep and not c.is_archived:
            filtered_cards.append(c)

    all_status = Status.query.all()
    all_setores = Setor.query.order_by(Setor.ordem).all()
    
    total = len(filtered_cards)
    atrasados = 0
    para_hoje = 0
    hoje_str = datetime.now().strftime('%Y-%m-%d')

    for c in filtered_cards:
        if c.prazo:
            if c.prazo < hoje_str: atrasados += 1
            elif c.prazo == hoje_str: para_hoje += 1

    labels_status, values_status, colors_status = [], [], []
    for st in all_status:
        count = sum(1 for c in filtered_cards if c.status_id == st.id)
        if count > 0:
            labels_status.append(st.nome)
            values_status.append(count)
            colors_status.append(st.cor)

    labels_setor, values_setor = [], []
    for s in all_setores:
        labels_setor.append(s.nome)
        cards_passaram = set([h.card_id for h in historico if h.setor_id == s.id and any(fc.id == h.card_id for fc in filtered_cards)])
        cards_atuais = set([c.id for c in filtered_cards if c.setor_id == s.id])
        total_setor = cards_passaram.union(cards_atuais)
        values_setor.append(len(total_setor))

    return render_template('dashboard.html', user=current_user, total=total, atrasados=atrasados, para_hoje=para_hoje,
                           labels_status=labels_status, values_status=values_status, colors_status=colors_status, 
                           labels_setor=labels_setor, values_setor=values_setor, start_date=start_date, end_date=end_date,
                           cards=filtered_cards, all_setores=all_setores, setor_selecionado=setor_id, cliente_busca=cliente_busca)

@app.route('/estoque')
@login_required
def estoque():
    if not current_user.is_admin and not current_user.acesso_estoque:
        flash('Acesso negado ao estoque.')
        return redirect(url_for('index'))
    materiais = Material.query.order_by(Material.categoria, Material.nome).all()
    return render_template('estoque.html', materiais=materiais, user=current_user)

@app.route('/estoque/adicionar_item', methods=['POST'])
@login_required
def adicionar_item_estoque():
    if not current_user.is_admin: return "Negado", 403
    novo = Material(
        nome=request.form.get('nome'), 
        categoria=request.form.get('categoria', 'Geral / Outros'),
        unidade=request.form.get('unidade'), 
        quantidade=float(request.form.get('quantidade')), 
        minimo=float(request.form.get('minimo'))
    )
    db.session.add(novo)
    db.session.add(Movimentacao(material=novo, tipo='ENTRADA', quantidade=novo.quantidade, usuario=current_user.username))
    db.session.commit()
    return redirect(url_for('estoque'))

@app.route('/estoque/movimentar', methods=['POST'])
@login_required
def movimentar_estoque():
    if not current_user.is_admin and not current_user.acesso_estoque: return "Negado", 403
    m = Material.query.get(request.form.get('id'))
    qtd = float(request.form.get('quantidade'))
    tipo = request.form.get('tipo')
    dest = request.form.get('destino')
    if m:
        if tipo == 'SAIDA': 
            m.quantidade -= qtd
            user_reg = f"{current_user.username} ➔ {dest}"
        else: 
            m.quantidade += qtd
            user_reg = current_user.username
        db.session.add(Movimentacao(material=m, tipo=tipo, quantidade=qtd, usuario=user_reg))
        db.session.commit()
    return redirect(url_for('estoque'))

@app.route('/estoque/excluir_item/<int:id>', methods=['POST'])
@login_required
def excluir_item_estoque(id):
    if not current_user.is_admin: return "Negado", 403
    m = Material.query.get(id)
    if m: 
        db.session.delete(m)
        db.session.commit()
    return redirect(url_for('estoque'))

@app.route('/estoque/historico/<int:id>')
@login_required
def historico_estoque(id):
    movs = Movimentacao.query.filter_by(material_id=id).order_by(Movimentacao.data.desc()).limit(20).all()
    return jsonify([{'tipo':m.tipo, 'qtd':m.quantidade, 'usuario':m.usuario, 'data':m.data.strftime("%d/%m %H:%M")} for m in movs])

# --- ROTAS DA AGENDA ---
@app.route('/agenda')
@login_required
def agenda():
    setores = Setor.query.order_by(Setor.ordem).all()
    return render_template('agenda.html', user=current_user, setores=setores)

@app.route('/api/eventos')
@login_required
def api_eventos():
    eventos = Evento.query.all()
    eventos_filtrados = []
    
    user_setores = [str(s.id) for s in current_user.acessos]
    
    for e in eventos:
        if e.visibilidade == 'todos':
            eventos_filtrados.append(e) 
            
        elif e.visibilidade == 'admin':
            if current_user.is_admin:
                eventos_filtrados.append(e) 
                
        elif e.visibilidade == 'privado':
            if e.criado_por == current_user.username:
                eventos_filtrados.append(e) 
                
        else:
            if current_user.is_admin:
                eventos_filtrados.append(e) 
            elif e.visibilidade:
                setores_evento = e.visibilidade.split(',')
                if any(s in setores_evento for s in user_setores):
                    eventos_filtrados.append(e)
                    
    return jsonify([{
        'id': e.id,
        'title': e.titulo,
        'start': e.inicio,
        'end': e.fim,
        'color': e.cor,
        'extendedProps': {'criado_por': e.criado_por, 'visibilidade': e.visibilidade}
    } for e in eventos_filtrados])

@app.route('/api/evento/adicionar', methods=['POST'])
@login_required
def adicionar_evento():
    if not current_user.is_admin: return jsonify({'error': 'Negado'}), 403
    data = request.get_json()
    e = Evento(
        titulo=data.get('titulo'),
        inicio=data.get('inicio'),
        fim=data.get('fim'),
        cor=data.get('cor', '#0079bf'),
        criado_por=current_user.username,
        visibilidade=data.get('visibilidade', 'todos') 
    )
    db.session.add(e)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/evento/editar/<int:id>', methods=['POST'])
@login_required
def editar_evento(id):
    if not current_user.is_admin: return jsonify({'error': 'Negado'}), 403
    data = request.get_json()
    e = Evento.query.get(id)
    if e:
        if 'titulo' in data: e.titulo = data.get('titulo')
        if 'inicio' in data: e.inicio = data.get('inicio')
        if 'fim' in data: e.fim = data.get('fim')
        if 'cor' in data: e.cor = data.get('cor')
        if 'visibilidade' in data: e.visibilidade = data.get('visibilidade')
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Não encontrado'}), 404

@app.route('/api/evento/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_evento(id):
    if not current_user.is_admin: return jsonify({'error': 'Negado'}), 403
    e = Evento.query.get(id)
    if e:
        db.session.delete(e)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Não encontrado'}), 404

if __name__ == '__main__':
    if not os.path.exists(os.path.join(basedir, 'printflow.db')):
        with app.app_context():
            db.create_all()
            if not Usuario.query.filter_by(username='admin').first():
                u = Usuario(username='admin', funcao='admin')
                u.set_password('admin')
                db.session.add(u)
            if not Setor.query.first(): 
                db.session.add(Setor(nome="Atendimento", ordem=1))
                db.session.add(Setor(nome="Produção", ordem=2))
                db.session.add(Setor(nome="Expedição", ordem=3))
            if not Status.query.first(): 
                db.session.add(Status(nome="Pendente", cor="gray", ordem=1))
                db.session.add(Status(nome="Concluído", cor="green", ordem=2))
            db.session.commit()
    else:
        with app.app_context(): 
            db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)