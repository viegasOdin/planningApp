from database import SessionLocal, AuditLog
from datetime import datetime

def registrar_log(user_id, action, table_affected, record_id, field_changed, old_value, new_value):
    """
    Grava um registro de alteração no banco de dados na tabela audit_logs.
    """
    db = SessionLocal()
    try:
        novo_log = AuditLog(
            user_id=user_id,
            action=action,
            table_affected=table_affected,
            record_id=record_id,
            field_changed=field_changed,
            old_value=str(old_value),
            new_value=str(new_value),
            timestamp=datetime.now()
        )
        db.add(novo_log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Erro ao salvar log de auditoria: {e}")
    finally:
        db.close()