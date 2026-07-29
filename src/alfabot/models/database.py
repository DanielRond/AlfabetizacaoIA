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


def inicializar_banco():
    """Cria o arquivo do banco e as tabelas se não existirem."""
    Base.metadata.create_all(engine)