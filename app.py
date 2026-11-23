from datetime import timedelta
from functools import wraps

from flask import Flask, jsonify, request
import yfinance as yf

from datetime import datetime

# Adicione o 'select' aqui junto com os outros imports do SQLAlchemy
from sqlalchemy import select

import secrets # Biblioteca nativa e segura do Python


# func -> Faz contas no banco (soma, média, contagem) para o Dashboard.
# cast -> Converte tipos de dados na consulta (ex: texto para número).
# Time -> Tipo de dado do MySQL usado para isolar apenas o horário (HH:MM:SS).

import os
from dotenv import load_dotenv

from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt

from models import db_session, Usuario, Empresa, Usuario_empresa, Investimento_acao, Investimento, Renda_fixa, Cotacao, \
    Indicador_financeiro, Historico_investimento, Historico_carteira, Simulacao, Item_simulacao, Categoria_financeira, \
    Movimentacao_financeira, Orcamento, Aporte_meta, Meta_financeira, Planejamento_financeiro, Comentario, Curtida, \
    Postagem, Sala_chat, Mensagem, Participante_sala, Participante_conversa, Conversa_privada, Solicitacao_conversa, \
    Bloqueio_usuario, Denuncia, Notificacao

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
            # CORRIGIDO: Alterado 'Funcionario.id' para 'Funcionario.id_usuario'
            sql = select(Usuario).where(Usuario.id_usuario == current_user)
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
                identity=str(usuario_existente.id_usuario),
                additional_claims={
                    "id_usuario": str(usuario_existente.id_usuario),
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
    telefone = dados.get('telefone')

    if not nome or not email or not senha or not cpf or not telefone:
        dados = {
            "msg": "Email, usuário, senha, CPF e telefone são obrigatórios"
        }
        return jsonify(dados), 400

    try:
        user_check = select(Usuario).where(Usuario.email == email)
        usuario_existente = db_session.execute(user_check).scalar()

        if usuario_existente:
            dados = {"msg": "Usuário já existe"}
            return jsonify(dados), 409

        novo_usuario = Usuario(nome=nome, email=email, cpf=cpf, telefone=telefone)
        novo_usuario.set_senha_hash(senha)
        db_session.add(novo_usuario)
        db_session.commit()

        dados = {
            "msg": "Usuário criado com sucesso",
            "user_id": novo_usuario.id_usuario
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
            "id_usuario": usuario.id_usuario,
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

def obter_historico(ticker):
    try:
        t = ticker.strip().upper()
        if not t.endswith('.SA'):
            t += '.SA'

        acao = yf.Ticker(t)
        hist = acao.history(period="1d", interval="5m")

        if hist.empty:
            return {"labels": [], "valores": []}

        return {
            "labels": hist.index.strftime("%H:%M").tolist(),
            "valores": [round(v, 2) for v in hist["Close"].tolist()]
        }
    except Exception as e:
        print(f"Erro ao buscar histórico de {ticker}: {e}")
        return {"labels": [], "valores": []}


def obter_preco_atual(ticker):
    try:
        # Formata o ticker para o padrão Yahoo Finance (Ex: PETR4 -> PETR4.SA)
        t = ticker.strip().upper()
        if not t.endswith('.SA'):
            t += '.SA'

        acao = yf.Ticker(t)
        # Puxa o histórico do último dia
        dados = acao.history(period="1d")

        if not dados.empty:
            # Retorna o preço de fechamento mais recente
            return round(dados['Close'].iloc[-1], 2)
        return None
    except Exception as e:
        print(f"Erro ao buscar ticker {ticker}: {e}")
        return None

def buscar_dados_empresa_yf(ticker):
    try:
        t = ticker.strip().upper()
        if not t.endswith('.SA'):
            t += '.SA'

        acao = yf.Ticker(t)
        info = acao.info

        # Verifica se o ativo existe (se não tiver preço atual nem nome, é inválido)
        preco = info.get('currentPrice') or info.get('regularMarketPrice')
        nome = info.get('longName') or info.get('shortName')

        if not preco or not nome:
            return None

        # Converte taxas decimais (ex: 0.15) para porcentagem (ex: 15.00)
        dy_raw = info.get('dividendYield')
        payout_raw = info.get('payoutRatio')
        roe_raw = info.get('returnOnEquity')
        roa_raw = info.get('returnOnAssets')

        return {
            "preco_atual": round(preco, 2),
            "nome_empresa": nome,
            "setor": info.get('sector'),
            "tipo_acao": info.get('quoteType'),  # Ex: EQUITY
            "valor_mercado": info.get('marketCap'),
            "patrimonio": info.get('totalStockholderEquity'),
            "ativos": info.get('totalAssets'),
            "lucro_liquido": info.get('netIncomeToCommon'),
            "dividendos_12m": info.get('dividendRate'),
            "payout": round(payout_raw * 100, 2) if payout_raw is not None else None,
            "dy": round(dy_raw * 100, 2) if dy_raw is not None else None,
            "roe": round(roe_raw * 100, 2) if roe_raw is not None else None,
            "roa": round(roa_raw * 100, 2) if roa_raw is not None else None,
            "roic": None,  # O Yahoo Finance não fornece ROIC diretamente no .info
            "divida": info.get('totalDebt'),
            "relatorio": info.get('longBusinessSummary')
        }
    except Exception as e:
        print(f"Erro ao buscar dados completos de {ticker}: {e}")
        return None


def gerar_relatorio_automatico(dados):
    nome = dados.get('nome_empresa', 'A empresa')
    setor = dados.get('setor') or 'não informado'
    valor_mercado = f"R$ {dados['valor_mercado']:,.2f}" if dados.get('valor_mercado') else "não divulgado"
    dy = f"{dados['dy']}%" if dados.get('dy') is not None else "não informado"
    roe = f"{dados['roe']}%" if dados.get('roe') is not None else "não informado"
    divida = f"R$ {dados['divida']:,.2f}" if dados.get('divida') else "não informada"

    return (
        f"Relatório Fundamentalista - {nome}\n"
        f"• Setor de atuação: {setor}\n"
        f"• Valor de Mercado: {valor_mercado}\n"
        f"• Dividend Yield (12m): {dy}\n"
        f"• Retorno sobre Patrimônio (ROE): {roe}\n"
        f"• Dívida Total: {divida}\n\n"
        f"Perfil Corporativo:\n{dados.get('relatorio') or 'Sem descrição adicional.'}"
    )


@app.route('/cadastrar_empresa', methods=['GET', 'POST'])
@admin_required
def api_empresa():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True)
            if not dados:
                return jsonify({"erro": "JSON inválido ou malformado."}), 400

            # O usuário envia APENAS o ticker
            ticker = (dados.get('ticker') or '').strip().upper().replace('.SA', '')

            if not ticker:
                return jsonify({"erro": "O campo 'ticker' é obrigatório."}), 400

            # 1. Verifica se já está cadastrado no banco
            empresa_existente = db_session.query(Empresa).filter(Empresa.ticker == ticker).first()
            if empresa_existente:
                return jsonify({"erro": f"A empresa '{ticker}' já está cadastrada."}), 409

            # 2. Puxa todos os dados automaticamente do Yahoo Finance
            dados_yf = buscar_dados_empresa_yf(ticker)
            if not dados_yf:
                return jsonify({"erro": f"Não foi possível encontrar dados para o ticker '{ticker}' na B3."}), 404

            # 3. Gera o relatório formatado e salva no banco de dados
            relatorio_texto = gerar_relatorio_automatico(dados_yf)

            nova_empresa = Empresa(
                nome_empresa=dados_yf['nome_empresa'],
                ticker=ticker,
                setor=dados_yf['setor'],
                tipo_acao=dados_yf['tipo_acao'],
                valor_mercado=dados_yf['valor_mercado'],
                patrimonio=dados_yf['patrimonio'],
                ativos=dados_yf['ativos'],
                lucro_liquido=dados_yf['lucro_liquido'],
                dividendos_12m=dados_yf['dividendos_12m'],
                payout=dados_yf['payout'],
                dy=dados_yf['dy'],
                roe=dados_yf['roe'],
                roa=dados_yf['roa'],
                roic=dados_yf['roic'],
                divida=dados_yf['divida'],
                relatorio=relatorio_texto
            )

            db_session.add(nova_empresa)
            db_session.commit()

            return jsonify({
                "mensagem": "Empresa cadastrada automaticamente com sucesso!",
                "id_empresa": nova_empresa.id_empresa,
                "ticker": nova_empresa.ticker,
                "nome_empresa": nova_empresa.nome_empresa,
                "setor": nova_empresa.setor,
                "preco_atual": dados_yf['preco_atual'],
                "dy": dados_yf['dy'],
                "roe": dados_yf['roe'],
                "relatorio": nova_empresa.relatorio
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro interno no cadastro: {str(e)}"}), 500

    # Método GET: Listagem paginada
    page = request.args.get('page', 1, type=int)
    per_page = 3
    offset = (page - 1) * per_page

    try:
        total_empresas = db_session.query(Empresa).count()
        total_pages = (total_empresas + per_page - 1) // per_page

        resultado = db_session.query(Empresa).order_by(Empresa.id_empresa.desc()).offset(offset).limit(per_page).all()

        lista_empresas = [{
            "id_empresa": e.id_empresa,
            "nome_empresa": e.nome_empresa,
            "ticker": e.ticker,
            "setor": e.setor,
            "valor_mercado": float(e.valor_mercado) if e.valor_mercado is not None else None,
            "dy": float(e.dy) if e.dy is not None else None,
            "roe": float(e.roe) if e.roe is not None else None,
            "divida": float(e.divida) if e.divida is not None else None,
            "relatorio": e.relatorio
        } for e in resultado]

        return jsonify({
            "lista_empresas": lista_empresas,
            "current_page": page,
            "total_pages": total_pages,
            "total_empresas": total_empresas,
        }), 200

    except Exception as e:
        app.logger.error(f"Erro na API de empresa: {e}", exc_info=True)
        return jsonify({"erro": "Erro interno ao listar as empresas."}), 500

@app.route('/empresa/<string:ticker>', methods=['PUT', 'DELETE'])
@admin_required
def gerenciar_empresa(ticker):
    ticker_limpo = ticker.strip().upper().replace('.SA', '')

    # Busca a empresa no banco de dados
    empresa = db_session.query(Empresa).filter(Empresa.ticker == ticker_limpo).first()
    if not empresa:
        return jsonify({"erro": f"Empresa com ticker '{ticker_limpo}' não encontrada."}), 404


    if request.method == 'PUT':
        try:
            dados_yf = buscar_dados_empresa_yf(ticker_limpo)
            if not dados_yf:
                return jsonify({"erro": f"Não foi possível obter dados atualizados para '{ticker_limpo}' no Yahoo Finance."}), 502

            # Atualiza os campos da empresa existente
            empresa.nome_empresa = dados_yf['nome_empresa']
            empresa.setor = dados_yf['setor']
            empresa.tipo_acao = dados_yf['tipo_acao']
            empresa.valor_mercado = dados_yf['valor_mercado']
            empresa.patrimonio = dados_yf['patrimonio']
            empresa.ativos = dados_yf['ativos']
            empresa.lucro_liquido = dados_yf['lucro_liquido']
            empresa.dividendos_12m = dados_yf['dividendos_12m']
            empresa.payout = dados_yf['payout']
            empresa.dy = dados_yf['dy']
            empresa.roe = dados_yf['roe']
            empresa.roa = dados_yf['roa']
            empresa.roic = dados_yf['roic']
            empresa.divida = dados_yf['divida']
            empresa.relatorio = gerar_relatorio_automatico(dados_yf)

            db_session.commit()

            return jsonify({
                "mensagem": f"Dados da empresa '{ticker_limpo}' atualizados com sucesso!",
                "id_empresa": empresa.id_empresa,
                "ticker": empresa.ticker,
                "nome_empresa": empresa.nome_empresa,
                "preco_atual": dados_yf['preco_atual'],
                "dy": dados_yf['dy'],
                "roe": dados_yf['roe'],
                "relatorio": empresa.relatorio,
                "data_atualizacao": empresa.data_atualizacao.isoformat() if empresa.data_atualizacao else None
            }), 200

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro interno ao atualizar empresa: {str(e)}"}), 500


    elif request.method == 'DELETE':
        try:
            db_session.query(Usuario_empresa).filter(
                Usuario_empresa.fk_id_empresa == empresa.id_empresa
            ).delete()

            db_session.delete(empresa)
            db_session.commit()

            return jsonify({
                "mensagem": f"Empresa '{ticker_limpo}' deletada com sucesso!"
            }), 200

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro interno ao deletar empresa: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

@app.route('/investimentos_acoes', methods=['GET', 'POST'])
@jwt_required()  # Ajuste para o seu decorator de autenticação (ex: @login_required ou @jwt_required)
def api_investimentos_acoes():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True)
            if not dados:
                return jsonify({"erro": "JSON inválido ou malformado."}), 400

            fk_id_investimento = dados.get('fk_id_investimento')
            num_acoes = dados.get('num_acoes')

            if not fk_id_investimento or num_acoes is None:
                return jsonify({"erro": "Os campos 'fk_id_investimento' e 'num_acoes' são obrigatórios."}), 400

            # 1. Valida se o investimento pai existe
            investimento = db_session.query(Investimento).filter(
                Investimento.id_investimento == fk_id_investimento
            ).first()
            if not investimento:
                return jsonify({"erro": f"Investimento ID '{fk_id_investimento}' não encontrado."}), 404

            # 2. Localiza a empresa pelo ID ou pelo Ticker
            fk_id_empresa = dados.get('fk_id_empresa')
            ticker = (dados.get('ticker') or '').strip().upper().replace('.SA', '')

            if fk_id_empresa:
                empresa = db_session.query(Empresa).filter(Empresa.id_empresa == fk_id_empresa).first()
            elif ticker:
                empresa = db_session.query(Empresa).filter(Empresa.ticker == ticker).first()
            else:
                return jsonify({"erro": "Informe 'fk_id_empresa' ou 'ticker'."}), 400

            if not empresa:
                return jsonify({"erro": "Empresa não encontrada no banco de dados. Cadastre-a primeiro."}), 404

            # 3. Define o preço da ação (usa o enviado no JSON ou busca o atual no Yahoo Finance)
            preco_acao = dados.get('preco_acao')
            if preco_acao is None:
                preco_acao = obter_preco_atual(empresa.ticker)
                if preco_acao is None:
                    return jsonify({"erro": f"Não foi possível obter o preço atual de '{empresa.ticker}'. Informe 'preco_acao' manualmente."}), 400

            # 4. Calcula o lote automaticamente (se não for informado, considera lote padrão de 100 ações)
            lote = dados.get('lote')
            if lote is None:
                lote = float(num_acoes) / 100

            # 5. Trata a data_compra (aceita ISO 'YYYY-MM-DD' ou 'YYYY-MM-DD HH:MM:SS', ou usa agora)
            data_compra_str = dados.get('data_compra')
            if data_compra_str:
                try:
                    data_compra = datetime.fromisoformat(data_compra_str)
                except ValueError:
                    return jsonify({"erro": "Formato de 'data_compra' inválido. Use 'YYYY-MM-DD' ou 'YYYY-MM-DDTHH:MM:SS'."}), 400
            else:
                data_compra = datetime.now()

            # 6. Cria e salva o registro
            novo_investimento_acao = Investimento_acao(
                fk_id_empresa=empresa.id_empresa,
                fk_id_investimento=investimento.id_investimento,
                num_acoes=num_acoes,
                preco_acao=preco_acao,
                lote=lote,
                data_compra=data_compra
            )

            db_session.add(novo_investimento_acao)
            db_session.commit()

            valor_total = round(float(num_acoes) * float(preco_acao), 2)

            return jsonify({
                "mensagem": "Investimento em ação registrado com sucesso!",
                "id_investimento_acao": novo_investimento_acao.id_investimento_acao,
                "empresa": empresa.nome_empresa,
                "ticker": empresa.ticker,
                "fk_id_investimento": novo_investimento_acao.fk_id_investimento,
                "num_acoes": float(novo_investimento_acao.num_acoes),
                "preco_acao": float(novo_investimento_acao.preco_acao),
                "lote": float(novo_investimento_acao.lote),
                "valor_total_investido": valor_total,
                "data_compra": novo_investimento_acao.data_compra.isoformat()
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro interno ao cadastrar investimento em ação: {str(e)}"}), 500


    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    fk_id_investimento = request.args.get('fk_id_investimento', type=int)

    try:
        query = db_session.query(Investimento_acao, Empresa).join(
            Empresa, Investimento_acao.fk_id_empresa == Empresa.id_empresa
        )

        if fk_id_investimento:
            query = query.filter(Investimento_acao.fk_id_investimento == fk_id_investimento)

        total_registros = query.count()
        total_pages = (total_registros + per_page - 1) // per_page

        resultados = query.order_by(Investimento_acao.data_compra.desc()).offset(offset).limit(per_page).all()

        lista = [{
            "id_investimento_acao": inv.id_investimento_acao,
            "fk_id_investimento": inv.fk_id_investimento,
            "fk_id_empresa": inv.fk_id_empresa,
            "ticker": emp.ticker,
            "nome_empresa": emp.nome_empresa,
            "num_acoes": float(inv.num_acoes),
            "preco_acao": float(inv.preco_acao),
            "lote": float(inv.lote),
            "valor_total": round(float(inv.num_acoes) * float(inv.preco_acao), 2),
            "data_compra": inv.data_compra.isoformat() if inv.data_compra else None
        } for inv, emp in resultados]

        return jsonify({
            "investimentos_acoes": lista,
            "current_page": page,
            "total_pages": total_pages,
            "total_registros": total_registros
        }), 200

    except Exception as e:
        app.logger.error(f"Erro ao listar investimentos em ações: {e}", exc_info=True)
        return jsonify({"erro": "Erro interno ao listar investimentos em ações."}), 500

@app.route('/investimentos_acoes/<int:id_investimento_acao>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_investimento_acao(id_investimento_acao):
    registro = db_session.query(Investimento_acao).filter(
        Investimento_acao.id_investimento_acao == id_investimento_acao
    ).first()

    if not registro:
        return jsonify({"erro": f"Investimento em ação ID '{id_investimento_acao}' não encontrado."}), 404

    # MÉTODO PUT: Atualiza quantidade, preço, lote ou data
    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True)
            if not dados:
                return jsonify({"erro": "JSON inválido ou malformado."}), 400

            if 'fk_id_empresa' in dados:
                empresa = db_session.query(Empresa).filter(Empresa.id_empresa == dados['fk_id_empresa']).first()
                if not empresa:
                    return jsonify({"erro": "Empresa informada não encontrada."}), 404
                registro.fk_id_empresa = empresa.id_empresa

            if 'num_acoes' in dados and dados['num_acoes'] is not None:
                registro.num_acoes = dados['num_acoes']
                # Recalcula o lote se não tiver sido enviado explicitamente
                if 'lote' not in dados:
                    registro.lote = float(dados['num_acoes']) / 100

            if 'preco_acao' in dados and dados['preco_acao'] is not None:
                registro.preco_acao = dados['preco_acao']

            if 'lote' in dados and dados['lote'] is not None:
                registro.lote = dados['lote']

            if 'data_compra' in dados and dados['data_compra']:
                try:
                    registro.data_compra = datetime.fromisoformat(dados['data_compra'])
                except ValueError:
                    return jsonify({"erro": "Formato de 'data_compra' inválido. Use 'YYYY-MM-DD'."}), 400

            db_session.commit()

            return jsonify({
                "mensagem": "Investimento em ação atualizado com sucesso!",
                "id_investimento_acao": registro.id_investimento_acao,
                "fk_id_empresa": registro.fk_id_empresa,
                "fk_id_investimento": registro.fk_id_investimento,
                "num_acoes": float(registro.num_acoes),
                "preco_acao": float(registro.preco_acao),
                "lote": float(registro.lote),
                "data_compra": registro.data_compra.isoformat()
            }), 200

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro interno ao atualizar: {str(e)}"}), 500

    # MÉTODO DELETE: Remove o lançamento
    elif request.method == 'DELETE':
        try:
            db_session.delete(registro)
            db_session.commit()

            return jsonify({
                "mensagem": f"Investimento em ação ID '{id_investimento_acao}' deletado com sucesso!"
            }), 200

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro interno ao deletar: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

def calcular_rendimento_renda_fixa(valor_investido, taxa_anual, tempo_anos):
    """
    Calcula juros compostos considerando taxa_anual em % (ex: 12.5) e tempo em anos.
    """
    c = float(valor_investido)
    i = float(taxa_anual) / 100.0
    t = float(tempo_anos)

    valor_final = c * ((1 + i) ** t)
    lucro = valor_final - c
    percentual_rentabilidade = (lucro / c) * 100 if c > 0 else 0.0

    return {
        "valor_final": round(valor_final, 2),
        "lucro": round(lucro, 2),
        "percentual_rentabilidade": round(percentual_rentabilidade, 2)
    }


@app.route('/rendas_fixas', methods=['GET', 'POST'])
@jwt_required()  # Ajuste para o seu decorator de autenticação
def api_rendas_fixas():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True)
            if not dados:
                return jsonify({"erro": "JSON inválido ou malformado."}), 400

            fk_id_investimento = dados.get('fk_id_investimento')
            tipo = (dados.get('tipo') or '').strip()
            indexador = (dados.get('indexador') or '').strip().upper()
            taxa = dados.get('taxa')
            valor_investido = dados.get('valor_investido')
            data_vencimento_str = dados.get('data_vencimento')

            # Validação dos campos obrigatórios de entrada
            if not all([fk_id_investimento, tipo, indexador, taxa is not None, valor_investido is not None, data_vencimento_str]):
                return jsonify({
                    "erro": "Campos obrigatórios: 'fk_id_investimento', 'tipo', 'indexador', 'taxa', 'valor_investido' e 'data_vencimento'."
                }), 400

            # 1. Verifica se o investimento pai existe
            investimento = db_session.query(Investimento).filter(
                Investimento.id_investimento == fk_id_investimento
            ).first()
            if not investimento:
                return jsonify({"erro": f"Investimento ID '{fk_id_investimento}' não encontrado."}), 404

            # 2. Trata data_aplicacao (padrão: hoje) e data_vencimento
            data_aplicacao_str = dados.get('data_aplicacao')
            try:
                data_aplicacao = datetime.fromisoformat(data_aplicacao_str) if data_aplicacao_str else datetime.now()
                data_vencimento = datetime.fromisoformat(data_vencimento_str)
            except ValueError:
                return jsonify({"erro": "Formato de data inválido. Use 'YYYY-MM-DD' ou 'YYYY-MM-DDTHH:MM:SS'."}), 400

            if data_vencimento <= data_aplicacao:
                return jsonify({"erro": "A 'data_vencimento' deve ser posterior à 'data_aplicacao'."}), 400

            # 3. Calcula o tempo em anos (se não enviado)
            tempo = dados.get('tempo')
            if tempo is None:
                dias = (data_vencimento - data_aplicacao).days
                tempo = round(dias / 365.0, 2)

            # 4. Calcula lucro, percentual_rentabilidade e valor_final (ou usa os enviados)
            calculo = calcular_rendimento_renda_fixa(valor_investido, taxa, tempo)
            lucro = dados.get('lucro') if dados.get('lucro') is not None else calculo['lucro']
            percentual_rentabilidade = (
                dados.get('percentual_rentabilidade')
                if dados.get('percentual_rentabilidade') is not None
                else calculo['percentual_rentabilidade']
            )
            valor_final = dados.get('valor_final') if dados.get('valor_final') is not None else calculo['valor_final']

            # 5. Cria e salva no banco
            nova_renda_fixa = Renda_fixa(
                fk_id_investimento=investimento.id_investimento,
                tipo=tipo,
                indexador=indexador,
                taxa=taxa,
                tempo=tempo,
                valor_investido=valor_investido,
                lucro=lucro,
                percentual_rentabilidade=percentual_rentabilidade,
                valor_final=valor_final,
                data_aplicacao=data_aplicacao,
                data_vencimento=data_vencimento
            )

            db_session.add(nova_renda_fixa)
            db_session.commit()

            return jsonify({
                "mensagem": "Aplicação em Renda Fixa cadastrada com sucesso!",
                "id_renda_fixa": nova_renda_fixa.id_renda_fixa,
                "fk_id_investimento": nova_renda_fixa.fk_id_investimento,
                "tipo": nova_renda_fixa.tipo,
                "indexador": nova_renda_fixa.indexador,
                "taxa": float(nova_renda_fixa.taxa),
                "tempo_anos": float(nova_renda_fixa.tempo),
                "valor_investido": float(nova_renda_fixa.valor_investido),
                "lucro": float(nova_renda_fixa.lucro),
                "percentual_rentabilidade": float(nova_renda_fixa.percentual_rentabilidade),
                "valor_final": float(nova_renda_fixa.valor_final),
                "data_aplicacao": nova_renda_fixa.data_aplicacao.isoformat(),
                "data_vencimento": nova_renda_fixa.data_vencimento.isoformat()
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro interno ao cadastrar renda fixa: {str(e)}"}), 500

    # ==========================================================
    # MÉTODO GET: Listagem paginada (com filtro por investimento)
    # ==========================================================
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    fk_id_investimento = request.args.get('fk_id_investimento', type=int)

    try:
        query = db_session.query(Renda_fixa)

        if fk_id_investimento:
            query = query.filter(Renda_fixa.fk_id_investimento == fk_id_investimento)

        total_registros = query.count()
        total_pages = (total_registros + per_page - 1) // per_page

        resultados = query.order_by(Renda_fixa.data_vencimento.asc()).offset(offset).limit(per_page).all()

        lista = [{
            "id_renda_fixa": rf.id_renda_fixa,
            "fk_id_investimento": rf.fk_id_investimento,
            "tipo": rf.tipo,
            "indexador": rf.indexador,
            "taxa": float(rf.taxa),
            "tempo": float(rf.tempo),
            "valor_investido": float(rf.valor_investido),
            "lucro": float(rf.lucro),
            "percentual_rentabilidade": float(rf.percentual_rentabilidade),
            "valor_final": float(rf.valor_final),
            "data_aplicacao": rf.data_aplicacao.isoformat() if rf.data_aplicacao else None,
            "data_vencimento": rf.data_vencimento.isoformat() if rf.data_vencimento else None
        } for rf in resultados]

        return jsonify({
            "rendas_fixas": lista,
            "current_page": page,
            "total_pages": total_pages,
            "total_registros": total_registros
        }), 200

    except Exception as e:
        app.logger.error(f"Erro ao listar rendas fixas: {e}", exc_info=True)
        return jsonify({"erro": "Erro interno ao listar rendas fixas."}), 500

@app.route('/rendas_fixas/<int:id_renda_fixa>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_renda_fixa(id_renda_fixa):
    registro = db_session.query(Renda_fixa).filter(
        Renda_fixa.id_renda_fixa == id_renda_fixa
    ).first()

    if not registro:
        return jsonify({"erro": f"Renda fixa ID '{id_renda_fixa}' não encontrada."}), 404

    # MÉTODO PUT: Atualiza dados e recalcula rendimentos automaticamente
    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True)
            if not dados:
                return jsonify({"erro": "JSON inválido ou malformado."}), 400

            if 'tipo' in dados and dados['tipo']:
                registro.tipo = dados['tipo'].strip()

            if 'indexador' in dados and dados['indexador']:
                registro.indexador = dados['indexador'].strip().upper()

            if 'taxa' in dados and dados['taxa'] is not None:
                registro.taxa = dados['taxa']

            if 'valor_investido' in dados and dados['valor_investido'] is not None:
                registro.valor_investido = dados['valor_investido']

            try:
                if 'data_aplicacao' in dados and dados['data_aplicacao']:
                    registro.data_aplicacao = datetime.fromisoformat(dados['data_aplicacao'])
                if 'data_vencimento' in dados and dados['data_vencimento']:
                    registro.data_vencimento = datetime.fromisoformat(dados['data_vencimento'])
            except ValueError:
                return jsonify({"erro": "Formato de data inválido. Use 'YYYY-MM-DD'."}), 400

            if registro.data_vencimento <= registro.data_aplicacao:
                return jsonify({"erro": "A 'data_vencimento' deve ser posterior à 'data_aplicacao'."}), 400

            # Recalcula o tempo se as datas mudaram e o tempo não foi enviado manualmente
            if 'tempo' in dados and dados['tempo'] is not None:
                registro.tempo = dados['tempo']
            else:
                dias = (registro.data_vencimento - registro.data_aplicacao).days
                registro.tempo = round(dias / 365.0, 2)

            # Recalcula lucro, rentabilidade e valor final (fora do else!)
            calculo = calcular_rendimento_renda_fixa(registro.valor_investido, registro.taxa, registro.tempo)
            registro.lucro = dados.get('lucro') if dados.get('lucro') is not None else calculo['lucro']

            registro.percentual_rentabilidade = (
                dados.get('percentual_rentabilidade')
                if dados.get('percentual_rentabilidade') is not None
                else calculo['percentual_rentabilidade']
            )
            registro.valor_final = (
                dados.get('valor_final')
                if dados.get('valor_final') is not None
                else calculo['valor_final']
            )

            db_session.commit()

            return jsonify({
                "mensagem": "Renda fixa atualizada com sucesso!",
                "id_renda_fixa": registro.id_renda_fixa,
                "tipo": registro.tipo,
                "indexador": registro.indexador,
                "taxa": float(registro.taxa),
                "tempo": float(registro.tempo),
                "valor_investido": float(registro.valor_investido),
                "lucro": float(registro.lucro),
                "percentual_rentabilidade": float(registro.percentual_rentabilidade),
                "valor_final": float(registro.valor_final),
                "data_aplicacao": registro.data_aplicacao.isoformat(),
                "data_vencimento": registro.data_vencimento.isoformat()
            }), 200

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro interno ao atualizar renda fixa: {str(e)}"}), 500

    # MÉTODO DELETE: Remove a aplicação
    elif request.method == 'DELETE':
        try:
            db_session.delete(registro)
            db_session.commit()

            return jsonify({
                "mensagem": f"Renda fixa ID '{id_renda_fixa}' deletada com sucesso!"
            }), 200

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro interno ao deletar renda fixa: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405


@app.route('/cotacoes', methods=['GET', 'POST'])
@jwt_required()  # Ajuste para o seu decorator de autenticação
def api_cotacoes():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True)
            if not dados:
                return jsonify({"erro": "JSON inválido ou malformado."}), 400

            # Localiza a empresa pelo ID ou pelo Ticker
            fk_id_empresa = dados.get('fk_id_empresa')
            ticker = (dados.get('ticker') or '').strip().upper().replace('.SA', '')

            if fk_id_empresa:
                empresa = db_session.query(Empresa).filter(Empresa.id_empresa == fk_id_empresa).first()
            elif ticker:
                empresa = db_session.query(Empresa).filter(Empresa.ticker == ticker).first()
            else:
                return jsonify({"erro": "Informe 'fk_id_empresa' ou 'ticker'."}), 400

            if not empresa:
                return jsonify({"erro": "Empresa não encontrada no banco de dados."}), 404

            # Se os preços não forem enviados manualmente, busca automático no Yahoo Finance
            preco_abertura = dados.get('preco_abertura')
            preco_fechamento = dados.get('preco_fechamento')
            preco_maximo = dados.get('preco_maximo')
            preco_minimo = dados.get('preco_minimo')
            volume_negociado = dados.get('volume_negociado')

            if any(v is None for v in [preco_abertura, preco_fechamento, preco_maximo, preco_minimo, volume_negociado]):
                acao = yf.Ticker(f"{empresa.ticker}.SA")
                hist = acao.history(period="1d")

                if hist.empty:
                    return jsonify({"erro": f"Não foi possível obter a cotação de '{empresa.ticker}' no Yahoo Finance."}), 404

                ultimo = hist.iloc[-1]
                preco_abertura = preco_abertura if preco_abertura is not None else round(float(ultimo['Open']), 4)
                preco_fechamento = preco_fechamento if preco_fechamento is not None else round(float(ultimo['Close']), 4)
                preco_maximo = preco_maximo if preco_maximo is not None else round(float(ultimo['High']), 4)
                preco_minimo = preco_minimo if preco_minimo is not None else round(float(ultimo['Low']), 4)
                volume_negociado = volume_negociado if volume_negociado is not None else round(float(ultimo['Volume']), 2)

            data_cotacao = (
                datetime.fromisoformat(dados['data_cotacao'])
                if dados.get('data_cotacao')
                else datetime.now()
            )

            nova_cotacao = Cotacao(
                fk_id_empresa=empresa.id_empresa,
                preco_abertura=preco_abertura,
                preco_fechamento=preco_fechamento,
                preco_maximo=preco_maximo,
                preco_minimo=preco_minimo,
                volume_negociado=volume_negociado,
                data_cotacao=data_cotacao
            )

            db_session.add(nova_cotacao)
            db_session.commit()

            return jsonify({
                "mensagem": "Cotação registrada com sucesso!",
                "id_cotacao": nova_cotacao.id_cotacao,
                "ticker": empresa.ticker,
                "preco_abertura": float(nova_cotacao.preco_abertura),
                "preco_fechamento": float(nova_cotacao.preco_fechamento),
                "preco_maximo": float(nova_cotacao.preco_maximo),
                "preco_minimo": float(nova_cotacao.preco_minimo),
                "volume_negociado": float(nova_cotacao.volume_negociado),
                "data_cotacao": nova_cotacao.data_cotacao.isoformat()
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro interno ao cadastrar cotação: {str(e)}"}), 500

    # MÉTODO GET: Listagem paginada (com filtro opcional por ticker ou fk_id_empresa)
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    fk_id_empresa = request.args.get('fk_id_empresa', type=int)

    try:
        query = db_session.query(Cotacao, Empresa).join(
            Empresa, Cotacao.fk_id_empresa == Empresa.id_empresa
        )

        if fk_id_empresa:
            query = query.filter(Cotacao.fk_id_empresa == fk_id_empresa)

        total = query.count()
        total_pages = (total + per_page - 1) // per_page
        resultados = query.order_by(Cotacao.data_cotacao.desc()).offset(offset).limit(per_page).all()

        lista = [{
            "id_cotacao": c.id_cotacao,
            "fk_id_empresa": c.fk_id_empresa,
            "ticker": emp.ticker,
            "preco_abertura": float(c.preco_abertura),
            "preco_fechamento": float(c.preco_fechamento),
            "preco_maximo": float(c.preco_maximo),
            "preco_minimo": float(c.preco_minimo),
            "volume_negociado": float(c.volume_negociado),
            "data_cotacao": c.data_cotacao.isoformat()
        } for c, emp in resultados]

        return jsonify({
            "cotacoes": lista,
            "current_page": page,
            "total_pages": total_pages,
            "total_registros": total
        }), 200

    except Exception as e:
        return jsonify({"erro": f"Erro ao listar cotações: {str(e)}"}), 500



@app.route('/cotacoes/<int:id_cotacao>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_cotacao(id_cotacao):
    cotacao = db_session.query(Cotacao).filter(Cotacao.id_cotacao == id_cotacao).first()
    if not cotacao:
        return jsonify({"erro": f"Cotação ID '{id_cotacao}' não encontrada."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}

            if 'preco_abertura' in dados:
                cotacao.preco_abertura = dados['preco_abertura']
            if 'preco_fechamento' in dados:
                cotacao.preco_fechamento = dados['preco_fechamento']
            if 'preco_maximo' in dados:
                cotacao.preco_maximo = dados['preco_maximo']
            if 'preco_minimo' in dados:
                cotacao.preco_minimo = dados['preco_minimo']
            if 'volume_negociado' in dados:
                cotacao.volume_negociado = dados['volume_negociado']
            if 'data_cotacao' in dados and dados['data_cotacao']:
                cotacao.data_cotacao = datetime.fromisoformat(dados['data_cotacao'])

            db_session.commit()
            return jsonify({"mensagem": "Cotação atualizada com sucesso!", "id_cotacao": cotacao.id_cotacao}), 200

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar cotação: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.delete(cotacao)
            db_session.commit()
            return jsonify({"mensagem": f"Cotação ID '{id_cotacao}' deletada com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar cotação: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

@app.route('/indicadores', methods=['GET', 'POST'])
@jwt_required()
def api_indicadores():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True)
            if not dados:
                return jsonify({"erro": "JSON inválido ou malformado."}), 400

            fk_id_empresa = dados.get('fk_id_empresa')
            ticker = (dados.get('ticker') or '').strip().upper().replace('.SA', '')

            if fk_id_empresa:
                empresa = db_session.query(Empresa).filter(Empresa.id_empresa == fk_id_empresa).first()
            elif ticker:
                empresa = db_session.query(Empresa).filter(Empresa.ticker == ticker).first()
            else:
                return jsonify({"erro": "Informe 'fk_id_empresa' ou 'ticker'."}), 400

            if not empresa:
                return jsonify({"erro": "Empresa não encontrada no banco de dados."}), 404

            # Busca automático no Yahoo Finance se os valores não forem enviados no JSON
            acao = yf.Ticker(f"{empresa.ticker}.SA")
            info = acao.info or {}

            roe_yf = round(info['returnOnEquity'] * 100, 4) if info.get('returnOnEquity') is not None else 0
            roa_yf = round(info['returnOnAssets'] * 100, 4) if info.get('returnOnAssets') is not None else 0
            payout_yf = round(info['payoutRatio'] * 100, 2) if info.get('payoutRatio') is not None else 0

            novo_indicador = Indicador_financeiro(
                fk_id_empresa=empresa.id_empresa,
                roic=dados.get('roic') if dados.get('roic') is not None else 0,
                roe=dados.get('roe') if dados.get('roe') is not None else roe_yf,
                roa=dados.get('roa') if dados.get('roa') is not None else roa_yf,
                divida=dados.get('divida') if dados.get('divida') is not None else (info.get('totalDebt') or 0),
                patrimonio=dados.get('patrimonio') if dados.get('patrimonio') is not None else (info.get('totalStockholderEquity') or 0),
                lucro_liquido=dados.get('lucro_liquido') if dados.get('lucro_liquido') is not None else (info.get('netIncomeToCommon') or 0),
                payout=dados.get('payout') if dados.get('payout') is not None else payout_yf
            )

            db_session.add(novo_indicador)
            db_session.commit()

            return jsonify({
                "mensagem": "Indicadores financeiros registrados com sucesso!",
                "id_indicador": novo_indicador.id_indicador,
                "ticker": empresa.ticker,
                "roic": float(novo_indicador.roic),
                "roe": float(novo_indicador.roe),
                "roa": float(novo_indicador.roa),
                "divida": float(novo_indicador.divida),
                "patrimonio": float(novo_indicador.patrimonio),
                "lucro_liquido": float(novo_indicador.lucro_liquido),
                "payout": float(novo_indicador.payout),
                "data_adicao": novo_indicador.data_adicao.isoformat() if novo_indicador.data_adicao else None
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro interno ao cadastrar indicadores: {str(e)}"}), 500

    # MÉTODO GET: Listagem paginada
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    fk_id_empresa = request.args.get('fk_id_empresa', type=int)

    try:
        query = db_session.query(Indicador_financeiro, Empresa).join(
            Empresa, Indicador_financeiro.fk_id_empresa == Empresa.id_empresa
        )

        if fk_id_empresa:
            query = query.filter(Indicador_financeiro.fk_id_empresa == fk_id_empresa)

        total = query.count()
        total_pages = (total + per_page - 1) // per_page
        resultados = query.order_by(Indicador_financeiro.data_adicao.desc()).offset(offset).limit(per_page).all()

        lista = [{
            "id_indicador": ind.id_indicador,
            "fk_id_empresa": ind.fk_id_empresa,
            "ticker": emp.ticker,
            "roic": float(ind.roic),
            "roe": float(ind.roe),
            "roa": float(ind.roa),
            "divida": float(ind.divida),
            "patrimonio": float(ind.patrimonio),
            "lucro_liquido": float(ind.lucro_liquido),
            "payout": float(ind.payout),
            "data_adicao": ind.data_adicao.isoformat() if ind.data_adicao else None
        } for ind, emp in resultados]

        return jsonify({
            "indicadores": lista,
            "current_page": page,
            "total_pages": total_pages,
            "total_registros": total
        }), 200

    except Exception as e:
        return jsonify({"erro": f"Erro ao listar indicadores: {str(e)}"}), 500

@app.route('/indicadores/<int:id_indicador>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_indicador(id_indicador):
    indicador = db_session.query(Indicador_financeiro).filter(
        Indicador_financeiro.id_indicador == id_indicador
    ).first()

    if not indicador:
        return jsonify({"erro": f"Indicador ID '{id_indicador}' não encontrado."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}

            for campo in ['roic', 'roe', 'roa', 'divida', 'patrimonio', 'lucro_liquido', 'payout']:
                if campo in dados and dados[campo] is not None:
                    setattr(indicador, campo, dados[campo])

            db_session.commit()
            return jsonify({"mensagem": "Indicador atualizado com sucesso!", "id_indicador": indicador.id_indicador}), 200

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar indicador: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.delete(indicador)
            db_session.commit()
            return jsonify({"mensagem": f"Indicador ID '{id_indicador}' deletado com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar indicador: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405


@app.route('/historicos_investimentos', methods=['GET', 'POST'])
@jwt_required()
def api_historicos_investimentos():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_investimento = dados.get('fk_id_investimento')
            valor_atual = dados.get('valor_atual')
            valor_investido = dados.get('valor_investido')

            if not all([fk_id_investimento, valor_atual is not None, valor_investido is not None]):
                return jsonify({"erro": "Campos obrigatórios: 'fk_id_investimento', 'valor_atual' e 'valor_investido'."}), 400

            investimento = db_session.query(Investimento).filter_by(id_investimento=fk_id_investimento).first()
            if not investimento:
                return jsonify({"erro": f"Investimento ID '{fk_id_investimento}' não encontrado."}), 404

            # Busca o último registro para definir valor_anterior automaticamente (se não for enviado)
            ultimo_hist = db_session.query(Historico_investimento).filter_by(
                fk_id_investimento=fk_id_investimento
            ).order_by(Historico_investimento.id_historico_investimento.desc()).first()

            valor_anterior = (
                float(dados['valor_anterior'])
                if dados.get('valor_anterior') is not None
                else (float(ultimo_hist.valor_atual) if ultimo_hist else float(valor_investido))
            )

            v_atual = float(valor_atual)
            v_investido = float(valor_investido)
            lucro = round(v_atual - v_investido, 2)
            rentabilidade = round((lucro / v_investido) * 100, 2) if v_investido > 0 else 0.0

            novo_hist = Historico_investimento(
                fk_id_investimento=fk_id_investimento,
                valor_atual=v_atual,
                valor_anterior=valor_anterior,
                valor_investido=v_investido,
                lucro=dados.get('lucro') if dados.get('lucro') is not None else lucro,
                rentabilidade_percentual=(
                    dados.get('rentabilidade_percentual')
                    if dados.get('rentabilidade_percentual') is not None
                    else rentabilidade
                )
            )

            db_session.add(novo_hist)
            db_session.commit()

            return jsonify({
                "mensagem": "Histórico de investimento registrado com sucesso!",
                "id_historico_investimento": novo_hist.id_historico_investimento,
                "valor_atual": float(novo_hist.valor_atual),
                "valor_anterior": float(novo_hist.valor_anterior),
                "valor_investido": float(novo_hist.valor_investido),
                "lucro": float(novo_hist.lucro),
                "rentabilidade_percentual": float(novo_hist.rentabilidade_percentual),
                "data_registro": novo_hist.data_registro.isoformat() if novo_hist.data_registro else None
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao registrar histórico: {str(e)}"}), 500

    # GET: Listagem paginada
    page = request.args.get('page', 1, type=int)
    per_page = 10
    fk_id_investimento = request.args.get('fk_id_investimento', type=int)

    try:
        query = db_session.query(Historico_investimento)
        if fk_id_investimento:
            query = query.filter_by(fk_id_investimento=fk_id_investimento)

        total = query.count()
        resultados = query.order_by(Historico_investimento.data_registro.desc()).offset((page - 1) * per_page).limit(per_page).all()

        lista = [{
            "id_historico_investimento": h.id_historico_investimento,
            "fk_id_investimento": h.fk_id_investimento,
            "valor_atual": float(h.valor_atual),
            "valor_anterior": float(h.valor_anterior),
            "valor_investido": float(h.valor_investido),
            "lucro": float(h.lucro),
            "rentabilidade_percentual": float(h.rentabilidade_percentual),
            "data_registro": h.data_registro.isoformat() if h.data_registro else None
        } for h in resultados]

        return jsonify({
            "historicos_investimentos": lista,
            "current_page": page,
            "total_pages": (total + per_page - 1) // per_page,
            "total_registros": total
        }), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar históricos: {str(e)}"}), 500


@app.route('/historicos_investimentos/<int:id_hist>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_historico_investimento(id_hist):
    hist = db_session.query(Historico_investimento).filter_by(id_historico_investimento=id_hist).first()
    if not hist:
        return jsonify({"erro": "Histórico não encontrado."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}
            for campo in ['valor_atual', 'valor_anterior', 'valor_investido', 'lucro', 'rentabilidade_percentual']:
                if campo in dados and dados[campo] is not None:
                    setattr(hist, campo, dados[campo])

            db_session.commit()
            return jsonify({"mensagem": "Histórico atualizado com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.delete(hist)
            db_session.commit()
            return jsonify({"mensagem": "Histórico deletado com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

@app.route('/historicos_carteiras', methods=['GET', 'POST'])
@jwt_required()
def api_historicos_carteiras():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_investimento = dados.get('fk_id_investimento')

            if not fk_id_investimento:
                return jsonify({"erro": "O campo 'fk_id_investimento' é obrigatório."}), 400

            investimento = db_session.query(Investimento).filter_by(id_investimento=fk_id_investimento).first()
            if not investimento:
                return jsonify({"erro": f"Investimento ID '{fk_id_investimento}' não encontrado."}), 404

            # Se os valores não forem enviados manualmente, calcula consolidando ações + renda fixa
            if any(dados.get(k) is None for k in ['valor_total', 'total_acoes', 'lucro_total', 'rentabilidade_total']):
                acoes = db_session.query(Investimento_acao, Empresa).join(
                    Empresa, Investimento_acao.fk_id_empresa == Empresa.id_empresa
                ).filter(Investimento_acao.fk_id_investimento == fk_id_investimento).all()

                rendas = db_session.query(Renda_fixa).filter_by(fk_id_investimento=fk_id_investimento).all()

                qtd_total_acoes = 0.0
                custo_total_acoes = 0.0
                valor_atual_acoes = 0.0

                for inv_acao, emp in acoes:
                    qtd = float(inv_acao.num_acoes)
                    preco_compra = float(inv_acao.preco_acao)
                    preco_hoje = obter_preco_atual(emp.ticker) or preco_compra

                    qtd_total_acoes += qtd
                    custo_total_acoes += qtd * preco_compra
                    valor_atual_acoes += qtd * preco_hoje

                custo_total_rf = sum(float(rf.valor_investido) for rf in rendas)
                valor_atual_rf = sum(float(rf.valor_final) for rf in rendas)

                total_investido = custo_total_acoes + custo_total_rf
                valor_total_calc = round(valor_atual_acoes + valor_atual_rf, 2)
                lucro_total_calc = round(valor_total_calc - total_investido, 2)
                rentabilidade_calc = round((lucro_total_calc / total_investido) * 100, 2) if total_investido > 0 else 0.0
            else:
                valor_total_calc = dados['valor_total']
                qtd_total_acoes = dados['total_acoes']
                lucro_total_calc = dados['lucro_total']
                rentabilidade_calc = dados['rentabilidade_total']

            novo_hist_carteira = Historico_carteira(
                fk_id_investimento=fk_id_investimento,
                valor_total=dados.get('valor_total') if dados.get('valor_total') is not None else valor_total_calc,
                total_acoes=dados.get('total_acoes') if dados.get('total_acoes') is not None else round(qtd_total_acoes, 2),
                lucro_total=dados.get('lucro_total') if dados.get('lucro_total') is not None else lucro_total_calc,
                rentabilidade_total=(
                    dados.get('rentabilidade_total')
                    if dados.get('rentabilidade_total') is not None
                    else rentabilidade_calc
                )
            )

            db_session.add(novo_hist_carteira)
            db_session.commit()

            return jsonify({
                "mensagem": "Histórico da carteira consolidado com sucesso!",
                "id_historico_carteira": novo_hist_carteira.id_historico_carteira,
                "valor_total": float(novo_hist_carteira.valor_total),
                "total_acoes": float(novo_hist_carteira.total_acoes),
                "lucro_total": float(novo_hist_carteira.lucro_total),
                "rentabilidade_total": float(novo_hist_carteira.rentabilidade_total),
                "data_registro": novo_hist_carteira.data_registro.isoformat() if novo_hist_carteira.data_registro else None
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao consolidar carteira: {str(e)}"}), 500

    # GET: Listagem paginada
    page = request.args.get('page', 1, type=int)
    per_page = 10
    fk_id_investimento = request.args.get('fk_id_investimento', type=int)

    try:
        query = db_session.query(Historico_carteira)
        if fk_id_investimento:
            query = query.filter_by(fk_id_investimento=fk_id_investimento)

        total = query.count()
        resultados = query.order_by(Historico_carteira.data_registro.desc()).offset((page - 1) * per_page).limit(per_page).all()

        lista = [{
            "id_historico_carteira": hc.id_historico_carteira,
            "fk_id_investimento": hc.fk_id_investimento,
            "valor_total": float(hc.valor_total),
            "total_acoes": float(hc.total_acoes),
            "lucro_total": float(hc.lucro_total),
            "rentabilidade_total": float(hc.rentabilidade_total),
            "data_registro": hc.data_registro.isoformat() if hc.data_registro else None
        } for hc in resultados]

        return jsonify({
            "historicos_carteiras": lista,
            "current_page": page,
            "total_pages": (total + per_page - 1) // per_page,
            "total_registros": total
        }), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar históricos de carteira: {str(e)}"}), 500


@app.route('/historicos_carteiras/<int:id_hc>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_historico_carteira(id_hc):
    hc = db_session.query(Historico_carteira).filter_by(id_historico_carteira=id_hc).first()
    if not hc:
        return jsonify({"erro": "Histórico de carteira não encontrado."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}
            for campo in ['valor_total', 'total_acoes', 'lucro_total', 'rentabilidade_total']:
                if campo in dados and dados[campo] is not None:
                    setattr(hc, campo, dados[campo])

            db_session.commit()
            return jsonify({"mensagem": "Histórico de carteira atualizado com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.delete(hc)
            db_session.commit()
            return jsonify({"mensagem": "Histórico de carteira deletado com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

@app.route('/simulacoes', methods=['GET', 'POST'])
@jwt_required()
def api_simulacoes():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_usuario = dados.get('fk_id_usuario')
            nome_simulacao = (dados.get('nome_simulacao') or '').strip()
            descricao = dados.get('descricao')

            if not fk_id_usuario or not nome_simulacao:
                return jsonify({"erro": "Os campos 'fk_id_usuario' e 'nome_simulacao' são obrigatórios."}), 400

            usuario = db_session.query(Usuario).filter_by(id_usuario=fk_id_usuario).first()
            if not usuario:
                return jsonify({"erro": f"Usuário ID '{fk_id_usuario}' não encontrado."}), 404

            nova_simulacao = Simulacao(
                fk_id_usuario=fk_id_usuario,
                nome_simulacao=nome_simulacao,
                descricao=descricao
            )

            db_session.add(nova_simulacao)
            db_session.commit()

            return jsonify({
                "mensagem": "Simulação criada com sucesso!",
                "id_simulacao": nova_simulacao.id_simulacao,
                "fk_id_usuario": nova_simulacao.fk_id_usuario,
                "nome_simulacao": nova_simulacao.nome_simulacao,
                "descricao": nova_simulacao.descricao,
                "data_criacao": nova_simulacao.data_criacao.isoformat() if nova_simulacao.data_criacao else None
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao criar simulação: {str(e)}"}), 500

    # GET: Listagem paginada (com filtro opcional por usuário)
    page = request.args.get('page', 1, type=int)
    per_page = 10
    fk_id_usuario = request.args.get('fk_id_usuario', type=int)

    try:
        query = db_session.query(Simulacao)
        if fk_id_usuario:
            query = query.filter_by(fk_id_usuario=fk_id_usuario)

        total = query.count()
        resultados = query.order_by(Simulacao.data_criacao.desc()).offset((page - 1) * per_page).limit(per_page).all()

        lista = [{
            "id_simulacao": s.id_simulacao,
            "fk_id_usuario": s.fk_id_usuario,
            "nome_simulacao": s.nome_simulacao,
            "descricao": s.descricao,
            "data_criacao": s.data_criacao.isoformat() if s.data_criacao else None
        } for s in resultados]

        return jsonify({
            "simulacoes": lista,
            "current_page": page,
            "total_pages": (total + per_page - 1) // per_page,
            "total_registros": total
        }), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar simulações: {str(e)}"}), 500


@app.route('/simulacoes/<int:id_simulacao>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_simulacao(id_simulacao):
    simulacao = db_session.query(Simulacao).filter_by(id_simulacao=id_simulacao).first()
    if not simulacao:
        return jsonify({"erro": "Simulação não encontrada."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}

            if 'nome_simulacao' in dados and dados['nome_simulacao']:
                simulacao.nome_simulacao = dados['nome_simulacao'].strip()
            if 'descricao' in dados:
                simulacao.descricao = dados['descricao']

            db_session.commit()
            return jsonify({
                "mensagem": "Simulação atualizada com sucesso!",
                "id_simulacao": simulacao.id_simulacao,
                "nome_simulacao": simulacao.nome_simulacao,
                "descricao": simulacao.descricao
            }), 200

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar simulação: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.delete(simulacao)
            db_session.commit()
            return jsonify({"mensagem": "Simulação deletada com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar simulação: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

from datetime import datetime


@app.route('/itens_simulacoes', methods=['GET', 'POST'])
@jwt_required()
def api_itens_simulacoes():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_simulacao = dados.get('fk_id_simulacao')
            tipo_ativo = (dados.get('tipo_ativo') or '').strip()
            valor_investido = dados.get('valor_investido')

            if not all([fk_id_simulacao, tipo_ativo, valor_investido is not None]):
                return jsonify({"erro": "Campos obrigatórios: 'fk_id_simulacao', 'tipo_ativo' e 'valor_investido'."}), 400

            simulacao = db_session.query(Simulacao).filter_by(id_simulacao=fk_id_simulacao).first()
            if not simulacao:
                return jsonify({"erro": f"Simulação ID '{fk_id_simulacao}' não encontrada."}), 404

            # Verifica empresa opcional (por ID ou Ticker)
            fk_id_empresa = dados.get('fk_id_empresa')
            ticker = (dados.get('ticker') or '').strip().upper().replace('.SA', '')
            empresa = None

            if fk_id_empresa:
                empresa = db_session.query(Empresa).filter_by(id_empresa=fk_id_empresa).first()
                if not empresa:
                    return jsonify({"erro": f"Empresa ID '{fk_id_empresa}' não encontrada."}), 404
            elif ticker:
                empresa = db_session.query(Empresa).filter_by(ticker=ticker).first()
                if empresa:
                    fk_id_empresa = empresa.id_empresa

            v_inv = float(valor_investido)
            preco_unitario = dados.get('preco_unitario')
            quantidade = dados.get('quantidade')

            # Se for ação e não tiver preço unitário, tenta buscar no Yahoo Finance
            if empresa and preco_unitario is None:
                preco_unitario = obter_preco_atual(empresa.ticker)

            if preco_unitario is not None and float(preco_unitario) > 0 and quantidade is None:
                quantidade = round(v_inv / float(preco_unitario), 4)

            # Cálculo automático de projeção (taxa anual em % e prazo em meses)
            taxa = dados.get('taxa')
            prazo = dados.get('prazo')  # em meses

            if dados.get('valor_final_estimado') is not None:
                valor_final_est = float(dados['valor_final_estimado'])
                rentabilidade_est = (
                    float(dados['rentabilidade_estimada'])
                    if dados.get('rentabilidade_estimada') is not None
                    else round(((valor_final_est - v_inv) / v_inv) * 100, 2) if v_inv > 0 else 0.0
                )
            elif taxa is not None and prazo is not None:
                anos = float(prazo) / 12.0
                calc = calcular_rendimento_renda_fixa(v_inv, float(taxa), anos)
                valor_final_est = calc['valor_final']
                rentabilidade_est = calc['percentual_rentabilidade']
            else:
                valor_final_est = v_inv
                rentabilidade_est = 0.0

            novo_item = Item_simulacao(
                fk_id_simulacao=fk_id_simulacao,
                fk_id_empresa=fk_id_empresa,
                tipo_ativo=tipo_ativo,
                valor_investido=v_inv,
                quantidade=quantidade,
                preco_unitario=preco_unitario,
                taxa=taxa,
                prazo=prazo,
                valor_final_estimado=valor_final_est,
                rentabilidade_estimada=rentabilidade_est
            )

            db_session.add(novo_item)
            db_session.commit()

            return jsonify({
                "mensagem": "Item adicionado à simulação com sucesso!",
                "id_item_simulacao": novo_item.id_item_simulacao,
                "fk_id_simulacao": novo_item.fk_id_simulacao,
                "fk_id_empresa": novo_item.fk_id_empresa,
                "tipo_ativo": novo_item.tipo_ativo,
                "valor_investido": float(novo_item.valor_investido),
                "quantidade": float(novo_item.quantidade) if novo_item.quantidade is not None else None,
                "preco_unitario": float(novo_item.preco_unitario) if novo_item.preco_unitario is not None else None,
                "taxa": float(novo_item.taxa) if novo_item.taxa is not None else None,
                "prazo": novo_item.prazo,
                "valor_final_estimado": float(novo_item.valor_final_estimado),
                "rentabilidade_estimada": float(novo_item.rentabilidade_estimada)
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao adicionar item na simulação: {str(e)}"}), 500

    # GET: Listagem com filtro por simulação
    fk_id_simulacao = request.args.get('fk_id_simulacao', type=int)

    try:
        query = db_session.query(Item_simulacao)
        if fk_id_simulacao:
            query = query.filter_by(fk_id_simulacao=fk_id_simulacao)

        resultados = query.order_by(Item_simulacao.id_item_simulacao.desc()).all()

        lista = [{
            "id_item_simulacao": item.id_item_simulacao,
            "fk_id_simulacao": item.fk_id_simulacao,
            "fk_id_empresa": item.fk_id_empresa,
            "tipo_ativo": item.tipo_ativo,
            "valor_investido": float(item.valor_investido),
            "quantidade": float(item.quantidade) if item.quantidade is not None else None,
            "preco_unitario": float(item.preco_unitario) if item.preco_unitario is not None else None,
            "taxa": float(item.taxa) if item.taxa is not None else None,
            "prazo": item.prazo,
            "valor_final_estimado": float(item.valor_final_estimado),
            "rentabilidade_estimada": float(item.rentabilidade_estimada)
        } for item in resultados]

        return jsonify({"itens_simulacoes": lista, "total": len(lista)}), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar itens da simulação: {str(e)}"}), 500


@app.route('/itens_simulacoes/<int:id_item>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_item_simulacao(id_item):
    item = db_session.query(Item_simulacao).filter_by(id_item_simulacao=id_item).first()
    if not item:
        return jsonify({"erro": "Item de simulação não encontrado."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}
            for campo in ['fk_id_empresa', 'tipo_ativo', 'valor_investido', 'quantidade', 'preco_unitario', 'taxa', 'prazo', 'valor_final_estimado', 'rentabilidade_estimada']:
                if campo in dados:
                    setattr(item, campo, dados[campo])

            db_session.commit()
            return jsonify({"mensagem": "Item de simulação atualizado com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar item: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.delete(item)
            db_session.commit()
            return jsonify({"mensagem": "Item de simulação deletado com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar item: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

@app.route('/categorias_financeiras', methods=['GET', 'POST'])
@jwt_required()
def api_categorias_financeiras():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_usuario = dados.get('fk_id_usuario')
            nome = (dados.get('nome') or '').strip()
            tipo = (dados.get('tipo') or '').strip().upper()  # Ex: RECEITA ou DESPESA
            descricao = dados.get('descricao')

            if not all([fk_id_usuario, nome, tipo]):
                return jsonify({"erro": "Campos obrigatórios: 'fk_id_usuario', 'nome' e 'tipo'."}), 400

            usuario = db_session.query(Usuario).filter_by(id_usuario=fk_id_usuario).first()
            if not usuario:
                return jsonify({"erro": f"Usuário ID '{fk_id_usuario}' não encontrado."}), 404

            nova_categoria = Categoria_financeira(
                fk_id_usuario=fk_id_usuario,
                nome=nome,
                tipo=tipo,
                descricao=descricao
            )

            db_session.add(nova_categoria)
            db_session.commit()

            return jsonify({
                "mensagem": "Categoria financeira criada com sucesso!",
                "id_categoria": nova_categoria.id_categoria,
                "nome": nova_categoria.nome,
                "tipo": nova_categoria.tipo,
                "descricao": nova_categoria.descricao
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao criar categoria: {str(e)}"}), 500

    # GET: Listagem (com filtro por usuário ou tipo)
    fk_id_usuario = request.args.get('fk_id_usuario', type=int)
    tipo = request.args.get('tipo', '').strip().upper()

    try:
        query = db_session.query(Categoria_financeira)
        if fk_id_usuario:
            query = query.filter_by(fk_id_usuario=fk_id_usuario)
        if tipo:
            query = query.filter_by(tipo=tipo)

        resultados = query.order_by(Categoria_financeira.nome.asc()).all()

        lista = [{
            "id_categoria": c.id_categoria,
            "fk_id_usuario": c.fk_id_usuario,
            "nome": c.nome,
            "tipo": c.tipo,
            "descricao": c.descricao
        } for c in resultados]

        return jsonify({"categorias": lista, "total": len(lista)}), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar categorias: {str(e)}"}), 500

@app.route('/categorias_financeiras/<int:id_categoria>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_categoria_financeira(id_categoria):
    categoria = db_session.query(Categoria_financeira).filter_by(id_categoria=id_categoria).first()
    if not categoria:
        return jsonify({"erro": "Categoria financeira não encontrada."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}
            if 'nome' in dados and dados['nome']:
                categoria.nome = dados['nome'].strip()
            if 'tipo' in dados and dados['tipo']:
                categoria.tipo = dados['tipo'].strip().upper()
            if 'descricao' in dados:
                categoria.descricao = dados['descricao']

            db_session.commit()
            return jsonify({"mensagem": "Categoria atualizada com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar categoria: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            # Verifica se existem movimentações vinculadas antes de excluir
            mov_vinculada = db_session.query(Movimentacao_financeira).filter_by(fk_id_categoria=id_categoria).first()
            if mov_vinculada:
                return jsonify({"erro": "Não é possível deletar: existem movimentações vinculadas a esta categoria."}), 409

            db_session.delete(categoria)
            db_session.commit()
            return jsonify({"mensagem": "Categoria deletada com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar categoria: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

@app.route('/movimentacoes_financeiras', methods=['GET', 'POST'])
@jwt_required()
def api_movimentacoes_financeiras():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_usuario = dados.get('fk_id_usuario')
            fk_id_categoria = dados.get('fk_id_categoria')
            valor = dados.get('valor')
            descricao = dados.get('descricao')

            if not all([fk_id_usuario, fk_id_categoria, valor is not None]):
                return jsonify({"erro": "Campos obrigatórios: 'fk_id_usuario', 'fk_id_categoria' e 'valor'."}), 400

            usuario = db_session.query(Usuario).filter_by(id_usuario=fk_id_usuario).first()
            if not usuario:
                return jsonify({"erro": f"Usuário ID '{fk_id_usuario}' não encontrado."}), 404

            categoria = db_session.query(Categoria_financeira).filter_by(id_categoria=fk_id_categoria).first()
            if not categoria:
                return jsonify({"erro": f"Categoria ID '{fk_id_categoria}' não encontrada."}), 404

            # Usa o tipo enviado ou herda automaticamente da categoria
            tipo = (dados.get('tipo') or categoria.tipo).strip().upper()

            try:
                data_mov = (
                    datetime.fromisoformat(dados['data_movimentacao'])
                    if dados.get('data_movimentacao')
                    else datetime.now()
                )
            except ValueError:
                return jsonify({"erro": "Formato de 'data_movimentacao' inválido. Use 'YYYY-MM-DD'."}), 400

            nova_mov = Movimentacao_financeira(
                fk_id_usuario=fk_id_usuario,
                fk_id_categoria=fk_id_categoria,
                tipo=tipo,
                descricao=descricao,
                valor=valor,
                data_movimentacao=data_mov
            )

            db_session.add(nova_mov)
            db_session.commit()

            return jsonify({
                "mensagem": "Movimentação financeira registrada com sucesso!",
                "id_movimentacao": nova_mov.id_movimentacao,
                "categoria": categoria.nome,
                "tipo": nova_mov.tipo,
                "descricao": nova_mov.descricao,
                "valor": float(nova_mov.valor),
                "data_movimentacao": nova_mov.data_movimentacao.isoformat()
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao registrar movimentação: {str(e)}"}), 500

    # GET: Listagem paginada com filtro por usuário, categoria ou tipo
    page = request.args.get('page', 1, type=int)
    per_page = 10
    fk_id_usuario = request.args.get('fk_id_usuario', type=int)
    fk_id_categoria = request.args.get('fk_id_categoria', type=int)
    tipo = request.args.get('tipo', '').strip().upper()

    try:
        query = db_session.query(Movimentacao_financeira, Categoria_financeira).join(
            Categoria_financeira, Movimentacao_financeira.fk_id_categoria == Categoria_financeira.id_categoria
        )

        if fk_id_usuario:
            query = query.filter(Movimentacao_financeira.fk_id_usuario == fk_id_usuario)
        if fk_id_categoria:
            query = query.filter(Movimentacao_financeira.fk_id_categoria == fk_id_categoria)
        if tipo:
            query = query.filter(Movimentacao_financeira.tipo == tipo)

        total = query.count()
        resultados = query.order_by(Movimentacao_financeira.data_movimentacao.desc()).offset((page - 1) * per_page).limit(per_page).all()

        lista = [{
            "id_movimentacao": mov.id_movimentacao,
            "fk_id_usuario": mov.fk_id_usuario,
            "fk_id_categoria": mov.fk_id_categoria,
            "nome_categoria": cat.nome,
            "tipo": mov.tipo,
            "descricao": mov.descricao,
            "valor": float(mov.valor),
            "data_movimentacao": mov.data_movimentacao.isoformat(),
            "data_registro": mov.data_registro.isoformat() if mov.data_registro else None
        } for mov, cat in resultados]

        return jsonify({
            "movimentacoes": lista,
            "current_page": page,
            "total_pages": (total + per_page - 1) // per_page,
            "total_registros": total
        }), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar movimentações: {str(e)}"}), 500

@app.route('/movimentacoes_financeiras/<int:id_mov>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_movimentacao_financeira(id_mov):
    mov = db_session.query(Movimentacao_financeira).filter_by(id_movimentacao=id_mov).first()
    if not mov:
        return jsonify({"erro": "Movimentação financeira não encontrada."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}

            if 'fk_id_categoria' in dados and dados['fk_id_categoria']:
                cat = db_session.query(Categoria_financeira).filter_by(id_categoria=dados['fk_id_categoria']).first()
                if not cat:
                    return jsonify({"erro": "Categoria informada não encontrada."}), 404
                mov.fk_id_categoria = cat.id_categoria

            if 'tipo' in dados and dados['tipo']:
                mov.tipo = dados['tipo'].strip().upper()
            if 'descricao' in dados:
                mov.descricao = dados['descricao']
            if 'valor' in dados and dados['valor'] is not None:
                mov.valor = dados['valor']
            if 'data_movimentacao' in dados and dados['data_movimentacao']:
                mov.data_movimentacao = datetime.fromisoformat(dados['data_movimentacao'])

            db_session.commit()
            return jsonify({"mensagem": "Movimentação atualizada com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar movimentação: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.delete(mov)
            db_session.commit()
            return jsonify({"mensagem": "Movimentação deletada com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar movimentação: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

@app.route('/orcamentos', methods=['GET', 'POST'])
@jwt_required()
def api_orcamentos():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_usuario = dados.get('fk_id_usuario')
            fk_id_categoria = dados.get('fk_id_categoria')
            valor_limite = dados.get('valor_limite')

            if not all([fk_id_usuario, fk_id_categoria, valor_limite is not None]):
                return jsonify({"erro": "Campos obrigatórios: 'fk_id_usuario', 'fk_id_categoria' e 'valor_limite'."}), 400

            usuario = db_session.query(Usuario).filter_by(id_usuario=fk_id_usuario).first()
            if not usuario:
                return jsonify({"erro": f"Usuário ID '{fk_id_usuario}' não encontrado."}), 404

            categoria = db_session.query(Categoria_financeira).filter_by(id_categoria=fk_id_categoria).first()
            if not categoria:
                return jsonify({"erro": f"Categoria ID '{fk_id_categoria}' não encontrada."}), 404

            hoje = datetime.now()
            mes_ref = dados.get('mes_referencia') or hoje.month
            ano_ref = dados.get('ano_referencia') or hoje.year

            # Evita orçamento duplicado para a mesma categoria/mês/ano
            existente = db_session.query(Orcamento).filter_by(
                fk_id_usuario=fk_id_usuario,
                fk_id_categoria=fk_id_categoria,
                mes_referencia=mes_ref,
                ano_referencia=ano_ref
            ).first()

            if existente:
                return jsonify({"erro": f"Já existe um orçamento para esta categoria em {mes_ref:02d}/{ano_ref}."}), 409

            novo_orcamento = Orcamento(
                fk_id_usuario=fk_id_usuario,
                fk_id_categoria=fk_id_categoria,
                valor_limite=valor_limite,
                mes_referencia=mes_ref,
                ano_referencia=ano_ref
            )

            db_session.add(novo_orcamento)
            db_session.commit()

            return jsonify({
                "mensagem": "Orçamento definido com sucesso!",
                "id_orcamento": novo_orcamento.id_orcamento,
                "categoria": categoria.nome,
                "valor_limite": float(novo_orcamento.valor_limite),
                "mes_referencia": novo_orcamento.mes_referencia,
                "ano_referencia": novo_orcamento.ano_referencia
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao criar orçamento: {str(e)}"}), 500

    # GET: Listagem com filtros opcionais
    fk_id_usuario = request.args.get('fk_id_usuario', type=int)
    mes = request.args.get('mes', type=int)
    ano = request.args.get('ano', type=int)

    try:
        query = db_session.query(Orcamento, Categoria_financeira).join(
            Categoria_financeira, Orcamento.fk_id_categoria == Categoria_financeira.id_categoria
        )

        if fk_id_usuario:
            query = query.filter(Orcamento.fk_id_usuario == fk_id_usuario)
        if mes:
            query = query.filter(Orcamento.mes_referencia == mes)
        if ano:
            query = query.filter(Orcamento.ano_referencia == ano)

        resultados = query.order_by(Orcamento.ano_referencia.desc(), Orcamento.mes_referencia.desc()).all()

        lista = [{
            "id_orcamento": orc.id_orcamento,
            "fk_id_usuario": orc.fk_id_usuario,
            "fk_id_categoria": orc.fk_id_categoria,
            "nome_categoria": cat.nome,
            "valor_limite": float(orc.valor_limite),
            "mes_referencia": orc.mes_referencia,
            "ano_referencia": orc.ano_referencia
        } for orc, cat in resultados]

        return jsonify({"orcamentos": lista, "total": len(lista)}), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar orçamentos: {str(e)}"}), 500


@app.route('/orcamentos/<int:id_orcamento>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_orcamento(id_orcamento):
    orcamento = db_session.query(Orcamento).filter_by(id_orcamento=id_orcamento).first()
    if not orcamento:
        return jsonify({"erro": "Orçamento não encontrado."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}
            if 'valor_limite' in dados and dados['valor_limite'] is not None:
                orcamento.valor_limite = dados['valor_limite']
            if 'mes_referencia' in dados and dados['mes_referencia'] is not None:
                orcamento.mes_referencia = dados['mes_referencia']
            if 'ano_referencia' in dados and dados['ano_referencia'] is not None:
                orcamento.ano_referencia = dados['ano_referencia']

            db_session.commit()
            return jsonify({"mensagem": "Orçamento atualizado com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar orçamento: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.delete(orcamento)
            db_session.commit()
            return jsonify({"mensagem": "Orçamento deletado com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar orçamento: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

@app.route('/metas_financeiras', methods=['GET', 'POST'])
@jwt_required()
def api_metas_financeiras():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_usuario = dados.get('fk_id_usuario')
            nome_meta = (dados.get('nome_meta') or '').strip()
            valor_objetivo = dados.get('valor_objetivo')

            if not all([fk_id_usuario, nome_meta, valor_objetivo is not None]):
                return jsonify({"erro": "Campos obrigatórios: 'fk_id_usuario', 'nome_meta' e 'valor_objetivo'."}), 400

            usuario = db_session.query(Usuario).filter_by(id_usuario=fk_id_usuario).first()
            if not usuario:
                return jsonify({"erro": f"Usuário ID '{fk_id_usuario}' não encontrado."}), 404

            valor_atual = float(dados.get('valor_atual') or 0)
            v_obj = float(valor_objetivo)
            status = (dados.get('status') or ('CONCLUIDA' if valor_atual >= v_obj else 'EM_ANDAMENTO')).strip().upper()

            try:
                data_inicio = datetime.fromisoformat(dados['data_inicio']) if dados.get('data_inicio') else datetime.now()
                data_limite = datetime.fromisoformat(dados['data_limite']) if dados.get('data_limite') else None
            except ValueError:
                return jsonify({"erro": "Formato de data inválido. Use 'YYYY-MM-DD'."}), 400

            nova_meta = Meta_financeira(
                fk_id_usuario=fk_id_usuario,
                nome_meta=nome_meta,
                descricao=dados.get('descricao'),
                valor_objetivo=v_obj,
                valor_atual=valor_atual,
                data_inicio=data_inicio,
                data_limite=data_limite,
                status=status
            )

            db_session.add(nova_meta)
            db_session.commit()

            return jsonify({
                "mensagem": "Meta financeira criada com sucesso!",
                "id_meta": nova_meta.id_meta,
                "nome_meta": nova_meta.nome_meta,
                "valor_objetivo": float(nova_meta.valor_objetivo),
                "valor_atual": float(nova_meta.valor_atual),
                "status": nova_meta.status
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao criar meta financeira: {str(e)}"}), 500

    # GET: Listagem com cálculo de porcentagem atingida
    fk_id_usuario = request.args.get('fk_id_usuario', type=int)
    status = request.args.get('status', '').strip().upper()

    try:
        query = db_session.query(Meta_financeira)
        if fk_id_usuario:
            query = query.filter_by(fk_id_usuario=fk_id_usuario)
        if status:
            query = query.filter_by(status=status)

        resultados = query.order_by(Meta_financeira.id_meta.desc()).all()

        lista = []
        for m in resultados:
            v_obj = float(m.valor_objetivo)
            v_atual = float(m.valor_atual)
            progresso = round((v_atual / v_obj) * 100, 2) if v_obj > 0 else 0.0

            lista.append({
                "id_meta": m.id_meta,
                "fk_id_usuario": m.fk_id_usuario,
                "nome_meta": m.nome_meta,
                "descricao": m.descricao,
                "valor_objetivo": v_obj,
                "valor_atual": v_atual,
                "progresso_percentual": progresso,
                "data_inicio": m.data_inicio.isoformat() if m.data_inicio else None,
                "data_limite": m.data_limite.isoformat() if m.data_limite else None,
                "status": m.status
            })

        return jsonify({"metas_financeiras": lista, "total": len(lista)}), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar metas financeiras: {str(e)}"}), 500

@app.route('/metas_financeiras/<int:id_meta>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_meta_financeira(id_meta):
    meta = db_session.query(Meta_financeira).filter_by(id_meta=id_meta).first()
    if not meta:
        return jsonify({"erro": "Meta financeira não encontrada."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}

            if 'nome_meta' in dados and dados['nome_meta']:
                meta.nome_meta = dados['nome_meta'].strip()
            if 'descricao' in dados:
                meta.descricao = dados['descricao']
            if 'valor_objetivo' in dados and dados['valor_objetivo'] is not None:
                meta.valor_objetivo = dados['valor_objetivo']
            if 'valor_atual' in dados and dados['valor_atual'] is not None:
                meta.valor_atual = dados['valor_atual']
            if 'data_limite' in dados:
                meta.data_limite = datetime.fromisoformat(dados['data_limite']) if dados['data_limite'] else None
            if 'status' in dados and dados['status']:
                meta.status = dados['status'].strip().upper()

            db_session.commit()
            return jsonify({"mensagem": "Meta financeira atualizada com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar meta: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            # Remove os aportes vinculados antes de excluir a meta
            db_session.query(Aporte_meta).filter_by(fk_id_meta=id_meta).delete()
            db_session.delete(meta)
            db_session.commit()
            return jsonify({"mensagem": "Meta financeira e seus aportes foram deletados com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar meta: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405


@app.route('/aportes_metas', methods=['GET', 'POST'])
@jwt_required()
def api_aportes_metas():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_meta = dados.get('fk_id_meta')
            valor = dados.get('valor')
            descricao = dados.get('descricao')

            if not fk_id_meta or valor is None:
                return jsonify({"erro": "Campos obrigatórios: 'fk_id_meta' e 'valor'."}), 400

            meta = db_session.query(Meta_financeira).filter_by(id_meta=fk_id_meta).first()
            if not meta:
                return jsonify({"erro": f"Meta financeira ID '{fk_id_meta}' não encontrada."}), 404

            valor_aporte = float(valor)
            if valor_aporte <= 0:
                return jsonify({"erro": "O valor do aporte deve ser maior que zero."}), 400

            novo_aporte = Aporte_meta(
                fk_id_meta=fk_id_meta,
                valor=valor_aporte,
                descricao=descricao
            )
            db_session.add(novo_aporte)

            # Atualiza automaticamente o saldo acumulado da meta
            novo_saldo_meta = float(meta.valor_atual) + valor_aporte
            meta.valor_atual = novo_saldo_meta

            if novo_saldo_meta >= float(meta.valor_objetivo):
                meta.status = 'CONCLUIDA'

            db_session.commit()

            return jsonify({
                "mensagem": "Aporte registrado e saldo da meta atualizado com sucesso!",
                "id_aporte": novo_aporte.id_aporte,
                "fk_id_meta": meta.id_meta,
                "valor_aportado": valor_aporte,
                "novo_valor_atual_meta": novo_saldo_meta,
                "status_meta": meta.status,
                "data_aporte": novo_aporte.data_aporte.isoformat() if novo_aporte.data_aporte else None
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao registrar aporte: {str(e)}"}), 500

    # GET: Listagem de aportes (com filtro por meta)
    fk_id_meta = request.args.get('fk_id_meta', type=int)

    try:
        query = db_session.query(Aporte_meta)
        if fk_id_meta:
            query = query.filter_by(fk_id_meta=fk_id_meta)

        resultados = query.order_by(Aporte_meta.data_aporte.desc()).all()

        lista = [{
            "id_aporte": ap.id_aporte,
            "fk_id_meta": ap.fk_id_meta,
            "valor": float(ap.valor),
            "descricao": ap.descricao,
            "data_aporte": ap.data_aporte.isoformat() if ap.data_aporte else None
        } for ap in resultados]

        return jsonify({"aportes_metas": lista, "total": len(lista)}), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar aportes: {str(e)}"}), 500


@app.route('/aportes_metas/<int:id_aporte>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_aporte_meta(id_aporte):
    aporte = db_session.query(Aporte_meta).filter_by(id_aporte=id_aporte).first()
    if not aporte:
        return jsonify({"erro": "Aporte não encontrado."}), 404

    meta = db_session.query(Meta_financeira).filter_by(id_meta=aporte.fk_id_meta).first()

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}

            if 'valor' in dados and dados['valor'] is not None:
                novo_valor = float(dados['valor'])
                diferenca = novo_valor - float(aporte.valor)
                aporte.valor = novo_valor

                if meta:
                    meta.valor_atual = max(0.0, float(meta.valor_atual) + diferenca)
                    meta.status = 'CONCLUIDA' if float(meta.valor_atual) >= float(meta.valor_objetivo) else 'EM_ANDAMENTO'

            if 'descricao' in dados:
                aporte.descricao = dados['descricao']

            db_session.commit()
            return jsonify({"mensagem": "Aporte atualizado e saldo da meta recalculado!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar aporte: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            if meta:
                meta.valor_atual = max(0.0, float(meta.valor_atual) - float(aporte.valor))
                if float(meta.valor_atual) < float(meta.valor_objetivo) and meta.status == 'CONCLUIDA':
                    meta.status = 'EM_ANDAMENTO'

            db_session.delete(aporte)
            db_session.commit()
            return jsonify({"mensagem": "Aporte deletado e valor estornado da meta com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar aporte: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405


@app.route('/planejamentos_financeiros', methods=['GET', 'POST'])
@jwt_required()
def api_planejamentos_financeiros():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_usuario = dados.get('fk_id_usuario')
            renda_mensal = dados.get('renda_mensal')
            gasto_mensal = dados.get('gasto_mensal_estimado')

            if not all([fk_id_usuario, renda_mensal is not None, gasto_mensal is not None]):
                return jsonify({"erro": "Campos obrigatórios: 'fk_id_usuario', 'renda_mensal' e 'gasto_mensal_estimado'."}), 400

            usuario = db_session.query(Usuario).filter_by(id_usuario=fk_id_usuario).first()
            if not usuario:
                return jsonify({"erro": f"Usuário ID '{fk_id_usuario}' não encontrado."}), 404

            renda = float(renda_mensal)
            gasto = float(gasto_mensal)

            # Cálculos automáticos se não forem informados no JSON
            sobra = max(0.0, renda - gasto)
            perc_poupanca = (
                float(dados['percentual_poupanca'])
                if dados.get('percentual_poupanca') is not None
                else (round((sobra / renda) * 100, 2) if renda > 0 else 0.0)
            )
            reserva_emergencia = (
                float(dados['valor_reserva_emergencia'])
                if dados.get('valor_reserva_emergencia') is not None
                else round(gasto * 6, 2)  # Padrão de 6 meses de despesas
            )

            novo_planejamento = Planejamento_financeiro(
                fk_id_usuario=fk_id_usuario,
                renda_mensal=renda,
                gasto_mensal_estimado=gasto,
                percentual_poupanca=perc_poupanca,
                valor_reserva_emergencia=reserva_emergencia
            )

            db_session.add(novo_planejamento)
            db_session.commit()

            return jsonify({
                "mensagem": "Planejamento financeiro criado com sucesso!",
                "id_planejamento": novo_planejamento.id_planejamento,
                "renda_mensal": float(novo_planejamento.renda_mensal),
                "gasto_mensal_estimado": float(novo_planejamento.gasto_mensal_estimado),
                "percentual_poupanca": float(novo_planejamento.percentual_poupanca),
                "valor_reserva_emergencia": float(novo_planejamento.valor_reserva_emergencia),
                "data_atualizacao": novo_planejamento.data_atualizacao.isoformat() if novo_planejamento.data_atualizacao else None
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao criar planejamento financeiro: {str(e)}"}), 500

    # GET: Listagem
    fk_id_usuario = request.args.get('fk_id_usuario', type=int)
    try:
        query = db_session.query(Planejamento_financeiro)
        if fk_id_usuario:
            query = query.filter_by(fk_id_usuario=fk_id_usuario)

        resultados = query.order_by(Planejamento_financeiro.data_atualizacao.desc()).all()

        lista = [{
            "id_planejamento": p.id_planejamento,
            "fk_id_usuario": p.fk_id_usuario,
            "renda_mensal": float(p.renda_mensal),
            "gasto_mensal_estimado": float(p.gasto_mensal_estimado),
            "percentual_poupanca": float(p.percentual_poupanca),
            "valor_reserva_emergencia": float(p.valor_reserva_emergencia),
            "data_atualizacao": p.data_atualizacao.isoformat() if p.data_atualizacao else None
        } for p in resultados]

        return jsonify({"planejamentos": lista, "total": len(lista)}), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar planejamentos: {str(e)}"}), 500

@app.route('/planejamentos_financeiros/<int:id_planejamento>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_planejamento_financeiro(id_planejamento):
    plan = db_session.query(Planejamento_financeiro).filter_by(id_planejamento=id_planejamento).first()
    if not plan:
        return jsonify({"erro": "Planejamento financeiro não encontrado."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}
            if 'renda_mensal' in dados and dados['renda_mensal'] is not None:
                plan.renda_mensal = dados['renda_mensal']
            if 'gasto_mensal_estimado' in dados and dados['gasto_mensal_estimado'] is not None:
                plan.gasto_mensal_estimado = dados['gasto_mensal_estimado']
            if 'percentual_poupanca' in dados and dados['percentual_poupanca'] is not None:
                plan.percentual_poupanca = dados['percentual_poupanca']
            if 'valor_reserva_emergencia' in dados and dados['valor_reserva_emergencia'] is not None:
                plan.valor_reserva_emergencia = dados['valor_reserva_emergencia']

            db_session.commit()
            return jsonify({"mensagem": "Planejamento financeiro atualizado com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar planejamento: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.delete(plan)
            db_session.commit()
            return jsonify({"mensagem": "Planejamento financeiro deletado com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar planejamento: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

@app.route('/postagens', methods=['GET', 'POST'])
@jwt_required()
def api_postagens():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_usuario = dados.get('fk_id_usuario')
            texto = (dados.get('texto_publicacao') or '').strip()
            visibilidade = (dados.get('visibilidade') or 'PUBLICO').strip().upper()

            if not fk_id_usuario or not texto:
                return jsonify({"erro": "Campos obrigatórios: 'fk_id_usuario' e 'texto_publicacao'."}), 400

            usuario = db_session.query(Usuario).filter_by(id_usuario=fk_id_usuario).first()
            if not usuario:
                return jsonify({"erro": f"Usuário ID '{fk_id_usuario}' não encontrado."}), 404

            nova_postagem = Postagem(
                fk_id_usuario=fk_id_usuario,
                texto_publicacao=texto,
                visibilidade=visibilidade,
                status='ATIVO'
            )

            db_session.add(nova_postagem)
            db_session.commit()

            return jsonify({
                "mensagem": "Postagem publicada com sucesso!",
                "id_postagem": nova_postagem.id_postagem,
                "autor": usuario.nome,
                "texto_publicacao": nova_postagem.texto_publicacao,
                "visibilidade": nova_postagem.visibilidade,
                "data_publicacao": nova_postagem.data_publicacao.isoformat() if nova_postagem.data_publicacao else None
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao publicar postagem: {str(e)}"}), 500

    # GET: Feed paginado com dados do autor e contagem de engajamento
    page = request.args.get('page', 1, type=int)
    per_page = 10
    fk_id_usuario = request.args.get('fk_id_usuario', type=int)

    try:
        query = db_session.query(Postagem, Usuario).join(
            Usuario, Postagem.fk_id_usuario == Usuario.id_usuario
        ).filter(Postagem.status == 'ATIVO')

        if fk_id_usuario:
            query = query.filter(Postagem.fk_id_usuario == fk_id_usuario)

        total = query.count()
        resultados = query.order_by(Postagem.data_publicacao.desc()).offset((page - 1) * per_page).limit(per_page).all()

        lista = []
        for post, autor in resultados:
            qtd_curtidas = db_session.query(Curtida).filter_by(fk_id_postagem=post.id_postagem).count()
            qtd_comentarios = db_session.query(Comentario).filter_by(fk_id_postagem=post.id_postagem).count()

            lista.append({
                "id_postagem": post.id_postagem,
                "fk_id_usuario": post.fk_id_usuario,
                "autor_nome": autor.nome,
                "autor_foto": autor.foto_perfil,
                "texto_publicacao": post.texto_publicacao,
                "visibilidade": post.visibilidade,
                "total_curtidas": qtd_curtidas,
                "total_comentarios": qtd_comentarios,
                "data_publicacao": post.data_publicacao.isoformat() if post.data_publicacao else None
            })

        return jsonify({
            "postagens": lista,
            "current_page": page,
            "total_pages": (total + per_page - 1) // per_page,
            "total_registros": total
        }), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar postagens: {str(e)}"}), 500


@app.route('/postagens/<int:id_postagem>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_postagem(id_postagem):
    post = db_session.query(Postagem).filter_by(id_postagem=id_postagem).first()
    if not post:
        return jsonify({"erro": "Postagem não encontrada."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}
            if 'texto_publicacao' in dados and dados['texto_publicacao']:
                post.texto_publicacao = dados['texto_publicacao'].strip()
            if 'visibilidade' in dados and dados['visibilidade']:
                post.visibilidade = dados['visibilidade'].strip().upper()
            if 'status' in dados and dados['status']:
                post.status = dados['status'].strip().upper()

            db_session.commit()
            return jsonify({"mensagem": "Postagem atualizada com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar postagem: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.query(Curtida).filter_by(fk_id_postagem=id_postagem).delete()
            db_session.query(Comentario).filter_by(fk_id_postagem=id_postagem).delete()
            db_session.delete(post)
            db_session.commit()
            return jsonify({"mensagem": "Postagem deletada com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar postagem: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

@app.route('/comentarios', methods=['GET', 'POST'])
@jwt_required()
def api_comentarios():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_usuario = dados.get('fk_id_usuario')
            fk_id_postagem = dados.get('fk_id_postagem')
            conteudo = (dados.get('conteudo') or '').strip()

            if not all([fk_id_usuario, fk_id_postagem, conteudo]):
                return jsonify({"erro": "Campos obrigatórios: 'fk_id_usuario', 'fk_id_postagem' e 'conteudo'."}), 400

            usuario = db_session.query(Usuario).filter_by(id_usuario=fk_id_usuario).first()
            post = db_session.query(Postagem).filter_by(id_postagem=fk_id_postagem).first()

            if not usuario or not post:
                return jsonify({"erro": "Usuário ou postagem não encontrados."}), 404

            novo_comentario = Comentario(
                fk_id_usuario=fk_id_usuario,
                fk_id_postagem=fk_id_postagem,
                conteudo=conteudo
            )

            db_session.add(novo_comentario)
            db_session.commit()

            return jsonify({
                "mensagem": "Comentário adicionado com sucesso!",
                "id_comentario": novo_comentario.id_comentario,
                "autor": usuario.nome,
                "conteudo": novo_comentario.conteudo,
                "data_comentario": novo_comentario.data_comentario.isoformat() if novo_comentario.data_comentario else None
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao comentar: {str(e)}"}), 500

    # GET: Lista comentários de uma postagem
    fk_id_postagem = request.args.get('fk_id_postagem', type=int)
    try:
        query = db_session.query(Comentario, Usuario).join(
            Usuario, Comentario.fk_id_usuario == Usuario.id_usuario
        )
        if fk_id_postagem:
            query = query.filter(Comentario.fk_id_postagem == fk_id_postagem)

        resultados = query.order_by(Comentario.data_comentario.asc()).all()

        lista = [{
            "id_comentario": c.id_comentario,
            "fk_id_postagem": c.fk_id_postagem,
            "fk_id_usuario": c.fk_id_usuario,
            "autor_nome": u.nome,
            "autor_foto": u.foto_perfil,
            "conteudo": c.conteudo,
            "data_comentario": c.data_comentario.isoformat() if c.data_comentario else None
        } for c, u in resultados]

        return jsonify({"comentarios": lista, "total": len(lista)}), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar comentários: {str(e)}"}), 500

@app.route('/comentarios/<int:id_comentario>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_comentario(id_comentario):
    comentario = db_session.query(Comentario).filter_by(id_comentario=id_comentario).first()
    if not comentario:
        return jsonify({"erro": "Comentário não encontrado."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}
            if 'conteudo' in dados and dados['conteudo'].strip():
                comentario.conteudo = dados['conteudo'].strip()
            db_session.commit()
            return jsonify({"mensagem": "Comentário atualizado com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar comentário: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.delete(comentario)
            db_session.commit()
            return jsonify({"mensagem": "Comentário deletado com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar comentário: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

@app.route('/curtidas', methods=['GET', 'POST'])
@jwt_required()
def api_curtidas():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_usuario = dados.get('fk_id_usuario')
            fk_id_postagem = dados.get('fk_id_postagem')

            if not fk_id_usuario or not fk_id_postagem:
                return jsonify({"erro": "Campos obrigatórios: 'fk_id_usuario' e 'fk_id_postagem'."}), 400

            curtida_existente = db_session.query(Curtida).filter_by(
                fk_id_usuario=fk_id_usuario,
                fk_id_postagem=fk_id_postagem
            ).first()

            if curtida_existente:
                db_session.delete(curtida_existente)
                db_session.commit()
                total = db_session.query(Curtida).filter_by(fk_id_postagem=fk_id_postagem).count()
                return jsonify({"mensagem": "Curtida removida.", "curtiu": False, "total_curtidas": total}), 200

            nova_curtida = Curtida(fk_id_usuario=fk_id_usuario, fk_id_postagem=fk_id_postagem)
            db_session.add(nova_curtida)
            db_session.commit()

            total = db_session.query(Curtida).filter_by(fk_id_postagem=fk_id_postagem).count()
            return jsonify({"mensagem": "Postagem curtida!", "curtiu": True, "total_curtidas": total}), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao processar curtida: {str(e)}"}), 500

    fk_id_postagem = request.args.get('fk_id_postagem', type=int)
    query = db_session.query(Curtida)
    if fk_id_postagem:
        query = query.filter_by(fk_id_postagem=fk_id_postagem)

    curtidas = query.all()
    return jsonify({
        "curtidas": [{
            "fk_id_usuario": c.fk_id_usuario,
            "fk_id_postagem": c.fk_id_postagem,
            "data_curtida": c.data_curtida.isoformat() if c.data_curtida else None
        } for c in curtidas],
        "total": len(curtidas)
    }), 200


@app.route('/salas_chat', methods=['GET', 'POST'])
@jwt_required()
def api_salas_chat():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_usuario = dados.get('fk_id_usuario')
            nome = (dados.get('nome') or '').strip()
            descricao = dados.get('descricao')

            if not fk_id_usuario or not nome:
                return jsonify({"erro": "Campos obrigatórios: 'fk_id_usuario' e 'nome'."}), 400

            usuario = db_session.query(Usuario).filter_by(id_usuario=fk_id_usuario).first()
            if not usuario:
                return jsonify({"erro": f"Usuário ID '{fk_id_usuario}' não encontrado."}), 404

            nova_sala = Sala_chat(
                fk_id_usuario=fk_id_usuario,
                nome=nome,
                descricao=descricao,
                status='ATIVO'
            )
            db_session.add(nova_sala)
            db_session.flush()  # Gera nova_sala.id_sala

            # Já inscreve o criador como participante da sala
            participante = Participante_sala(
                fk_id_sala=nova_sala.id_sala,
                fk_id_usuario=fk_id_usuario,
                status='ATIVO'
            )
            db_session.add(participante)
            db_session.commit()

            return jsonify({
                "mensagem": "Sala de chat criada com sucesso!",
                "id_sala": nova_sala.id_sala,
                "nome": nova_sala.nome,
                "descricao": nova_sala.descricao,
                "criador": usuario.nome
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao criar sala de chat: {str(e)}"}), 500

    # GET: Listagem de salas ativas
    try:
        salas = db_session.query(Sala_chat).filter_by(status='ATIVO').order_by(Sala_chat.data_criacao.desc()).all()

        lista = [{
            "id_sala": s.id_sala,
            "fk_id_usuario": s.fk_id_usuario,
            "nome": s.nome,
            "descricao": s.descricao,
            "status": s.status,
            "data_criacao": s.data_criacao.isoformat() if s.data_criacao else None
        } for s in salas]

        return jsonify({"salas_chat": lista, "total": len(lista)}), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar salas de chat: {str(e)}"}), 500


@app.route('/salas_chat/<int:id_sala>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_sala_chat(id_sala):
    sala = db_session.query(Sala_chat).filter_by(id_sala=id_sala).first()
    if not sala:
        return jsonify({"erro": "Sala de chat não encontrada."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}
            if 'nome' in dados and dados['nome'].strip():
                sala.nome = dados['nome'].strip()
            if 'descricao' in dados:
                sala.descricao = dados['descricao']
            if 'status' in dados and dados['status']:
                sala.status = dados['status'].strip().upper()

            db_session.commit()
            return jsonify({"mensagem": "Sala de chat atualizada com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar sala: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.query(Mensagem).filter_by(fk_id_sala=id_sala).delete()
            db_session.query(Participante_sala).filter_by(fk_id_sala=id_sala).delete()
            db_session.delete(sala)
            db_session.commit()
            return jsonify({"mensagem": "Sala de chat deletada com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar sala: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405


@app.route('/participantes_salas', methods=['GET', 'POST'])
@jwt_required()
def api_participantes_salas():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_sala = dados.get('fk_id_sala')
            fk_id_usuario = dados.get('fk_id_usuario')

            if not fk_id_sala or not fk_id_usuario:
                return jsonify({"erro": "Campos obrigatórios: 'fk_id_sala' e 'fk_id_usuario'."}), 400

            sala = db_session.query(Sala_chat).filter_by(id_sala=fk_id_sala).first()
            usuario = db_session.query(Usuario).filter_by(id_usuario=fk_id_usuario).first()

            if not sala or not usuario:
                return jsonify({"erro": "Sala de chat ou usuário não encontrados."}), 404

            existente = db_session.query(Participante_sala).filter_by(
                fk_id_sala=fk_id_sala,
                fk_id_usuario=fk_id_usuario
            ).first()

            if existente:
                if existente.status == 'ATIVO':
                    return jsonify({"erro": "Usuário já é participante ativo desta sala."}), 409
                existente.status = 'ATIVO'
                existente.data_entrada = datetime.now()
                db_session.commit()
                return jsonify({"mensagem": "Usuário reativado na sala com sucesso!"}), 200

            novo_part = Participante_sala(
                fk_id_sala=fk_id_sala,
                fk_id_usuario=fk_id_usuario,
                status='ATIVO'
            )
            db_session.add(novo_part)
            db_session.commit()

            return jsonify({
                "mensagem": "Usuário adicionado à sala com sucesso!",
                "fk_id_sala": novo_part.fk_id_sala,
                "fk_id_usuario": novo_part.fk_id_usuario,
                "usuario_nome": usuario.nome
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao adicionar participante na sala: {str(e)}"}), 500

    # GET: Lista participantes de uma sala
    fk_id_sala = request.args.get('fk_id_sala', type=int)
    try:
        query = db_session.query(Participante_sala, Usuario).join(
            Usuario, Participante_sala.fk_id_usuario == Usuario.id_usuario
        )
        if fk_id_sala:
            query = query.filter(Participante_sala.fk_id_sala == fk_id_sala)

        resultados = query.all()
        lista = [{
            "fk_id_sala": p.fk_id_sala,
            "fk_id_usuario": p.fk_id_usuario,
            "usuario_nome": u.nome,
            "usuario_foto": u.foto_perfil,
            "status": p.status,
            "data_entrada": p.data_entrada.isoformat() if p.data_entrada else None
        } for p, u in resultados]

        return jsonify({"participantes": lista, "total": len(lista)}), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar participantes: {str(e)}"}), 500


@app.route('/participantes_salas/<int:fk_id_sala>/<int:fk_id_usuario>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_participante_sala(fk_id_sala, fk_id_usuario):
    part = db_session.query(Participante_sala).filter_by(
        fk_id_sala=fk_id_sala,
        fk_id_usuario=fk_id_usuario
    ).first()

    if not part:
        return jsonify({"erro": "Participante não encontrado nesta sala."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}
            if 'status' in dados and dados['status']:
                part.status = dados['status'].strip().upper()
            db_session.commit()
            return jsonify({"mensagem": "Status do participante atualizado!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar participante: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.delete(part)
            db_session.commit()
            return jsonify({"mensagem": "Usuário removido da sala com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao remover participante: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

@app.route('/conversas_privadas', methods=['GET', 'POST'])
@jwt_required()
def api_conversas_privadas():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            participantes_ids = dados.get('participantes', [])

            nova_conversa = Conversa_privada(status='ATIVO')
            db_session.add(nova_conversa)
            db_session.flush()  # Gera nova_conversa.id_conversa_privada

            # Se forem enviados IDs de usuários, já vincula na tabela participantes_conversas
            for uid in set(participantes_ids):
                usuario = db_session.query(Usuario).filter_by(id_usuario=uid).first()
                if not usuario:
                    db_session.rollback()
                    return jsonify({"erro": f"Usuário ID '{uid}' não encontrado."}), 404

                db_session.add(Participante_conversa(
                    fk_id_conversa=nova_conversa.id_conversa_privada,
                    fk_id_usuario=uid,
                    status='ATIVO'
                ))

            db_session.commit()

            return jsonify({
                "mensagem": "Conversa privada criada com sucesso!",
                "id_conversa_privada": nova_conversa.id_conversa_privada,
                "status": nova_conversa.status,
                "participantes": list(set(participantes_ids)),
                "data_criacao": nova_conversa.data_criacao.isoformat() if nova_conversa.data_criacao else None
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao criar conversa privada: {str(e)}"}), 500

    # GET: Lista conversas (com filtro opcional por usuário participante)
    fk_id_usuario = request.args.get('fk_id_usuario', type=int)
    try:
        if fk_id_usuario:
            conversas = db_session.query(Conversa_privada).join(
                Participante_conversa,
                Conversa_privada.id_conversa_privada == Participante_conversa.fk_id_conversa
            ).filter(Participante_conversa.fk_id_usuario == fk_id_usuario).all()
        else:
            conversas = db_session.query(Conversa_privada).all()

        lista = []
        for conv in conversas:
            parts = db_session.query(Participante_conversa, Usuario).join(
                Usuario, Participante_conversa.fk_id_usuario == Usuario.id_usuario
            ).filter(Participante_conversa.fk_id_conversa == conv.id_conversa_privada).all()

            lista.append({
                "id_conversa_privada": conv.id_conversa_privada,
                "status": conv.status,
                "data_criacao": conv.data_criacao.isoformat() if conv.data_criacao else None,
                "participantes": [{
                    "id_usuario": u.id_usuario,
                    "nome": u.nome,
                    "status": pc.status
                } for pc, u in parts]
            })

        return jsonify({"conversas_privadas": lista, "total": len(lista)}), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar conversas privadas: {str(e)}"}), 500


@app.route('/conversas_privadas/<int:id_conversa>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_conversa_privada(id_conversa):
    conv = db_session.query(Conversa_privada).filter_by(id_conversa_privada=id_conversa).first()
    if not conv:
        return jsonify({"erro": "Conversa privada não encontrada."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}
            if 'status' in dados and dados['status']:
                conv.status = dados['status'].strip().upper()
            db_session.commit()
            return jsonify({"mensagem": "Conversa privada atualizada!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar conversa: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.query(Mensagem).filter_by(fk_id_conversa=id_conversa).delete()
            db_session.query(Participante_conversa).filter_by(fk_id_conversa=id_conversa).delete()
            db_session.delete(conv)
            db_session.commit()
            return jsonify({"mensagem": "Conversa privada deletada com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar conversa: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405


@app.route('/participantes_conversas', methods=['POST'])
@jwt_required()
def adicionar_participante_conversa():
    try:
        dados = request.get_json(silent=True) or {}
        fk_id_conversa = dados.get('fk_id_conversa')
        fk_id_usuario = dados.get('fk_id_usuario')

        if not fk_id_conversa or not fk_id_usuario:
            return jsonify({"erro": "Campos obrigatórios: 'fk_id_conversa' e 'fk_id_usuario'."}), 400

        existente = db_session.query(Participante_conversa).filter_by(
            fk_id_conversa=fk_id_conversa,
            fk_id_usuario=fk_id_usuario
        ).first()

        if existente:
            return jsonify({"erro": "Usuário já participa desta conversa."}), 409

        novo = Participante_conversa(
            fk_id_conversa=fk_id_conversa,
            fk_id_usuario=fk_id_usuario,
            status='ATIVO'
        )
        db_session.add(novo)
        db_session.commit()
        return jsonify({"mensagem": "Participante adicionado à conversa!"}), 201
    except Exception as e:
        db_session.rollback()
        return jsonify({"erro": f"Erro ao adicionar participante: {str(e)}"}), 500

@app.route('/participantes_conversas/<int:fk_id_conversa>/<int:fk_id_usuario>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_participante_conversa(fk_id_conversa, fk_id_usuario):
    pc = db_session.query(Participante_conversa).filter_by(
        fk_id_conversa=fk_id_conversa,
        fk_id_usuario=fk_id_usuario
    ).first()

    if not pc:
        return jsonify({"erro": "Participante não encontrado na conversa."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}
            if 'status' in dados and dados['status']:
                pc.status = dados['status'].strip().upper()
            db_session.commit()
            return jsonify({"mensagem": "Status atualizado com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.delete(pc)
            db_session.commit()
            return jsonify({"mensagem": "Participante removido da conversa!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao remover: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

@app.route('/solicitacoes_conversas', methods=['GET', 'POST'])
@jwt_required()
def api_solicitacoes_conversas():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_remetente = dados.get('fk_id_remetente')
            fk_id_destinatario = dados.get('fk_id_destinatario')

            if not fk_id_remetente or not fk_id_destinatario:
                return jsonify({"erro": "Campos obrigatórios: 'fk_id_remetente' e 'fk_id_destinatario'."}), 400

            if fk_id_remetente == fk_id_destinatario:
                return jsonify({"erro": "Não é possível enviar solicitação de conversa para si mesmo."}), 400

            # Verifica se há bloqueio entre os usuários
            bloqueio = db_session.query(Bloqueio_usuario).filter(
                ((Bloqueio_usuario.fk_id_bloqueador == fk_id_remetente) & (Bloqueio_usuario.fk_id_bloqueado == fk_id_destinatario)) |
                ((Bloqueio_usuario.fk_id_bloqueador == fk_id_destinatario) & (Bloqueio_usuario.fk_id_bloqueado == fk_id_remetente))
            ).first()
            if bloqueio:
                return jsonify({"erro": "Não é possível enviar solicitação devido a um bloqueio entre os usuários."}), 403

            # Evita solicitação pendente duplicada
            pendente = db_session.query(Solicitacao_conversa).filter_by(
                fk_id_remetente=fk_id_remetente,
                fk_id_destinatario=fk_id_destinatario,
                status='PENDENTE'
            ).first()
            if pendente:
                return jsonify({"erro": "Já existe uma solicitação pendente para este usuário."}), 409

            nova_sol = Solicitacao_conversa(
                fk_id_remetente=fk_id_remetente,
                fk_id_destinatario=fk_id_destinatario,
                status='PENDENTE'
            )
            db_session.add(nova_sol)
            db_session.commit()

            return jsonify({
                "mensagem": "Solicitação de conversa enviada com sucesso!",
                "id_solicitacao": nova_sol.id_solicitacao,
                "status": nova_sol.status,
                "data_solicitacao": nova_sol.data_solicitacao.isoformat() if nova_sol.data_solicitacao else None
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao enviar solicitação: {str(e)}"}), 500

    # GET: Lista solicitações recebidas ou enviadas
    fk_id_destinatario = request.args.get('fk_id_destinatario', type=int)
    fk_id_remetente = request.args.get('fk_id_remetente', type=int)
    status = request.args.get('status', '').strip().upper()

    try:
        query = db_session.query(Solicitacao_conversa)
        if fk_id_destinatario:
            query = query.filter_by(fk_id_destinatario=fk_id_destinatario)
        if fk_id_remetente:
            query = query.filter_by(fk_id_remetente=fk_id_remetente)
        if status:
            query = query.filter_by(status=status)

        resultados = query.order_by(Solicitacao_conversa.data_solicitacao.desc()).all()

        lista = [{
            "id_solicitacao": s.id_solicitacao,
            "fk_id_remetente": s.fk_id_remetente,
            "fk_id_destinatario": s.fk_id_destinatario,
            "status": s.status,
            "data_solicitacao": s.data_solicitacao.isoformat() if s.data_solicitacao else None,
            "data_resposta": s.data_resposta.isoformat() if s.data_resposta else None
        } for s in resultados]

        return jsonify({"solicitacoes": lista, "total": len(lista)}), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar solicitações: {str(e)}"}), 500

@app.route('/solicitacoes_conversas/<int:id_solicitacao>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_solicitacao_conversa(id_solicitacao):
    sol = db_session.query(Solicitacao_conversa).filter_by(id_solicitacao=id_solicitacao).first()
    if not sol:
        return jsonify({"erro": "Solicitação de conversa não encontrada."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}
            novo_status = (dados.get('status') or '').strip().upper()

            if novo_status not in ['ACEITA', 'RECUSADA', 'PENDENTE']:
                return jsonify({"erro": "Status inválido. Use 'ACEITA', 'RECUSADA' ou 'PENDENTE'."}), 400

            status_anterior = sol.status
            sol.status = novo_status
            sol.data_resposta = datetime.now()

            id_conversa_criada = None

            # Se foi aceita agora, cria automaticamente a conversa privada e adiciona os dois usuários
            if novo_status == 'ACEITA' and status_anterior != 'ACEITA':
                nova_conv = Conversa_privada(status='ATIVO')
                db_session.add(nova_conv)
                db_session.flush()

                db_session.add_all([
                    Participante_conversa(fk_id_conversa=nova_conv.id_conversa_privada, fk_id_usuario=sol.fk_id_remetente, status='ATIVO'),
                    Participante_conversa(fk_id_conversa=nova_conv.id_conversa_privada, fk_id_usuario=sol.fk_id_destinatario, status='ATIVO')
                ])
                id_conversa_criada = nova_conv.id_conversa_privada

            db_session.commit()

            resposta = {
                "mensagem": f"Solicitação marcada como '{novo_status}'.",
                "id_solicitacao": sol.id_solicitacao,
                "status": sol.status,
                "data_resposta": sol.data_resposta.isoformat()
            }
            if id_conversa_criada:
                resposta["id_conversa_privada_criada"] = id_conversa_criada

            return jsonify(resposta), 200

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao responder solicitação: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.delete(sol)
            db_session.commit()
            return jsonify({"mensagem": "Solicitação deletada com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar solicitação: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

@app.route('/mensagens', methods=['GET', 'POST'])
@jwt_required()
def api_mensagens():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_usuario = dados.get('fk_id_usuario')
            fk_id_sala = dados.get('fk_id_sala')
            fk_id_conversa = dados.get('fk_id_conversa')
            conteudo = (dados.get('conteudo') or '').strip()

            if not fk_id_usuario or not conteudo:
                return jsonify({"erro": "Campos obrigatórios: 'fk_id_usuario' e 'conteudo'."}), 400

            if not fk_id_sala and not fk_id_conversa:
                return jsonify({"erro": "Informe 'fk_id_sala' ou 'fk_id_conversa'."}), 400

            usuario = db_session.query(Usuario).filter_by(id_usuario=fk_id_usuario).first()
            if not usuario:
                return jsonify({"erro": f"Usuário ID '{fk_id_usuario}' não encontrado."}), 404

            nova_msg = Mensagem(
                fk_id_usuario=fk_id_usuario,
                fk_id_sala=fk_id_sala,
                fk_id_conversa=fk_id_conversa,
                conteudo=conteudo,
                status='ENVIADA'
            )

            db_session.add(nova_msg)
            db_session.commit()

            return jsonify({
                "mensagem": "Mensagem enviada com sucesso!",
                "id_mensagem": nova_msg.id_mensagem,
                "fk_id_usuario": nova_msg.fk_id_usuario,
                "autor": usuario.nome,
                "fk_id_sala": nova_msg.fk_id_sala,
                "fk_id_conversa": nova_msg.fk_id_conversa,
                "conteudo": nova_msg.conteudo,
                "status": nova_msg.status,
                "data_envio": nova_msg.data_envio.isoformat() if nova_msg.data_envio else None
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao enviar mensagem: {str(e)}"}), 500

    page = request.args.get('page', 1, type=int)
    per_page = 20
    fk_id_sala = request.args.get('fk_id_sala', type=int)
    fk_id_conversa = request.args.get('fk_id_conversa', type=int)

    try:
        query = db_session.query(Mensagem, Usuario).join(
            Usuario, Mensagem.fk_id_usuario == Usuario.id_usuario
        )

        if fk_id_sala:
            query = query.filter(Mensagem.fk_id_sala == fk_id_sala)
        if fk_id_conversa:
            query = query.filter(Mensagem.fk_id_conversa == fk_id_conversa)

        total = query.count()
        resultados = query.order_by(Mensagem.data_envio.asc()).offset((page - 1) * per_page).limit(per_page).all()

        lista = [{
            "id_mensagem": m.id_mensagem,
            "fk_id_usuario": m.fk_id_usuario,
            "autor_nome": u.nome,
            "autor_foto": u.foto_perfil,
            "fk_id_sala": m.fk_id_sala,
            "fk_id_conversa": m.fk_id_conversa,
            "conteudo": m.conteudo,
            "status": m.status,
            "data_envio": m.data_envio.isoformat() if m.data_envio else None
        } for m, u in resultados]

        return jsonify({
            "mensagens": lista,
            "current_page": page,
            "total_pages": (total + per_page - 1) // per_page,
            "total_registros": total
        }), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar mensagens: {str(e)}"}), 500


@app.route('/mensagens/<int:id_mensagem>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_mensagem(id_mensagem):
    msg = db_session.query(Mensagem).filter_by(id_mensagem=id_mensagem).first()
    if not msg:
        return jsonify({"erro": "Mensagem não encontrada."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}
            if 'conteudo' in dados and dados['conteudo'].strip():
                msg.conteudo = dados['conteudo'].strip()
            if 'status' in dados and dados['status']:
                msg.status = dados['status'].strip().upper()
            db_session.commit()
            return jsonify({"mensagem": "Mensagem atualizada com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar mensagem: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.delete(msg)
            db_session.commit()
            return jsonify({"mensagem": "Mensagem deletada com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar mensagem: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

@app.route('/bloqueios_usuarios', methods=['GET', 'POST'])
@jwt_required()
def api_bloqueios_usuarios():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_bloqueador = dados.get('fk_id_bloqueador')
            fk_id_bloqueado = dados.get('fk_id_bloqueado')
            motivo = dados.get('motivo')

            if not fk_id_bloqueador or not fk_id_bloqueado:
                return jsonify({"erro": "Campos obrigatórios: 'fk_id_bloqueador' e 'fk_id_bloqueado'."}), 400

            if fk_id_bloqueador == fk_id_bloqueado:
                return jsonify({"erro": "Não é possível bloquear a si mesmo."}), 400

            existente = db_session.query(Bloqueio_usuario).filter_by(
                fk_id_bloqueador=fk_id_bloqueador,
                fk_id_bloqueado=fk_id_bloqueado
            ).first()

            if existente:
                return jsonify({"erro": "Este usuário já está bloqueado."}), 409

            novo_bloqueio = Bloqueio_usuario(
                fk_id_bloqueador=fk_id_bloqueador,
                fk_id_bloqueado=fk_id_bloqueado,
                motivo=motivo
            )
            db_session.add(novo_bloqueio)
            db_session.commit()

            return jsonify({
                "mensagem": "Usuário bloqueado com sucesso!",
                "fk_id_bloqueador": novo_bloqueio.fk_id_bloqueador,
                "fk_id_bloqueado": novo_bloqueio.fk_id_bloqueado,
                "motivo": novo_bloqueio.motivo,
                "data_bloqueio": novo_bloqueio.data_bloqueio.isoformat() if novo_bloqueio.data_bloqueio else None
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao bloquear usuário: {str(e)}"}), 500

    fk_id_bloqueador = request.args.get('fk_id_bloqueador', type=int)
    try:
        query = db_session.query(Bloqueio_usuario, Usuario).join(
            Usuario, Bloqueio_usuario.fk_id_bloqueado == Usuario.id_usuario
        )
        if fk_id_bloqueador:
            query = query.filter(Bloqueio_usuario.fk_id_bloqueador == fk_id_bloqueador)

        resultados = query.all()
        lista = [{
            "fk_id_bloqueador": b.fk_id_bloqueador,
            "fk_id_bloqueado": b.fk_id_bloqueado,
            "nome_bloqueado": u.nome,
            "motivo": b.motivo,
            "data_bloqueio": b.data_bloqueio.isoformat() if b.data_bloqueio else None
        } for b, u in resultados]

        return jsonify({"bloqueios": lista, "total": len(lista)}), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar bloqueios: {str(e)}"}), 500


@app.route('/bloqueios_usuarios/<int:fk_id_bloqueador>/<int:fk_id_bloqueado>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_bloqueio_usuario(fk_id_bloqueador, fk_id_bloqueado):
    bloqueio = db_session.query(Bloqueio_usuario).filter_by(
        fk_id_bloqueador=fk_id_bloqueador,
        fk_id_bloqueado=fk_id_bloqueado
    ).first()

    if not bloqueio:
        return jsonify({"erro": "Registro de bloqueio não encontrado."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}
            if 'motivo' in dados:
                bloqueio.motivo = dados['motivo']
            db_session.commit()
            return jsonify({"mensagem": "Bloqueio atualizado com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar bloqueio: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.delete(bloqueio)
            db_session.commit()
            return jsonify({"mensagem": "Usuário desbloqueado com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao desbloquear usuário: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

@app.route('/denuncias', methods=['GET', 'POST'])
@jwt_required()
def api_denuncias():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_usuario = dados.get('fk_id_usuario')
            tipo_alvo = (dados.get('tipo_alvo') or '').strip().upper()
            id_alvo = dados.get('id_alvo')
            motivo = (dados.get('motivo') or '').strip()
            descricao = dados.get('descricao')

            if not all([fk_id_usuario, tipo_alvo, id_alvo is not None, motivo]):
                return jsonify({"erro": "Campos obrigatórios: 'fk_id_usuario', 'tipo_alvo', 'id_alvo' e 'motivo'."}), 400

            nova_denuncia = Denuncia(
                fk_id_usuario=fk_id_usuario,
                tipo_alvo=tipo_alvo,
                id_alvo=id_alvo,
                motivo=motivo,
                descricao=descricao,
                status='PENDENTE'
            )
            db_session.add(nova_denuncia)
            db_session.commit()

            return jsonify({
                "mensagem": "Denúncia registrada com sucesso!",
                "id_denuncia": nova_denuncia.id_denuncia,
                "status": nova_denuncia.status,
                "data_denuncia": nova_denuncia.data_denuncia.isoformat() if nova_denuncia.data_denuncia else None
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao registrar denúncia: {str(e)}"}), 500

    status = request.args.get('status', '').strip().upper()
    tipo_alvo = request.args.get('tipo_alvo', '').strip().upper()

    try:
        query = db_session.query(Denuncia)
        if status:
            query = query.filter_by(status=status)
        if tipo_alvo:
            query = query.filter_by(tipo_alvo=tipo_alvo)

        resultados = query.order_by(Denuncia.data_denuncia.desc()).all()
        lista = [{
            "id_denuncia": d.id_denuncia,
            "fk_id_usuario": d.fk_id_usuario,
            "tipo_alvo": d.tipo_alvo,
            "id_alvo": d.id_alvo,
            "motivo": d.motivo,
            "descricao": d.descricao,
            "status": d.status,
            "data_denuncia": d.data_denuncia.isoformat() if d.data_denuncia else None
        } for d in resultados]

        return jsonify({"denuncias": lista, "total": len(lista)}), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar denúncias: {str(e)}"}), 500


@app.route('/denuncias/<int:id_denuncia>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_denuncia(id_denuncia):
    denuncia = db_session.query(Denuncia).filter_by(id_denuncia=id_denuncia).first()
    if not denuncia:
        return jsonify({"erro": "Denúncia não encontrada."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}
            if 'status' in dados and dados['status']:
                denuncia.status = dados['status'].strip().upper()
            if 'descricao' in dados:
                denuncia.descricao = dados['descricao']
            db_session.commit()
            return jsonify({"mensagem": "Denúncia atualizada com sucesso!", "status": denuncia.status}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar denúncia: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.delete(denuncia)
            db_session.commit()
            return jsonify({"mensagem": "Denúncia deletada com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar denúncia: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405

@app.route('/notificacoes', methods=['GET', 'POST'])
@jwt_required()
def api_notificacoes():
    if request.method == 'POST':
        try:
            dados = request.get_json(silent=True) or {}
            fk_id_usuario = dados.get('fk_id_usuario')
            tipo = (dados.get('tipo') or '').strip().upper()
            titulo = (dados.get('titulo') or '').strip()
            conteudo = (dados.get('conteudo') or '').strip()

            if not all([fk_id_usuario, tipo, titulo, conteudo]):
                return jsonify({"erro": "Campos obrigatórios: 'fk_id_usuario', 'tipo', 'titulo' e 'conteudo'."}), 400

            nova_notif = Notificacao(
                fk_id_usuario=fk_id_usuario,
                tipo=tipo,
                titulo=titulo,
                conteudo=conteudo,
                lida=0
            )
            db_session.add(nova_notif)
            db_session.commit()

            return jsonify({
                "mensagem": "Notificação criada com sucesso!",
                "id_notificacao": nova_notif.id_notificacao,
                "titulo": nova_notif.titulo,
                "lida": nova_notif.lida
            }), 201

        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao criar notificação: {str(e)}"}), 500

    fk_id_usuario = request.args.get('fk_id_usuario', type=int)
    lida = request.args.get('lida', type=int)

    try:
        query = db_session.query(Notificacao)
        if fk_id_usuario:
            query = query.filter_by(fk_id_usuario=fk_id_usuario)
        if lida is not None:
            query = query.filter_by(lida=lida)

        resultados = query.order_by(Notificacao.data_criacao.desc()).all()
        lista = [{
            "id_notificacao": n.id_notificacao,
            "fk_id_usuario": n.fk_id_usuario,
            "tipo": n.tipo,
            "titulo": n.titulo,
            "conteudo": n.conteudo,
            "lida": n.lida,
            "data_criacao": n.data_criacao.isoformat() if n.data_criacao else None
        } for n in resultados]

        return jsonify({"notificacoes": lista, "total": len(lista)}), 200
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar notificações: {str(e)}"}), 500


@app.route('/notificacoes/<int:id_notificacao>', methods=['PUT', 'DELETE'])
@jwt_required()
def gerenciar_notificacao(id_notificacao):
    notif = db_session.query(Notificacao).filter_by(id_notificacao=id_notificacao).first()
    if not notif:
        return jsonify({"erro": "Notificação não encontrada."}), 404

    if request.method == 'PUT':
        try:
            dados = request.get_json(silent=True) or {}
            notif.lida = dados.get('lida', 1)
            db_session.commit()
            return jsonify({"mensagem": "Notificação atualizada com sucesso!", "lida": notif.lida}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao atualizar notificação: {str(e)}"}), 500

    elif request.method == 'DELETE':
        try:
            db_session.delete(notif)
            db_session.commit()
            return jsonify({"mensagem": "Notificação deletada com sucesso!"}), 200
        except Exception as e:
            db_session.rollback()
            return jsonify({"erro": f"Erro ao deletar notificação: {str(e)}"}), 500

    return jsonify({"erro": "Método não permitido."}), 405




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)