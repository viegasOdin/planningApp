"""
Testes de integração para database.py

Verifica as operações CRUD dos modelos SQLAlchemy usando banco em memória:
- Scenario (criação, relacionamentos, defaults)
- TaskOdyc (criação, FK, cascade delete)
- TaskGeral (criação, FK, cascade delete)
- ResourceAbsence (criação, query por recurso)
- AuditLog (criação)
- registrar_log de utils.py (persistência no banco)
"""

from datetime import date, datetime

import pytest

from database import AuditLog, ResourceAbsence, Scenario, TaskGeral, TaskOdyc
from utils import registrar_log


class TestScenario:
    def test_create_scenario_odyc(self, db_session):
        scenario = Scenario(name="Cenário OdyC", mode="OdyC", author="Tester")
        db_session.add(scenario)
        db_session.commit()

        saved = db_session.query(Scenario).filter_by(name="Cenário OdyC").first()
        assert saved is not None
        assert saved.mode == "OdyC"
        assert saved.author == "Tester"

    def test_create_scenario_geral(self, db_session):
        scenario = Scenario(name="Cenário Geral", mode="Geral")
        db_session.add(scenario)
        db_session.commit()

        saved = db_session.query(Scenario).filter_by(name="Cenário Geral").first()
        assert saved.mode == "Geral"

    def test_is_baseline_defaults_to_false(self, db_session):
        scenario = Scenario(name="Test", mode="OdyC")
        db_session.add(scenario)
        db_session.commit()

        saved = db_session.query(Scenario).first()
        assert saved.is_baseline is False

    def test_created_at_is_set_automatically(self, db_session):
        scenario = Scenario(name="Test", mode="OdyC")
        db_session.add(scenario)
        db_session.commit()

        saved = db_session.query(Scenario).first()
        assert saved.created_at is not None
        assert isinstance(saved.created_at, datetime)

    def test_id_is_assigned_after_commit(self, db_session):
        scenario = Scenario(name="Test", mode="OdyC")
        db_session.add(scenario)
        db_session.commit()

        assert scenario.id is not None
        assert isinstance(scenario.id, int)


class TestTaskOdyc:
    def test_create_task_linked_to_scenario(self, db_session):
        scenario = Scenario(name="Test", mode="OdyC")
        db_session.add(scenario)
        db_session.commit()

        task = TaskOdyc(
            scenario_id=scenario.id,
            project_name="Projeto A",
            task_code="T001",
            resource_name="João",
            workload_hours=80.0,
        )
        db_session.add(task)
        db_session.commit()

        saved = db_session.query(TaskOdyc).first()
        assert saved.scenario_id == scenario.id
        assert saved.resource_name == "João"
        assert saved.workload_hours == 80.0

    def test_cascade_delete_removes_tasks_when_scenario_deleted(self, db_session):
        scenario = Scenario(name="Test", mode="OdyC")
        db_session.add(scenario)
        db_session.commit()

        db_session.add(TaskOdyc(scenario_id=scenario.id, resource_name="João", workload_hours=10.0))
        db_session.commit()
        assert db_session.query(TaskOdyc).count() == 1

        db_session.delete(scenario)
        db_session.commit()

        assert db_session.query(TaskOdyc).count() == 0

    def test_scenario_tasks_odyc_relationship(self, db_session):
        scenario = Scenario(name="Test", mode="OdyC")
        db_session.add(scenario)
        db_session.commit()

        for i in range(3):
            db_session.add(TaskOdyc(scenario_id=scenario.id, resource_name=f"R{i}", workload_hours=float(i * 10)))
        db_session.commit()

        db_session.refresh(scenario)
        assert len(scenario.tasks_odyc) == 3

    def test_multiple_tasks_belong_to_same_scenario(self, db_session):
        scenario = Scenario(name="Test", mode="OdyC")
        db_session.add(scenario)
        db_session.commit()

        db_session.add(TaskOdyc(scenario_id=scenario.id, resource_name="A", workload_hours=5.0))
        db_session.add(TaskOdyc(scenario_id=scenario.id, resource_name="B", workload_hours=15.0))
        db_session.commit()

        tasks = db_session.query(TaskOdyc).filter_by(scenario_id=scenario.id).all()
        assert len(tasks) == 2


class TestTaskGeral:
    def test_create_task_geral_linked_to_scenario(self, db_session):
        scenario = Scenario(name="Geral Test", mode="Geral")
        db_session.add(scenario)
        db_session.commit()

        task = TaskGeral(
            scenario_id=scenario.id,
            project_name="Projeto X",
            activity_name="Atividade Y",
            cost_center_name="CC 100",
            resource_name="Maria",
            workload_hours=40.0,
        )
        db_session.add(task)
        db_session.commit()

        saved = db_session.query(TaskGeral).first()
        assert saved.cost_center_name == "CC 100"
        assert saved.resource_name == "Maria"
        assert saved.workload_hours == 40.0

    def test_cascade_delete_removes_tasks_geral(self, db_session):
        scenario = Scenario(name="Test", mode="Geral")
        db_session.add(scenario)
        db_session.commit()

        db_session.add(TaskGeral(scenario_id=scenario.id, resource_name="Maria", workload_hours=20.0))
        db_session.commit()
        assert db_session.query(TaskGeral).count() == 1

        db_session.delete(scenario)
        db_session.commit()

        assert db_session.query(TaskGeral).count() == 0

    def test_scenario_tasks_geral_relationship(self, db_session):
        scenario = Scenario(name="Test", mode="Geral")
        db_session.add(scenario)
        db_session.commit()

        for i in range(2):
            db_session.add(TaskGeral(scenario_id=scenario.id, resource_name=f"R{i}", workload_hours=10.0))
        db_session.commit()

        db_session.refresh(scenario)
        assert len(scenario.tasks_geral) == 2


class TestResourceAbsence:
    def test_create_absence(self, db_session):
        absence = ResourceAbsence(
            resource_name="Carlos",
            start_date=date(2025, 7, 1),
            end_date=date(2025, 7, 30),
            reason="Férias",
            registered_by="Admin",
        )
        db_session.add(absence)
        db_session.commit()

        saved = db_session.query(ResourceAbsence).first()
        assert saved.resource_name == "Carlos"
        assert saved.start_date == date(2025, 7, 1)
        assert saved.end_date == date(2025, 7, 30)
        assert saved.reason == "Férias"

    def test_reason_defaults_to_ferias(self, db_session):
        absence = ResourceAbsence(
            resource_name="Ana",
            start_date=date(2025, 8, 1),
            end_date=date(2025, 8, 15),
        )
        db_session.add(absence)
        db_session.commit()

        saved = db_session.query(ResourceAbsence).first()
        assert saved.reason == "Férias"

    def test_query_absences_by_resource_name(self, db_session):
        db_session.add(ResourceAbsence(resource_name="Ana", start_date=date(2025, 7, 1), end_date=date(2025, 7, 10)))
        db_session.add(ResourceAbsence(resource_name="Bob", start_date=date(2025, 8, 1), end_date=date(2025, 8, 5)))
        db_session.add(ResourceAbsence(resource_name="Ana", start_date=date(2025, 9, 1), end_date=date(2025, 9, 15)))
        db_session.commit()

        ana_absences = db_session.query(ResourceAbsence).filter_by(resource_name="Ana").all()
        assert len(ana_absences) == 2

    def test_created_at_is_set_automatically(self, db_session):
        absence = ResourceAbsence(
            resource_name="Test",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 10),
        )
        db_session.add(absence)
        db_session.commit()

        saved = db_session.query(ResourceAbsence).first()
        assert saved.created_at is not None


class TestAuditLog:
    def test_create_audit_log(self, db_session):
        log = AuditLog(
            user_id="admin",
            action="CREATE",
            table_affected="scenarios",
            record_id="1",
            field_changed="Nova Entrada",
            old_value="",
            new_value="Criado",
        )
        db_session.add(log)
        db_session.commit()

        saved = db_session.query(AuditLog).first()
        assert saved.user_id == "admin"
        assert saved.action == "CREATE"
        assert saved.table_affected == "scenarios"

    def test_timestamp_set_automatically(self, db_session):
        log = AuditLog(user_id="user", action="UPDATE", table_affected="tasks_odyc", record_id="5")
        db_session.add(log)
        db_session.commit()

        saved = db_session.query(AuditLog).first()
        assert saved.timestamp is not None


class TestRegistrarLog:
    """Testes de integração para utils.registrar_log."""

    def test_registrar_log_persists_record(self, db_session):
        registrar_log(
            user_id="tester",
            action="CREATE",
            table_affected="resource_absences",
            record_id="João",
            field_changed="Nova Ausência",
            old_value="",
            new_value="Férias: 01/07/2025 a 30/07/2025",
        )

        log = db_session.query(AuditLog).filter_by(user_id="tester").first()
        assert log is not None
        assert log.action == "CREATE"
        assert log.table_affected == "resource_absences"
        assert log.record_id == "João"

    def test_registrar_log_converts_record_id_to_string(self, db_session):
        registrar_log("user", "UPDATE", "tasks_odyc", 42, "Planned start", "01/01/2025", "05/01/2025")

        log = db_session.query(AuditLog).first()
        assert log.record_id == "42"

    def test_multiple_logs_are_all_persisted(self, db_session):
        registrar_log("userA", "CREATE", "scenarios", "1", "Nome", "", "Cenário 1")
        registrar_log("userB", "UPDATE", "scenarios", "1", "Nome", "Cenário 1", "Cenário 1 Rev")

        logs = db_session.query(AuditLog).all()
        assert len(logs) == 2
