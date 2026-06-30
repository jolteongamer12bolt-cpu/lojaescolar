import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'chave_secreta_fazenda_sao_bento'

UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def inicializar_banco():
    conn = sqlite3.connect('usuarios.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            serie TEXT NOT NULL,
            senha TEXT NOT NULL,
            foto TEXT,
            codigo_aluno TEXT,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            produto_nome TEXT NOT NULL,
            produto_preco REAL NOT NULL,
            forma_pagamento TEXT NOT NULL,
            comprovante TEXT,
            nome_aluno TEXT NOT NULL,
            serie TEXT NOT NULL,
            sala TEXT NOT NULL,
            turno TEXT NOT NULL,
            data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            entregue INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            preco REAL NOT NULL,
            categoria TEXT NOT NULL,
            imagem TEXT
        )
    ''')
    
    # Tabela de Amizades
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS amizades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            remetente_id INTEGER NOT NULL,
            destinatario_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pendente',
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

inicializar_banco()

# ==================== ROTAS ====================

@app.route('/')
def loja():
    usuario_nome = "Visitante"
    usuario_status = "Não conectado"
    usuario_avatar = "👤"
    logado = False
    usuario_serie = ""
    usuario_codigo = ""
    is_admin = 0

    if 'usuario_id' in session:
        conn = sqlite3.connect('usuarios.db')
        conn.row_factory = sqlite3.Row
        user_db = conn.execute('SELECT * FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
        conn.close()
        if user_db:
            usuario_nome = user_db['nome']
            usuario_status = user_db['serie']
            usuario_serie = user_db['serie']
            try:
                usuario_codigo = user_db['codigo_aluno'] or ""
            except:
                usuario_codigo = ""
            try:
                is_admin = user_db['is_admin'] or 0
            except:
                is_admin = 0
            logado = True
            if user_db['foto']:
                caminho_foto = url_for('static', filename=f'uploads/{user_db["foto"]}')
                usuario_avatar = f'<img src="{caminho_foto}">'

    conn = sqlite3.connect('usuarios.db')
    conn.row_factory = sqlite3.Row
    produtos_db = conn.execute('SELECT * FROM produtos ORDER BY categoria, id').fetchall()
    conn.close()

    lanches = [p for p in produtos_db if p['categoria'] == 'Lanches']
    contas_jogos = [p for p in produtos_db if p['categoria'] == 'Contas de Jogos']

    if logado:
        painel_cadastro_login = f"""
        <div class="panel profile-box">
            <div class="big-avatar">{usuario_avatar}</div>
            <h4>{usuario_nome}</h4>
            <p style="color: #b31010; font-weight: bold; font-size: 13px;">Série: {usuario_status}</p>
            <p style="color: #4ade80; font-size: 12px;">ID: {usuario_codigo}</p>
        </div>
        """
        menu_sair = '<a href="/sair" class="nav-item sair">🚪 Sair da Conta</a>'
    else:
        painel_cadastro_login = """
        <div class="panel">
            <h3>Entrar na Conta</h3>
            <form action="/login" method="POST">
                <div class="form-group">
                    <label>Email</label>
                    <input type="email" name="email" class="form-control" required>
                </div>
                <div class="form-group">
                    <label>Senha</label>
                    <input type="password" name="senha" class="form-control" required>
                </div>
                <button type="submit" class="btn-submit">Entrar</button>
            </form>
            <a href="/cadastro" class="toggle-link">Não tem conta? Cadastre-se aqui</a>
        </div>
        """
        menu_sair = ""

    return render_template('loja.html', 
                           usuario_nome=usuario_nome, 
                           usuario_status=usuario_status,
                           usuario_serie=usuario_serie,
                           usuario_codigo=usuario_codigo,
                           usuario_avatar=usuario_avatar,
                           lanches=lanches,
                           contas_jogos=contas_jogos,
                           painel_cadastro_login=painel_cadastro_login,
                           menu_sair=menu_sair,
                           is_admin=is_admin)

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'GET':
        return render_template('cadastro.html')
    
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip()
    serie = request.form.get('serie', '').strip()
    senha = request.form.get('senha', '')
    foto = request.files.get('foto')

    nome_foto = None
    if foto and foto.filename != '':
        extensao = foto.filename.rsplit('.', 1)[-1].lower()
        nome_foto = f"perfil_{email.replace('@', '_').replace('.', '_')}.{extensao}"
        foto.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_foto))

    try:
        conn = sqlite3.connect('usuarios.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO usuarios (nome, email, serie, senha, foto) 
            VALUES (?, ?, ?, ?, ?)
        ''', (nome, email, serie, senha, nome_foto))
        
        usuario_id = cursor.lastrowid
        codigo_aluno = f"FSB-{str(usuario_id).zfill(4)}"
        cursor.execute('UPDATE usuarios SET codigo_aluno = ? WHERE id = ?', (codigo_aluno, usuario_id))
        conn.commit()
        conn.close()
        
        return f"<script>alert('Cadastro realizado com sucesso! Seu ID: {codigo_aluno}'); window.location.href='/';</script>"
    except sqlite3.IntegrityError:
        return "<script>alert('Este e-mail já está cadastrado.'); window.location.href='/cadastro';</script>"

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email', '').strip()
    senha = request.form.get('senha', '')

    conn = sqlite3.connect('usuarios.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    usuario = cursor.execute('SELECT * FROM usuarios WHERE email = ? AND senha = ?', (email, senha)).fetchone()
    conn.close()

    if usuario:
        session['usuario_id'] = usuario['id']
        return f"<script>alert('Bem-vindo, {usuario['nome']}!'); window.location.href='/';</script>"
    else:
        return "<script>alert('E-mail ou senha incorretos.'); window.location.href='/';</script>"

@app.route('/sair')
def sair():
    session.clear()
    return redirect(url_for('loja'))

# ==================== ÁREA ADMIN ====================

@app.route('/admin')
def admin():
    if 'usuario_id' not in session:
        return redirect(url_for('loja'))
    
    conn = sqlite3.connect('usuarios.db')
    conn.row_factory = sqlite3.Row
    user = conn.execute('SELECT is_admin FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
    
    if not user or user['is_admin'] != 1:
        conn.close()
        return "<h2 style='color:red; text-align:center; margin-top:100px;'>Acesso negado.</h2>"
    
    pedidos = conn.execute('''
        SELECT p.*, u.nome as nome_completo, u.email, u.codigo_aluno 
        FROM pedidos p
        LEFT JOIN usuarios u ON p.usuario_id = u.id
        ORDER BY p.data_pedido DESC
    ''').fetchall()
    conn.close()
    return render_template('admin.html', pedidos=pedidos)

@app.route('/entregar/<int:pedido_id>', methods=['POST'])
def entregar(pedido_id):
    if 'usuario_id' not in session:
        return redirect(url_for('loja'))
    conn = sqlite3.connect('usuarios.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE pedidos SET entregue = 1 WHERE id = ?', (pedido_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

# ==================== PERFIL ====================

@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('loja'))
    
    conn = sqlite3.connect('usuarios.db')
    conn.row_factory = sqlite3.Row
    usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        serie = request.form.get('serie')
        
        cursor = conn.cursor()
        cursor.execute('UPDATE usuarios SET nome = ?, serie = ? WHERE id = ?', 
                       (nome, serie, session['usuario_id']))
        
        foto = request.files.get('foto')
        if foto and foto.filename != '':
            extensao = foto.filename.rsplit('.', 1)[-1].lower()
            nome_foto = f"perfil_{session['usuario_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{extensao}"
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_foto))
            cursor.execute('UPDATE usuarios SET foto = ? WHERE id = ?', 
                           (nome_foto, session['usuario_id']))
        
        conn.commit()
        conn.close()
        return redirect(url_for('perfil'))
    
    conn.close()
    return render_template('perfil.html', usuario=usuario)

# ==================== SISTEMA DE AMIZADE ====================

@app.route('/amizades')
def amizades():
    if 'usuario_id' not in session:
        return redirect(url_for('loja'))
    
    conn = sqlite3.connect('usuarios.db')
    conn.row_factory = sqlite3.Row
    
    pedidos_pendentes = conn.execute('''
        SELECT a.*, u.nome, u.codigo_aluno 
        FROM amizades a
        JOIN usuarios u ON a.remetente_id = u.id
        WHERE a.destinatario_id = ? AND a.status = 'pendente'
    ''', (session['usuario_id'],)).fetchall()
    
    amigos = conn.execute('''
        SELECT u.id, u.nome, u.codigo_aluno, u.serie
        FROM amizades a
        JOIN usuarios u ON (
            (a.remetente_id = u.id AND a.destinatario_id = ?) OR 
            (a.destinatario_id = u.id AND a.remetente_id = ?)
        )
        WHERE a.status = 'aceito'
    ''', (session['usuario_id'], session['usuario_id'])).fetchall()
    
    conn.close()
    return render_template('amizades.html', pedidos_pendentes=pedidos_pendentes, amigos=amigos)

@app.route('/enviar_pedido_amizade', methods=['POST'])
def enviar_pedido_amizade():
    if 'usuario_id' not in session:
        return redirect(url_for('loja'))
    
    amigo_id = request.form.get('amigo_id')
    
    if not amigo_id or int(amigo_id) == session['usuario_id']:
        return "<script>alert('ID inválido!'); window.location.href='/amizades';</script>"
    
    conn = sqlite3.connect('usuarios.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id FROM amizades 
        WHERE (remetente_id = ? AND destinatario_id = ?) 
           OR (remetente_id = ? AND destinatario_id = ?)
    ''', (session['usuario_id'], amigo_id, amigo_id, session['usuario_id']))
    
    if cursor.fetchone():
        conn.close()
        return "<script>alert('Já existe um pedido ou amizade com esse usuário.'); window.location.href='/amizades';</script>"
    
    cursor.execute('''
        INSERT INTO amizades (remetente_id, destinatario_id, status)
        VALUES (?, ?, 'pendente')
    ''', (session['usuario_id'], amigo_id))
    conn.commit()
    conn.close()
    
    return "<script>alert('Pedido de amizade enviado!'); window.location.href='/amizades';</script>"

@app.route('/aceitar_amizade/<int:amizade_id>', methods=['POST'])
def aceitar_amizade(amizade_id):
    if 'usuario_id' not in session:
        return redirect(url_for('loja'))
    
    conn = sqlite3.connect('usuarios.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE amizades SET status = "aceito" WHERE id = ? AND destinatario_id = ?', 
                   (amizade_id, session['usuario_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('amizades'))

@app.route('/recusar_amizade/<int:amizade_id>', methods=['POST'])
def recusar_amizade(amizade_id):
    if 'usuario_id' not in session:
        return redirect(url_for('loja'))
    
    conn = sqlite3.connect('usuarios.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM amizades WHERE id = ? AND destinatario_id = ?', 
                   (amizade_id, session['usuario_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('amizades'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)