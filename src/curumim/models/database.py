from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# --- CONFIGURAÇÃO DE CAMINHO ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_DIR = PROJECT_ROOT / "data"

DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "curumim.db"

DATABASE_URL = f"sqlite:///{DB_PATH}"

Base = declarative_base()

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class LearnerProfile(Base):
    __tablename__ = 'learner_profiles'

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, nullable=False, index=True)
    pedagogical_level = Column(String, default='iniciante')
    onboarding_state = Column(String, default='new')
    display_name = Column(String, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relacionamento opcional para facilitar a busca de mensagens do aluno
    mensagens = relationship("ChatMessage", back_populates="learner", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True, index=True)
    # Associa a mensagem ao ID do perfil do aluno
    learner_id = Column(Integer, ForeignKey('learner_profiles.id'), nullable=False, index=True)

    # 'user' para aluno, 'assistant' para a IA (Curumim)
    sender = Column(String, nullable=False)

    # Usamos Text em vez de String para suportar mensagens mais longas
    content = Column(Text, nullable=False)

    # Para registrar se foi texto, áudio transcrito, etc.
    message_type = Column(String, default='text')

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relacionamento reverso
    learner = relationship("LearnerProfile", back_populates="mensagens")


class MediaArtifact(Base):
    __tablename__ = 'media_artifacts'

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey('learner_profiles.id'), nullable=False, index=True)
    artifact_type = Column(String, default='audio')
    local_path = Column(String, nullable=False)
    mime_type = Column(String, default='audio/ogg')
    # pending | ready | sent | failed
    status = Column(String, default='ready')

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    learner = relationship("LearnerProfile", backref="artifacts")


class InteractionRecord(Base):
    __tablename__ = 'interaction_records'

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey('learner_profiles.id'), nullable=False, index=True)
    correlation_id = Column(String, index=True)
    # inbound | outbound
    direction = Column(String, nullable=False)
    # JSON
    payload_snapshot = Column(Text)
    response_text = Column(Text)
    # received | processed | sent | failed
    status = Column(String, default='received')

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    learner = relationship("LearnerProfile", backref="interactions")


def _adicionar_coluna_se_faltar(conn_engine, tabela: str, coluna: str, tipo: str):
    """Adiciona uma coluna em tabela existente sem quebrar o banco em produção."""
    from sqlalchemy import inspect, text
    colunas = [c['name'] for c in inspect(conn_engine).get_columns(tabela)]
    if coluna not in colunas:
        with conn_engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}"))


def inicializar_banco():
    """Cria o arquivo do banco e as tabelas se não existirem."""
    Base.metadata.create_all(engine)
    _adicionar_coluna_se_faltar(engine, 'learner_profiles', 'display_name', 'VARCHAR')
    _adicionar_coluna_se_faltar(engine, 'learner_profiles', 'last_seen_at', 'DATETIME')