from sqlalchemy import create_engine, ForeignKey, select, Numeric, Text
from sqlalchemy.orm import relationship, sessionmaker, scoped_session, declarative_base
from sqlalchemy.sql import func

from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy import Column, Integer, String, DateTime

from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, ForeignKey, UniqueConstraint, func


# INICIAR CONEXÃO COM O BANCO DE DADOS

engine = create_engine('sqlite:///investimento.db', echo=True)
Base = declarative_base()

db_session = scoped_session(sessionmaker(bind=engine))

class Usuario(Base):
    __tablename__ = 'usuarios'

    id_usuario = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    cpf = Column(String(100), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    senha_hash = Column(String(255), nullable=False)
    perfil = Column(String(50), nullable=False, default='usuario')

    data_cadastro = Column(DateTime, nullable=False, server_default=func.now())
    last_login = Column(DateTime, nullable=True)

    telefone = Column(String(100), nullable=False)

    foto_perfil = Column(String(255), nullable=True)
    status = Column(String(100), nullable=True)
    biografia = Column(String(255), nullable=True)

    def set_senha_hash(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password_hash(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def serialize(self):
        return {
            "id_usuario": self.id_usuario,
            "nome": self.nome,
            "email": self.email,
            "perfil": self.perfil,
            "data_cadastro": self.data_cadastro.strftime("%d/%m/%Y %H:%M:%S") if self.data_cadastro else None,
            "cpf": self.cpf,
            "last_login": self.last_login,
            "foto_perfil": self.foto_perfil,
            "status": self.status,
            "biografia": self.biografia,
            "telefone": self.telefone
        }


class Empresa(Base):
    __tablename__ = 'empresas'

    id_empresa = Column(Integer, primary_key=True, autoincrement=True)

    nome_empresa = Column(String(255), nullable=False)
    ticker = Column(String(20), nullable=False, unique=True)
    setor = Column(String(100), nullable=True)
    tipo_acao = Column(String(50), nullable=True)

    valor_mercado = Column(Numeric(20, 2), nullable=True)
    patrimonio = Column(Numeric(20, 2), nullable=True)
    ativos = Column(Numeric(20, 2), nullable=True)
    lucro_liquido = Column(Numeric(20, 2), nullable=True)

    dividendos_12m = Column(Numeric(20, 2), nullable=True)
    payout = Column(Numeric(10, 2), nullable=True)
    dy = Column(Numeric(10, 2), nullable=True)

    roe = Column(Numeric(10, 2), nullable=True)
    roa = Column(Numeric(10, 2), nullable=True)
    roic = Column(Numeric(10, 2), nullable=True)

    divida = Column(Numeric(20, 2), nullable=True)
    relatorio = Column(Text, nullable=True)

    data_atualizacao = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class Usuario_empresa(Base):
    __tablename__ = 'usuario_empresas'
    __table_args__ = (
        UniqueConstraint('fk_id_usuario', 'fk_id_empresa', name='uq_usuario_empresa'),
    )

    id_usuario_empresa = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    fk_id_empresa = Column(Integer, ForeignKey('empresas.id_empresa'), nullable=False)
    data_adicao = Column(DateTime, nullable=False, server_default=func.now())



class Cotacao(Base):
    __tablename__ = 'cotacoes'

    id_cotacao = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_empresa = Column(Integer, ForeignKey('empresas.id_empresa'), nullable=False)

    preco_abertura = Column(Numeric(18, 4), nullable=False)
    preco_fechamento = Column(Numeric(18, 4), nullable=False)
    preco_maximo = Column(Numeric(18, 4), nullable=False)
    preco_minimo = Column(Numeric(18, 4), nullable=False)

    volume_negociado = Column(Numeric(20, 2), nullable=False)
    data_cotacao = Column(DateTime, nullable=False)

class Indicador_financeiro(Base):
    __tablename__ = 'indicadores_financeiros'

    id_indicador = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_empresa = Column(Integer, ForeignKey('empresas.id_empresa'), nullable=False)

    roic = Column(Numeric(18, 4), nullable=False)
    roe = Column(Numeric(18, 4), nullable=False)
    roa = Column(Numeric(18, 4), nullable=False)

    divida = Column(Numeric(20, 2), nullable=False)
    patrimonio = Column(Numeric(20, 2), nullable=False)
    lucro_liquido = Column(Numeric(20, 2), nullable=False)
    payout = Column(Numeric(10, 2), nullable=False)
    data_adicao = Column(DateTime, nullable=False, server_default=func.now())

class Investimento(Base):
    __tablename__ = 'investimentos'

    id_investimento = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    categoria = Column(String(50), nullable=False)
    status_investimento = Column(String(100), nullable=False)
    data_criacao = Column(DateTime, nullable=False, server_default=func.now())


class Investimento_acao(Base):
    __tablename__ = 'investimentos_acoes'

    id_investimento_acao = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_empresa = Column(Integer, ForeignKey('empresas.id_empresa'), nullable=False)
    fk_id_investimento = Column(Integer, ForeignKey('investimentos.id_investimento'), nullable=False)

    num_acoes = Column(Numeric(20, 2), nullable=False)
    preco_acao = Column(Numeric(18, 4), nullable=False)
    lote = Column(Numeric(20, 2), nullable=False)
    data_compra = Column(DateTime, nullable=False)


class Renda_fixa(Base):
    __tablename__ = 'rendas_fixas'

    id_renda_fixa = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_investimento = Column(Integer, ForeignKey('investimentos.id_investimento'), nullable=False)

    tipo = Column(String(100), nullable=False)
    indexador = Column(String(50), nullable=False)
    taxa = Column(Numeric(20, 2), nullable=False)
    tempo = Column(Numeric(20, 2), nullable=False)
    valor_investido = Column(Numeric(20, 2), nullable=False)
    lucro = Column(Numeric(20, 2), nullable=False)
    percentual_rentabilidade = Column(Numeric(20, 2), nullable=False)
    valor_final = Column(Numeric(20, 2), nullable=False)
    data_aplicacao = Column(DateTime, nullable=False)
    data_vencimento = Column(DateTime, nullable=False)


class Historico_investimento(Base):
    __tablename__ = 'historicos_investimentos'

    id_historico_investimento = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_investimento = Column(Integer, ForeignKey('investimentos.id_investimento'), nullable=False)

    valor_atual = Column(Numeric(20, 2), nullable=False)
    valor_anterior = Column(Numeric(20, 2), nullable=False)
    valor_investido = Column(Numeric(20, 2), nullable=False)
    lucro = Column(Numeric(20, 2), nullable=False)
    rentabilidade_percentual = Column(Numeric(20, 2), nullable=False)
    data_registro = Column(DateTime, nullable=False, server_default=func.now())

class Historico_carteira(Base):
    __tablename__ = 'historicos_carteiras'

    id_historico_carteira = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_investimento = Column(Integer, ForeignKey('investimentos.id_investimento'), nullable=False)

    valor_total = Column(Numeric(20, 2), nullable=False)
    total_acoes = Column(Numeric(20, 2), nullable=False)
    lucro_total = Column(Numeric(20, 2), nullable=False)
    rentabilidade_total = Column(Numeric(20, 2), nullable=False)
    data_registro = Column(DateTime, nullable=False, server_default=func.now())


class Simulacao(Base):
    __tablename__ = 'simulacoes'

    id_simulacao = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)

    nome_simulacao = Column(String(100), nullable=False)
    descricao = Column(Text, nullable=True)
    data_criacao = Column(DateTime, nullable=False, server_default=func.now())


class Item_simulacao(Base):
    __tablename__ = 'itens_simulacoes'

    id_item_simulacao = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_simulacao = Column(Integer, ForeignKey('simulacoes.id_simulacao'), nullable=False)
    fk_id_empresa = Column(Integer, ForeignKey('empresas.id_empresa'), nullable=True)

    tipo_ativo = Column(String(50), nullable=False)
    valor_investido = Column(Numeric(20, 2), nullable=False)
    quantidade = Column(Numeric(20, 4), nullable=True)
    preco_unitario = Column(Numeric(18, 4), nullable=True)
    taxa = Column(Numeric(10, 2), nullable=True)
    prazo = Column(Integer, nullable=True)
    valor_final_estimado = Column(Numeric(20, 2), nullable=False)
    rentabilidade_estimada = Column(Numeric(10, 2), nullable=False)

class Categoria_financeira(Base):
    __tablename__ = 'categorias_financeiras'

    id_categoria = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)

    nome = Column(String(100), nullable=False)
    tipo = Column(String(50), nullable=False)
    descricao = Column(String(255), nullable=True)


class Movimentacao_financeira(Base):
    __tablename__ = 'movimentacoes_financeiras'

    id_movimentacao = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    fk_id_categoria = Column(Integer, ForeignKey('categorias_financeiras.id_categoria'), nullable=False)
    tipo = Column(String(50), nullable=False)
    descricao = Column(String(255), nullable=True)
    valor = Column(Numeric(20, 2), nullable=False)
    data_movimentacao = Column(DateTime, nullable=False)
    data_registro = Column(DateTime, nullable=False, server_default=func.now())


class Orcamento(Base):
    __tablename__ = 'orcamentos'
    id_orcamento = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    fk_id_categoria = Column(Integer, ForeignKey('categorias_financeiras.id_categoria'), nullable=False)
    valor_limite = Column(Numeric(20, 2), nullable=False)
    mes_referencia = Column(Integer, nullable=False)
    ano_referencia = Column(Integer, nullable=False)


class Meta_financeira(Base):
    __tablename__  = 'metas_financeiras'

    id_meta = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    nome_meta = Column(String(100), nullable=False)
    descricao = Column(Text, nullable=True)
    valor_objetivo = Column(Numeric(20, 2), nullable=False)
    valor_atual = Column(Numeric(20, 2), nullable=False, default=0)
    data_inicio = Column(DateTime, nullable=False)
    data_limite = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False)


class Aporte_meta(Base):
    __tablename__  = 'aportes_metas'

    id_aporte = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_meta = Column(Integer, ForeignKey('metas_financeiras.id_meta'), nullable=False)
    valor = Column(Numeric(20, 2), nullable=False)
    data_aporte = Column(DateTime, nullable=False, server_default=func.now())
    descricao = Column(String(255), nullable=True)


class Planejamento_financeiro(Base):
    __tablename__  = 'planejamentos_financeiros'

    id_planejamento = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    renda_mensal = Column(Numeric(20, 2), nullable=False)
    gasto_mensal_estimado = Column(Numeric(20, 2), nullable=False)
    percentual_poupanca = Column(Numeric(10, 2), nullable=False)
    valor_reserva_emergencia = Column(Numeric(20, 2), nullable=False)
    data_atualizacao = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class Postagem(Base):
    __tablename__  = 'postagens'

    id_postagem = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    texto_publicacao = Column(Text, nullable=False)
    visibilidade = Column(String(50), nullable=False, default='PUBLICO')
    data_publicacao = Column(DateTime, nullable=False, server_default=func.now())
    status = Column(String(50), nullable=False, default='ATIVO')


class Comentario(Base):
    __tablename__  = 'comentarios'

    id_comentario = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    fk_id_postagem = Column(Integer, ForeignKey('postagens.id_postagem'), nullable=False)
    conteudo = Column(Text, nullable=False)
    data_comentario = Column(DateTime, nullable=False, server_default=func.now())


class Curtida(Base):
    __tablename__ = 'curtidas'
    fk_id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), primary_key=True)
    fk_id_postagem = Column(Integer, ForeignKey('postagens.id_postagem'), primary_key=True)
    data_curtida = Column(DateTime, nullable=False, server_default=func.now())


class Sala_chat(Base):
    __tablename__ = 'salas_chat'

    id_sala = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    nome = Column(String(100), nullable=False)
    descricao = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default='ATIVO')
    data_criacao = Column(DateTime, nullable=False, server_default=func.now())


class Participante_sala(Base):
    __tablename__ = 'participantes_salas'

    fk_id_sala = Column(Integer, ForeignKey('salas_chat.id_sala'), primary_key=True)
    fk_id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), primary_key=True)
    data_entrada = Column(DateTime, nullable=False, server_default=func.now())
    status = Column(String(50), nullable=False, default='ATIVO')

class Conversa_privada(Base):
    __tablename__ = 'conversa_privada'
    id_conversa_privada = Column(Integer, primary_key=True, autoincrement=True)
    data_criacao = Column(DateTime, nullable=False, server_default=func.now())
    status = Column(String(50), nullable=False, default='ATIVO')


class Participante_conversa(Base):
    __tablename__ = 'participantes_conversas'

    fk_id_conversa = Column(Integer, ForeignKey('conversa_privada.id_conversa_privada'), primary_key=True)
    fk_id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), primary_key=True)
    data_entrada = Column(DateTime, nullable=False, server_default=func.now())
    status = Column(String(50), nullable=False, default='ATIVO')



class Solicitacao_conversa(Base):
    __tablename__ = 'solicitacoes_conversas'

    id_solicitacao = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_remetente = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    fk_id_destinatario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    status = Column(String(50), nullable=False, default='PENDENTE')
    data_solicitacao = Column(DateTime, nullable=False, server_default=func.now())
    data_resposta = Column(DateTime, nullable=True)


class Mensagem(Base):
    __tablename__ = 'mensagens'

    id_mensagem = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    fk_id_sala = Column(Integer, ForeignKey('salas_chat.id_sala'), nullable=True)
    fk_id_conversa = Column(Integer, ForeignKey('conversa_privada.id_conversa_privada'), nullable=True)  # <-- Atualize aqui também
    conteudo = Column(Text, nullable=False)
    data_envio = Column(DateTime, nullable=False, server_default=func.now())
    status = Column(String(50), nullable=False, default='ENVIADA')



class Bloqueio_usuario(Base):
    __tablename__ = 'bloqueios_usuarios'

    fk_id_bloqueador = Column(Integer, ForeignKey('usuarios.id_usuario'), primary_key=True)
    fk_id_bloqueado = Column(Integer, ForeignKey('usuarios.id_usuario'), primary_key=True)
    data_bloqueio = Column(DateTime, nullable=False, server_default=func.now())
    motivo = Column(String(255), nullable=True)


class Denuncia(Base):
    __tablename__ = 'denuncias'

    id_denuncia = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    tipo_alvo = Column(String(50), nullable=False)
    id_alvo = Column(Integer, nullable=False)
    motivo = Column(String(100), nullable=False)
    descricao = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default='PENDENTE')
    data_denuncia = Column(DateTime, nullable=False, server_default=func.now())


class Notificacao(Base):
    __tablename__ = 'notificacoes'

    id_notificacao = Column(Integer, primary_key=True, autoincrement=True)
    fk_id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    tipo = Column(String(50), nullable=False)
    titulo = Column(String(100), nullable=False)
    conteudo = Column(Text, nullable=False)
    lida = Column(Integer, nullable=False, default=0)
    data_criacao = Column(DateTime, nullable=False, server_default=func.now())



def inicializar_banco():
    Base.metadata.create_all(engine)

    usuario_existente = db_session.execute(
        select(Usuario.id_usuario).limit(1)
    ).first()

    if not usuario_existente:
        admin = Usuario(
            nome='admin',
            cpf='7899456321',
            email='thaylamoralles@gmail.com',
            telefone='18991878560',
            perfil='admin',
            status='ATIVO',
            biografia='Administrador do sistema.'
        )

        admin.set_senha_hash('@admin123')

        db_session.add(admin)
        db_session.commit()

if __name__ == '__main__':
    inicializar_banco()
    print("Base de dados inicializado com sucesso!!!")