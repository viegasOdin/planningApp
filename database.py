from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

# Cria a conexão com o banco de dados SQLite local
# O arquivo 'app_database.db' será criado automaticamente na sua pasta
engine = create_engine('sqlite:///app_database.db', echo=False)

# Classe base para criar os modelos (tabelas)
Base = declarative_base()

# ==========================================
# 1. TABELA DE CENÁRIOS (Para versionamento)
# ==========================================
class Scenario(Base):
    __tablename__ = 'scenarios'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False) # Ex: "Baseline Jan/2026", "Simulação Otimista"
    mode = Column(String, nullable=False) # "OdyC" ou "Geral"
    created_at = Column(DateTime, default=datetime.now)
    author = Column(String) # Quem criou o cenário
    is_baseline = Column(Boolean, default=False) # Marca se é uma foto oficial para comparação
    
    # Relações com as tarefas
    tasks_odyc = relationship("TaskOdyc", back_populates="scenario", cascade="all, delete-orphan")
    tasks_geral = relationship("TaskGeral", back_populates="scenario", cascade="all, delete-orphan")

# ==========================================
# 2. TABELA DE TAREFAS - MODO ODYC
# ==========================================
class TaskOdyc(Base):
    __tablename__ = 'tasks_odyc'
    
    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey('scenarios.id'))
    
    # Chaves de identificação do OdyC
    project_name = Column(String)
    task_code = Column(String)
    line_identifier = Column(String)
    resource_name = Column(String)
    
    # Dados de agendamento e carga
    planned_start = Column(DateTime)
    planned_finish = Column(DateTime)
    workload_hours = Column(Float)
    
    # Relação com o cenário
    scenario = relationship("Scenario", back_populates="tasks_odyc")

# ==========================================
# 3. TABELA DE TAREFAS - MODO GERAL
# ==========================================
class TaskGeral(Base):
    __tablename__ = 'tasks_geral'
    
    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey('scenarios.id'))
    
    # Chaves de identificação do Workload Geral
    project_name = Column(String)
    activity_name = Column(String)
    cost_center_name = Column(String)
    resource_name = Column(String)
    
    # Dados de agendamento e carga
    planned_start = Column(DateTime)
    planned_finish = Column(DateTime)
    workload_hours = Column(Float)
    
    # Relação com o cenário
    scenario = relationship("Scenario", back_populates="tasks_geral")

# ==========================================
# 4. TABELA DE LOG DE AUDITORIA (Histórico)
# ==========================================
class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False) # Quem alterou
    action = Column(String) # "CREATE", "UPDATE", "DELETE"
    table_affected = Column(String) # "tasks_odyc" ou "tasks_geral"
    record_id = Column(Integer) # ID da tarefa alterada
    field_changed = Column(String) # Ex: "planned_finish"
    old_value = Column(String)
    new_value = Column(String)
    timestamp = Column(DateTime, default=datetime.now)

# ==========================================
# 5. TABELA DE DEPENDÊNCIAS (Predecessoras)
# ==========================================
class TaskDependency(Base):
    __tablename__ = 'task_dependencies'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, nullable=False) # A tarefa que vai sofrer o impacto
    depends_on_task_id = Column(Integer, nullable=False) # A tarefa que dita a regra (predecessora)
    dependency_type = Column(String, default="FS") # FS (Finish-to-Start), SS (Start-to-Start), etc.
    lag_days = Column(Integer, default=0) # Dias de atraso/adiantamento
    mode = Column(String) # "OdyC" ou "Geral"

# ==========================================
# FUNÇÕES DE INICIALIZAÇÃO
# ==========================================
def init_db():
    """Cria todas as tabelas no banco de dados, se não existirem."""
    Base.metadata.create_all(engine)
    print("Banco de dados SQLite inicializado com sucesso!")

# Cria um 'fabricante de sessões' para usarmos nos outros arquivos
SessionLocal = sessionmaker(bind=engine)

# Se rodar este arquivo diretamente, ele cria o banco
if __name__ == "__main__":
    init_db()