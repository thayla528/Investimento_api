from datetime import timedelta, datetime
from functools import wraps

from flask import Flask, flash, redirect, url_for, render_template, jsonify, request

from sqlalchemy import cast
from werkzeug.utils import secure_filename
# Adicione o 'select' aqui junto com os outros imports do SQLAlchemy
from sqlalchemy import Integer, func, select

import secrets # Biblioteca nativa e segura do Python


# func -> Faz contas no banco (soma, média, contagem) para o Dashboard.
# cast -> Converte tipos de dados na consulta (ex: texto para número).
# Time -> Tipo de dado do MySQL usado para isolar apenas o horário (HH:MM:SS).

import os
from dotenv import load_dotenv

from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt

from models import db_session, Usuario

# carregar variaveis de ambiente
load_dotenv()


app = Flask(__name__)
# definir a senha, em produção colocar em local seguro
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'Grafica_EPA')
jwt = JWTManager(app)

DESVIAR_PROXY = {"http": None, "https": None}

API_URL ='http://10.135.232.44:5003'

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_user = get_jwt_identity()
        print(f"current_user:{current_user}")

        try:
            # CORRIGIDO: Alterado 'Funcionario.id' para 'Funcionario.id_funcinario'
            sql = select(Usuario).where(Usuario.id_funcinario == current_user)
            usuario_existente = db_session.execute(sql).scalar()
            print(f'Usuario existente: {usuario_existente}')

            # CORRIGIDO: Alterado 'usuario_existente.papel' para 'usuario_existente.perfil'
            if usuario_existente and usuario_existente.perfil == "admin":
                return fn(*args, **kwargs)

            dado = {
                "msg": "Acesso negado: Requer privilégio de administrador"
            }
            return jsonify(dado), 403
        except Exception as e:
            print("Erro admin_required:", e)
            dado = {
                "msg": "Erro ao verificar privilégio"
            }
            return jsonify(dado), 500  # Alterado para 500 (Erro interno do servidor)

    return wrapper


@app.route('/', methods=['GET'])
def principal():
    print(f"def_identificacaoxx {str(datetime.now())}")
    dados = {
        "msg": "COD: 3jUU",
        "atualizado_em": str(datetime.now())
    }
    return jsonify(dados), 200


@app.route('/login', methods=['POST'])
def login():
    try:
        dados_entrada= request.get_json()
        if not dados_entrada:
            return jsonify({"msg": "JSON inválido"}), 400
        email = dados_entrada.get("email")

        if not email:
            return jsonify({"msg": "Email é obrigatório"}), 400
        senha = dados_entrada.get("senha")

        if not senha:
            return jsonify({"msg": "Senha é obrigatória"}), 400
        sql = select(Usuario).where(Usuario.email == email)
        usuario_existente = db_session.execute(sql).scalar()
        if not usuario_existente:
            return jsonify({"msg": "Email não cadastrado"}), 401
        if usuario_existente and usuario_existente.check_password_hash(senha):
        # criação e configurar token
            acess_token = create_access_token(
                identity=str(usuario_existente.id_funcinario),
                additional_claims={
                    "id_funcinario": str(usuario_existente.id_funcinario),
                    "nome": usuario_existente.nome,
                    "token_criado_em": str(datetime.now())
                },
                expires_delta=timedelta(minutes=30
            )
            )
            dados={
                "access_token": acess_token
            }
            return jsonify(dados), 200
        dados = {
            "msg":"Crencenciais invalidas"
        }
        return jsonify(dados), 401

    except Exception as e:
        print("Erro login:", e)
        dados = {
            "msg": "Erro ao logar"
        }
        return jsonify(dados), 400


@app.route('/usuarios', methods=['POST'])
def cadastro():
    print("def_user_post")
    dados = request.get_json(silent=True)

    if not dados:
        return jsonify({"msg": "JSON inválido"}), 400

    nome = dados.get('nome')
    email = dados.get('email')
    cpf = dados.get('cpf')
    senha = dados.get('senha')
    # <-- ADICIONADO AQUI

    if not nome or not email or not senha or not cpf:
        dados = {
            "msg": "Email, usuário, senha e CPF são obrigatórios"
        }
        return jsonify(dados), 400

    try:
        # Verificar se o usuário já existe pelo e-mail
        user_check = select(Usuario).where(Usuario.email == email)
        usuario_existente = db_session.execute(user_check).scalar()

        if usuario_existente:
            dados = {"msg": "Usuário já existe"}
            return jsonify(dados), 409

        novo_usuario = Usuario(nome=nome, email=email, cpf=cpf)
        novo_usuario.set_senha_hash(senha)
        db_session.add(novo_usuario)
        db_session.commit()

        dados = {
            "msg": "Usuário criado com sucesso",
            "user_id": novo_usuario.id_funcinario
        }
        return jsonify(dados), 201
    except Exception as e:
        db_session.rollback()
        print("erro500: ", e)
        dados = {
            "msg": f"Erro ao registrar usuário: {str(e)}"
        }
        return jsonify(dados), 500

@app.route('/usuarios', methods=['GET'])
@jwt_required()
@admin_required
def listar_usuarios():
    print("def_user_get")
    try:
        stmt = select(Usuario)
        users_result = db_session.execute(stmt).scalars().all()
        for usuario in users_result:
            print("asd: ", usuario.serialize())
        users_result = [user.serialize() for user in users_result]
        return jsonify(users_result)
    except Exception as e:
        print("listaUserErro:", str(e))
        dados = {
            "msg": "Erro ao listar usuários"
        }
        return jsonify(dados), 500

@app.route('/usuarios/<id>', methods=['PUT'])
@jwt_required()
def atualizar_usuario(id):
    # --- 1. IDENTIFICAÇÃO E AUTORIZAÇÃO ---
    usuario_logado = get_jwt_identity()


    if str(usuario_logado) != str(id):
        dados = {"msg": "Acesso negado. Você só pode atualizar o seu próprio perfil."}
        return jsonify(dados), 403

    # --- 2. RECEBENDO OS DADOS (Com silent=True) ---
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"msg": "JSON inválido"}), 400

    try:
        # --- 3. BUSCA DO USUÁRIO NO BANCO ---
        usuario = db_session.get(Usuario, id)

        if usuario is None:
            return jsonify({"msg": "Usuário não encontrado."}), 404


        if 'nome' in data:
            nome_novo = str(data.get('nome')).strip()
            if nome_novo:
                usuario.nome = nome_novo

        # Troca de Senha
        if 'senha' in data:
            senha_nova = str(data.get('senha')).strip()
            if len(senha_nova) >= 8:
                usuario.set_senha_hash(senha_nova)
            else:
                return jsonify({"msg": "A senha deve ter pelo menos 8 caracteres."}), 400

        # A REGRA DO E-MAIL (Evitar duplicidade)
        if 'email' in data:
            email_novo = str(data.get('email')).strip()

            # Só faz a checagem no banco se ele REALMENTE estiver tentando mudar o e-mail
            if email_novo != usuario.email:
                # Verifica se já existe ALGUÉM com esse e-mail
                email_existente = db_session.execute(
                    select(Usuario).where(Usuario.email == email_novo)
                ).scalar_one_or_none()
                if email_existente:
                    return jsonify({"msg": "O email já está em uso."}), 409  # conflito

                usuario.email = email_novo


        db_session.commit()
        dados = {"msg": "Usuário atualizado com sucesso."}
        return jsonify(dados), 200
    except Exception as e:
        db_session.rollback()
        print("Erro ao atualizar usuário:", str(e))
        dados = {"msg": "Erro interno ao atualizar usuário."}
        return jsonify(dados), 500


@app.route('/usuarios/<int:id>', methods=['GET'])
@jwt_required()
def obter_detalhes_usuario(id):
    # --- 1. IDENTIFICAÇÃO NATIVA (Usa a claim 'sub' gerada no login) ---
    usuario_logado_id = get_jwt_identity()

    # Validação segura convertendo ambos os lados para string limpa
    if str(usuario_logado_id).strip() != str(id).strip():
        dados = {
            "msg": "Acesso negado. Você só pode visualizar o seu próprio perfil.",
            "seu_id_no_token": usuario_logado_id,
            "id_que_voce_tentou_ver": id
        }
        return jsonify(dados), 403

    try:
        # --- 2. BUSCA NO BANCO DE DADOS ---
        usuario = db_session.get(Usuario, id)

        # --- 3. VALIDAÇÃO DE EXISTÊNCIA (404) ---
        if usuario is None:
            return jsonify({"msg": "Usuário não encontrado."}), 404

        # --- 4. MONTAGEM DA RESPOSTA SEGURA ---
        detalhes_usuario = {
            "id_funcinario": usuario.id_funcinario,
            "nome": usuario.nome,
            "email": usuario.email,

            "data_cadastro": usuario.data_cadastro if hasattr(usuario, 'data_cadastro') else None
        }
        return jsonify(detalhes_usuario), 200

    except Exception as e:
        print("Erro ao obter detalhes do usuário:", str(e))
        dados = {"msg": "Erro interno ao buscar detalhes do usuário."}
        return jsonify(dados), 500


def api_obter_funcionario_por_cpf(cpf):
    try:
        funcionario = db_session.execute(
            select(Usuario).where(Usuario.cpf == cpf)
        ).scalar_one_or_none()

        if not funcionario:
            return jsonify({"erro": "Funcionario não localizado"}), 404

        return jsonify({
            "nome": funcionario.nome,
            "cpf": funcionario.cpf,
            "email": funcionario.email,
        }), 200
    except Exception as e:
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500





if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)