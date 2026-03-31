from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Date
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

# Cria a conexão com o banco de dados SQLite local
engine = create_engine('sqlite:///app_database.db', echo=False)

# Classe base para criar os modelos (tabelas)
Base = declarative_base()

# ==========================================
# 1. TABELA DE CENÁRIOS (Para versionamento)
# ==========================================
class Scenario(Base):
    __tablename__ = 'scenarios'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    mode = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    author = Column(String)
    is_baseline = Column(Boolean, default=False)
    
    tasks_odyc = relationship("TaskOdyc", back_populates="scenario", cascade="all, delete-orphan")
    tasks_geral = relationship("TaskGeral", back_populates="scenario", cascade="all, delete-orphan")

# ==========================================
# 2. TABELA DE TAREFAS - MODO ODYC
# ==========================================
class TaskOdyc(Base):
    __tablename__ = 'tasks_odyc'
    
    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey('scenarios.id'))
    
    project_name = Column(String)
    task_code = Column(String)
    line_identifier = Column(String)
    resource_name = Column(String)
    
    planned_start = Column(DateTime)
    planned_finish = Column(DateTime)
    workload_hours = Column(Float)
    
    scenario = relationship("Scenario", back_populates="tasks_odyc")

# ==========================================
# 3. TABELA DE TAREFAS - MODO GERAL
# ==========================================
class TaskGeral(Base):
    __tablename__ = 'tasks_geral'
    
    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey('scenarios.id'))
    
    project_name = Column(String)
    activity_name = Column(String)
    cost_center_name = Column(String)
    resource_name = Column(String)
    
    planned_start = Column(DateTime)
    planned_finish = Column(DateTime)
    workload_hours = Column(Float)
    
    scenario = relationship("Scenario", back_populates="tasks_geral")

# ==========================================
# 4. TABELA DE LOG DE AUDITORIA (Histórico)
# ==========================================
class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    action = Column(String)
    table_affected = Column(String)
    record_id = Column(String)
    field_changed = Column(String)
    old_value = Column(String)
    new_value = Column(String)
    timestamp = Column(DateTime, default=datetime.now)

# ==========================================
# 5. TABELA DE DEPENDÊNCIAS (Predecessoras)
# ==========================================
class TaskDependency(Base):
    __tablename__ = 'task_dependencies'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, nullable=False)
    depends_on_task_id = Column(Integer, nullable=False)
    dependency_type = Column(String, default="FS")
    lag_days = Column(Integer, default=0)
    mode = Column(String)

# ==========================================
# 6. TABELA DE FÉRIAS E AUSÊNCIAS (NOVIDADE)
# ==========================================
class ResourceAbsence(Base):
    __tablename__ = 'resource_absences'
    
    id = Column(Integer, primary_key=True)
    resource_name = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(String, default="Férias") # Férias, Licença, Folga, etc.
    registered_by = Column(String) # Quem cadastrou
    created_at = Column(DateTime, default=datetime.now)

# ==========================================
# FUNÇÕES DE INICIALIZAÇÃO
# ==========================================
def init_db():
    """Cria todas as tabelas no banco de dados, se não existirem."""
    Base.metadata.create_all(engine)
    print("Banco de dados SQLite inicializado com sucesso!")

SessionLocal = sessionmaker(bind=engine)

if __name__ == "__main__":
    init_db()