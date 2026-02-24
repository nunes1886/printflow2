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
    
    # Permissão específica para ver/movimentar estoque
    acesso_estoque = db.Column(db.Boolean, default=False)
    
    # RELACIONAMENTO: Lista de setores que este usuário pode ver
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
    cards = db.relationship('Card', backref='setor_ref', lazy=True, order_by='Card.id')

class Status(db.Model):
    __tablename__ = 'status'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    cor = db.Column(db.String(20), default='#CCCCCC')

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
    
    # RELACIONAMENTO: Comentários do Card (NOVO)
    comentarios = db.relationship('Comentario', backref='card', lazy=True, cascade="all, delete-orphan")

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
    usuario = db.Column(db.String(100))
    texto = db.Column(db.Text)
    data_envio = db.Column(db.String(50))

class Material(db.Model):
    __tablename__ = 'materiais'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
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

@login_manager.user_loader
def load_user(user_id): return Usuario.query.get(int(user_id))

def salvar_imagem_base64(base64_string):
    if not base64_string: return None
    try:
        header, encoded = base64_string.split(",", 1); data = base64.b64decode(encoded)
        filename = f"{uuid.uuid4()}.png"
        folder = os.path.join(basedir, 'static', 'uploads')
        if not os.path.exists(folder): os.makedirs(folder)
        filepath = os.path.join(folder, filename)
        with open(filepath, "wb") as f: f.write(data)
        return filename
    except: return None


# --- INTEGRAÇÃO N8N ---
def notificar_status_n8n(card, nome_coluna):
    url_n8n = "http://localhost:5678/webhook-test/atualizacao-pedido" 
    
    payload = {
        "cliente": card.cliente or "Cliente",
        "telefone": "5579999999999", 
        "pedido": str(card.id),
        "produto": card.titulo,
        "etapa_atual": nome_coluna  # <--- Agora enviamos a coluna
    }
    
    try:
        requests.post(url_n8n, json=payload, timeout=3)
    except Exception as e:
        print(f"Erro ao notificar n8n: {e}")

# --- ROTAS PRINCIPAIS ---

@app.route('/verificar_atualizacao')
def verificar_atualizacao():
    ultimo_msg = Mensagem.query.order_by(Mensagem.id.desc()).first()
    msg_id = ultimo_msg.id if ultimo_msg else 0
    last_card = Card.query.order_by(Card.id.desc()).first()
    card_id = last_card.id if last_card else 0
    return jsonify({'timestamp': ULTIMA_ATUALIZACAO, 'chat_id': msg_id, 'last_card_id': card_id})

@app.route('/chat/enviar', methods=['POST'])
@login_required
def enviar_mensagem():
    data = request.get_json()
    db.session.add(Mensagem(usuario=current_user.username, texto=data.get('texto'), data_envio=datetime.now().strftime("%H:%M")))
    db.session.commit()
    return jsonify({'success': True})

@app.route('/chat/listar')
@login_required
def listar_mensagens():
    msgs = Mensagem.query.order_by(Mensagem.id.asc()).all()[-50:]
    return jsonify([{'usuario': m.usuario, 'texto': m.texto, 'hora': m.data_envio, 'eu_mesmo': m.usuario == current_user.username} for m in msgs])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = Usuario.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user); return redirect(url_for('index'))
        flash('Erro no login.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    todos_setores = Setor.query.order_by(Setor.ordem).all()
    lista_status = Status.query.all()
    
    setores_visiveis = []
    
    # 1. Filtra permissões
    if current_user.is_admin:
        setores_visiveis = todos_setores
    else:
        if len(current_user.acessos) > 0:
            ids_permitidos = [s.id for s in current_user.acessos]
            setores_visiveis = [s for s in todos_setores if s.id in ids_permitidos]
        else:
            setores_visiveis = todos_setores

    # 2. ORDENAÇÃO INTELIGENTE (Prioridade no Semáforo)
    # Ordena: Com Prazo primeiro (0), Sem Prazo depois (1).
    # Dentro dos com prazo: Data menor (mais urgente) primeiro.
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
    
    # Permissão do estoque
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
            flash('Usuário já existe.'); return redirect(url_for('usuarios'))
        u = Usuario(username=nome, funcao=nova_funcao)
        u.set_password(senha if senha else '1234')
        u.acesso_estoque = (acesso_estoque_check == 'on')
        db.session.add(u)
    
    u.acessos = [] 
    for sid in setores_ids:
        setor = Setor.query.get(int(sid))
        if setor:
            u.acessos.append(setor)
            
    db.session.commit()
    return redirect(url_for('usuarios'))

@app.route('/usuario/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_usuario(id):
    if not current_user.is_admin or id == current_user.id: return jsonify({'error': 'Erro'}), 400
    db.session.delete(Usuario.query.get(id))
    db.session.commit()
    return jsonify({'success': True})

# --- KANBAN API ---
@app.route('/api/card/<int:card_id>')
@login_required
def get_card_data(card_id):
    c = Card.query.get_or_404(card_id)
    return jsonify({'id':c.id, 'titulo':c.titulo, 'descricao':c.descricao, 'cliente':c.cliente, 'setor_id':c.setor_id, 'status_id':c.status_id, 'imagem_path':c.imagem_path, 'created_by':c.created_by, 'prazo':c.prazo})

# --- ROTAS DE COMENTÁRIOS (NOVO) ---
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
    db.session.add(c); db.session.commit()
    return jsonify({'success': True})

@app.route('/adicionar', methods=['POST'])
@login_required
def adicionar():
    if not current_user.is_admin: return "Negado", 403
    img = salvar_imagem_base64(request.form.get('imagem_base64'))
    s = Setor.query.order_by(Setor.ordem).first()
    st = Status.query.first()
    c = Card(titulo=request.form.get('titulo'), cliente=request.form.get('cliente'), descricao=request.form.get('descricao'), data_criacao=datetime.now().strftime("%d/%m %H:%M"), setor_id=s.id, status_id=st.id, imagem_path=img, created_by=current_user.username, prazo=request.form.get('prazo'))
    db.session.add(c); db.session.commit(); atualizar_versao()
    return redirect(url_for('index'))

@app.route('/editar', methods=['POST'])
@login_required
def editar():
    c = Card.query.get(request.form.get('id'))
    if c:
        if request.form.get('status_id'): c.status_id = int(request.form.get('status_id'))
        if request.form.get('setor_id'): c.setor_id = int(request.form.get('setor_id'))
        if current_user.is_admin:
            c.titulo = request.form.get('titulo')
            c.cliente = request.form.get('cliente')
            c.descricao = request.form.get('descricao')
            c.prazo = request.form.get('prazo')
            img = salvar_imagem_base64(request.form.get('imagem_base64'))
            if img: c.imagem_path = img
        db.session.commit(); atualizar_versao()
    return redirect(url_for('index'))

@app.route('/mover', methods=['POST'])
@login_required
def mover():
    data = request.get_json()
    c = Card.query.get(data.get('id'))
    
    if c:
        novo_setor_id = data.get('setor_id')
        
        # Atualiza setor e status padrão vindo do front
        if 'setor_id' in data: c.setor_id = novo_setor_id
        if 'status_id' in data: c.status_id = data.get('status_id')

        # --- AUTOMAÇÃO DE STATUS (Lógica Nova) ---
        # Busca o nome do setor para onde o card foi movido
        setor_destino = Setor.query.get(novo_setor_id)

        if setor_destino:
            nome_setor = setor_destino.nome.strip() # Remove espaços extras por segurança

            # Regra 1: Se foi para "Produção" -> Muda Status para "Em acabamento"
            if nome_setor == "Produção":
                status_alvo = Status.query.filter_by(nome="Em acabamento").first()
                if status_alvo:
                    c.status_id = status_alvo.id
            
            # Regra 2: Se foi para "Pronto para entrega" -> Muda Status para "Expedição"
            elif nome_setor == "Pronto para entrega":
                status_alvo = Status.query.filter_by(nome="Expedição").first()
                if status_alvo:
                    c.status_id = status_alvo.id

        db.session.commit()
        atualizar_versao()

        if setor_destino:
            # Enviamos o nome da coluna para o n8n (ex: "Impressão", "Expedição")
            notificar_status_n8n(c, setor_destino.nome)

        return jsonify({'success': True})
    
    return jsonify({'error': 'Erro'}), 404



@app.route('/arquivar/<int:id>', methods=['POST'])
@login_required
def arquivar(id):
    if not current_user.is_admin: return jsonify({'error': 'Negado'}), 403
    c = Card.query.get(id)
    if c: c.is_archived = True; db.session.commit(); atualizar_versao(); return jsonify({'success': True})
    return jsonify({'error': 'Erro'}), 404

@app.route('/excluir/<int:id>', methods=['POST'])
@login_required
def excluir(id):
    if not current_user.is_admin: return jsonify({'error': 'Negado'}), 403
    db.session.delete(Card.query.get(id)); db.session.commit(); atualizar_versao(); return jsonify({'success': True})

@app.route('/configuracoes')
@login_required
def configuracoes():
    if not current_user.is_admin: return redirect(url_for('index'))
    setores = Setor.query.order_by(Setor.ordem).all(); lista_status = Status.query.all()
    upload_folder = os.path.join(app.root_path, 'static', 'uploads')
    total_size = 0; total_files = 0
    if os.path.exists(upload_folder):
        for path, dirs, files in os.walk(upload_folder):
            for f in files:
                fp = os.path.join(path, f); total_size += os.path.getsize(fp); total_files += 1
    size_mb = round(total_size / (1024 * 1024), 2)
    return render_template('configuracoes.html', setores=setores, lista_status=lista_status, user=current_user, size_mb=size_mb, total_files=total_files)

@app.route('/setor/adicionar', methods=['POST'])
@login_required
def adicionar_setor():
    if not current_user.is_admin: return "Negado", 403
    u = Setor.query.order_by(Setor.ordem.desc()).first()
    db.session.add(Setor(nome=request.form.get('nome'), ordem=(u.ordem + 1) if u else 1)); db.session.commit(); atualizar_versao()
    return redirect(url_for('configuracoes'))

@app.route('/setor/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_setor(id):
    s = Setor.query.get(id)
    if s and not s.cards: db.session.delete(s); db.session.commit(); atualizar_versao()
    return redirect(url_for('configuracoes'))

@app.route('/status/adicionar', methods=['POST'])
@login_required
def adicionar_status():
    if not current_user.is_admin: return "Negado", 403
    db.session.add(Status(nome=request.form.get('nome'), cor=request.form.get('cor'))); db.session.commit()
    return redirect(url_for('configuracoes'))

@app.route('/status/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_status(id):
    s = Status.query.get(id)
    if s: db.session.delete(s); db.session.commit()
    return redirect(url_for('configuracoes'))

@app.route('/chat/limpar', methods=['POST'])
@login_required
def limpar_chat():
    if not current_user.is_admin: return jsonify({'error':'Negado'}), 403
    Mensagem.query.delete(); db.session.commit(); atualizar_versao(); return jsonify({'success':True})

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
    if c: c.is_archived = False; db.session.commit(); atualizar_versao(); return jsonify({'success':True})
    return jsonify({'error':'Erro'}), 404

@app.route('/api/limpar_imagens', methods=['POST'])
@login_required
def limpar_imagens():
    if current_user.funcao != 'admin': return jsonify({'error': 'Não autorizado'}), 403
    dias = int(request.json.get('dias', 60)) 
    data_limite_obj = datetime.now() - timedelta(days=dias)
    cards_arquivados = Card.query.filter_by(is_archived=True).all()
    imagens_apagadas = 0; espaco_liberado = 0; upload_folder = os.path.join(app.root_path, 'static', 'uploads')
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
                        imagens_apagadas += 1; espaco_liberado += tamanho
        except Exception as e: print(f"Erro ao limpar card {card.id}: {e}")
    db.session.commit(); mb_liberados = round(espaco_liberado / (1024 * 1024), 2)
    return jsonify({'success': True, 'qtd': imagens_apagadas, 'mb': mb_liberados})

@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin: return redirect(url_for('index'))
    
    # 1. Busca todos os dados ativos
    all_cards = Card.query.filter_by(is_archived=False).all()
    all_status = Status.query.all()
    all_setores = Setor.query.order_by(Setor.ordem).all()

    # 2. Calcula KPIs (Números do Topo)
    total = len(all_cards)
    atrasados = 0
    para_hoje = 0
    hoje_str = datetime.now().strftime('%Y-%m-%d')

    for c in all_cards:
        if c.prazo:
            # Compara datas (string YYYY-MM-DD)
            if c.prazo < hoje_str:
                atrasados += 1
            elif c.prazo == hoje_str:
                para_hoje += 1

    # 3. Prepara dados para o Gráfico de Status (Pizza)
    labels_status = []
    values_status = []
    colors_status = [] # <--- A VARIÁVEL QUE FALTAVA E CAUSAVA O ERRO

    for st in all_status:
        # Conta quantos cards ativos tem nesse status
        count = Card.query.filter_by(status_id=st.id, is_archived=False).count()
        # Só adiciona no gráfico se tiver pelo menos 1 card (para não ficar poluído)
        if count > 0:
            labels_status.append(st.nome)
            values_status.append(count)
            colors_status.append(st.cor) # Pega a cor configurada no banco

    # 4. Prepara dados para o Gráfico de Setores (Barras)
    labels_setor = []
    values_setor = []

    for s in all_setores:
        # Conta cards ativos neste setor
        count = len([c for c in s.cards if not c.is_archived])
        labels_setor.append(s.nome)
        values_setor.append(count)

    # 5. Envia tudo para o HTML (Incluindo a colors_status)
    return render_template('dashboard.html', 
                           user=current_user, 
                           total=total, 
                           atrasados=atrasados, 
                           para_hoje=para_hoje,
                           labels_status=labels_status, 
                           values_status=values_status,
                           colors_status=colors_status, # <--- CORREÇÃO AQUI
                           labels_setor=labels_setor, 
                           values_setor=values_setor)

# --- ROTAS DE ESTOQUE ---

@app.route('/estoque')
@login_required
def estoque():
    # Só Admin ou quem tem 'acesso_estoque' pode entrar
    if not current_user.is_admin and not current_user.acesso_estoque:
        flash('Acesso negado ao estoque.')
        return redirect(url_for('index'))
        
    materiais = Material.query.order_by(Material.nome).all()
    return render_template('estoque.html', materiais=materiais, user=current_user)

@app.route('/estoque/adicionar_item', methods=['POST'])
@login_required
def adicionar_item_estoque():
    # CRIAR: Só Admin
    if not current_user.is_admin: return "Negado", 403
    novo = Material(nome=request.form.get('nome'), unidade=request.form.get('unidade'), quantidade=float(request.form.get('quantidade')), minimo=float(request.form.get('minimo')))
    db.session.add(novo); db.session.add(Movimentacao(material=novo, tipo='ENTRADA', quantidade=novo.quantidade, usuario=current_user.username)); db.session.commit()
    return redirect(url_for('estoque'))

@app.route('/estoque/movimentar', methods=['POST'])
@login_required
def movimentar_estoque():
    # MOVIMENTAR (Dar Baixa): Admin OU quem tem acesso
    if not current_user.is_admin and not current_user.acesso_estoque:
        return "Negado", 403
        
    m = Material.query.get(request.form.get('id')); qtd = float(request.form.get('quantidade')); tipo = request.form.get('tipo'); dest = request.form.get('destino')
    if m:
        if tipo == 'SAIDA': m.quantidade -= qtd; user_reg = f"{current_user.username} ➔ {dest}"
        else: m.quantidade += qtd; user_reg = current_user.username
        db.session.add(Movimentacao(material=m, tipo=tipo, quantidade=qtd, usuario=user_reg)); db.session.commit()
    return redirect(url_for('estoque'))

@app.route('/estoque/excluir_item/<int:id>', methods=['POST'])
@login_required
def excluir_item_estoque(id):
    # EXCLUIR: Só Admin
    if not current_user.is_admin: return "Negado", 403
    m = Material.query.get(id); 
    if m: db.session.delete(m); db.session.commit()
    return redirect(url_for('estoque'))

@app.route('/estoque/historico/<int:id>')
@login_required
def historico_estoque(id):
    movs = Movimentacao.query.filter_by(material_id=id).order_by(Movimentacao.data.desc()).limit(20).all()
    return jsonify([{'tipo':m.tipo, 'qtd':m.quantidade, 'usuario':m.usuario, 'data':m.data.strftime("%d/%m %H:%M")} for m in movs])

if __name__ == '__main__':
    if not os.path.exists(os.path.join(basedir, 'printflow.db')):
        with app.app_context():
            db.create_all()
            if not Usuario.query.filter_by(username='admin').first():
                u = Usuario(username='admin', funcao='admin'); u.set_password('admin'); db.session.add(u)
            if not Setor.query.first(): db.session.add(Setor(nome="Atendimento", ordem=1)); db.session.add(Setor(nome="Produção", ordem=2)); db.session.add(Setor(nome="Expedição", ordem=3))
            if not Status.query.first(): db.session.add(Status(nome="Pendente", cor="gray")); db.session.add(Status(nome="Concluído", cor="green"))
            db.session.commit()
    else:
        with app.app_context(): db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)