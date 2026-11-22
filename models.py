from sqlalchemy import create_engine, ForeignKey, select
from sqlalchemy.orm import relationship, sessionmaker, scoped_session, declarative_base
from sqlalchemy.sql import func

from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy import Column, Integer, String, DateTime

##-- Iniciar conexao com o banco de dados

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
            "data_cadastro": self.data_cadastro.strftime("%d/%m/%Y %H:%M:%S") if self.data_cadastro else None,
            "cpf": self.cpf,
            "last_login": self.last_login,
            "foto_perfil": self.foto_perfil,
            "status": self.status,
            "biografia": self.biografia,
            "telefone": self.telefone
        }

class Usuario_empresa(Base):
    __tablename__ = 'usuario_empresas'

    fk_id_usuario = Column(Integer,ForeignKey('usuarios.id_usuario'),primary_key=True)
    fk_id_empresa = Column(Integer, ForeignKey('empresas.id_empresa'), primary_key=True)
    data_adicao = Column(DateTime, nullable=False, server_default=func.now())

from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text

class Empresa(Base):
    __tablename__ = 'empresas'

    # Identificação da empresa
    id_empresa = Column(Integer, primary_key=True, autoincrement=True)

    # Informações básicas
    nome_empresa = Column(String(255), nullable=False)
    ticker = Column(String(20), nullable=False, unique=True)
    setor = Column(String(100))
    tipo_acao = Column(String(50))  # ON, PN ou UNIT

    # Indicadores financeiros
    valor_mercado = Column(Numeric(20, 2))  # Valor total de mercado da empresa
    patrimonio = Column(Numeric(20, 2))     # Patrimônio líquido
    ativos = Column(Numeric(20, 2))        # Total de ativos
    lucro_liquido = Column(Numeric(20, 2))  # Lucro líquido da empresa

    # Indicadores de dividendos
    dividendos_12m = Column(Numeric(20, 2))  # Dividendos pagos nos últimos 12 meses
    payout = Column(Numeric(10, 2))          # Percentual do lucro distribuído em dividendos
    dy = Column(Numeric(10, 2))              # Dividend Yield (%)

    # Indicadores de rentabilidade
    roe = Column(Numeric(10, 2))   # Retorno sobre o patrimônio líquido (%)
    roa = Column(Numeric(10, 2))   # Retorno sobre os ativos (%)
    roic = Column(Numeric(10, 2))  # Retorno sobre o capital investido (%)

    # Endividamento
    divida = Column(Numeric(20, 2))  # Valor da dívida da empresa

    # Relatório e atualização
    relatorio = Column(Text)  # Texto com informações e análise da empresa

    data_atualizacao = Column(
        DateTime,
        nullable=False,
        server_default=func.now()  # Data e hora geradas pelo banco no cadastro
    )

# Numeric(precisao, escala):
# Tipo de dado utilizado para armazenar números decimais com precisão definida.
# O primeiro parâmetro representa a quantidade máxima de dígitos do número.
# O segundo parâmetro representa a quantidade de casas decimais.
# Exemplo: Numeric(10, 2) permite armazenar até 10 dígitos no total,
# sendo 2 casas decimais. É recomendado para valores financeiros,
# pois oferece maior precisão decimal do que Float.

class Cotacao(Base):
    __tablename__ = 'cotacoes'

    # Identificação da cotação
    id_cotacao = Column(Integer, primary_key=True, autoincrement=True)

    # Relacionamento com a empresa
    id_empresa = Column(Integer, ForeignKey('empresas.id_empresa'), nullable=False)

    # Preços da ação
    preco_abertura = Column(Numeric(18, 4), nullable=False)
    preco_fechamento = Column(Numeric(18, 4), nullable=False)
    preco_maximo = Column(Numeric(18, 4), nullable=False)
    preco_minimo = Column(Numeric(18, 4), nullable=False)

    # Quantidade de ações negociadas
    volume_negociado = Column(Numeric(20, 2), nullable=False)

    # Data referente à negociação
    data_cotacao = Column(DateTime, nullable=False)

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
            telefone='18991878560'
        )

        admin.set_senha_hash('@admin123')

        db_session.add(admin)
        db_session.commit()

if __name__ == '__main__':
    inicializar_banco()
    print("Base de dados inicializado com sucesso!!!")




