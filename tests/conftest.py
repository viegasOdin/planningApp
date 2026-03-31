"""
Configuração central dos testes.

- Cria um banco de dados SQLite em memória (StaticPool) para que todos os
  testes compartilhem o mesmo banco sem tocar no arquivo de produção.
- Fixtures `db_session`, `clean_db` e `patch_session_local` são autouse onde
  necessário para garantir isolamento entre testes.
"""

import sys
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Garante que o diretório raiz do projeto está no path de importação
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (
    Base,
    Scenario,
    TaskOdyc,
    TaskGeral,
    ResourceAbsence,
    AuditLog,
    TaskDependency,
)

# ---------------------------------------------------------------------------
# Engine de teste em memória
# StaticPool: todas as conexões compartilham a mesma conexão SQLite subjacente,
# garantindo que sessões diferentes vejam os dados umas das outras.
# ---------------------------------------------------------------------------
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
Base.metadata.create_all(TEST_ENGINE)
TestSessionLocal = sessionmaker(bind=TEST_ENGINE)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """Sessão de banco de dados de teste para verificações diretas nos testes."""
    session = TestSessionLocal()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def clean_db():
    """
    Limpa todas as tabelas APÓS cada teste.
    Ordem respeitando FK constraints: filhas antes de pais.
    """
    yield
    session = TestSessionLocal()
    try:
        session.query(TaskOdyc).delete()
        session.query(TaskGeral).delete()
        session.query(Scenario).delete()
        session.query(ResourceAbsence).delete()
        session.query(AuditLog).delete()
        session.query(TaskDependency).delete()
        session.commit()
    finally:
        session.close()


@pytest.fixture(autouse=True)
def patch_session_local(monkeypatch):
    """
    Substitui SessionLocal em todos os módulos do projeto pelo factory de teste.
    Isso garante que nenhuma função chame o banco de dados de produção.
    """
    import database
    import data_processing
    import data_processing_geral
    import utils
    import visualizations

    monkeypatch.setattr(database, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(data_processing, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(data_processing_geral, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(utils, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(visualizations, "SessionLocal", TestSessionLocal)
