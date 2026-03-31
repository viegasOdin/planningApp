"""
Testes de integração para data_processing.py (modo OdyC)

Verifica que salvar_cenario_odyc_no_banco:
- Cria um Scenario com os campos corretos no banco
- Salva todas as tarefas (TaskOdyc) vinculadas ao cenário
- Retorna o ID do cenário criado
- Retorna None em caso de erro interno
"""

from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import pytest

from data_processing import salvar_cenario_odyc_no_banco
from database import Scenario, TaskOdyc


def _make_df_master(num_rows: int = 3) -> pd.DataFrame:
    """DataFrame mínimo simulando a saída de load_and_process_data."""
    return pd.DataFrame(
        {
            "Task Code": [f"T00{i}" for i in range(num_rows)],
            "Activity Name": [f"Atividade {i}" for i in range(num_rows)],
            "Resource Name": [f"Recurso {i}" for i in range(num_rows)],
            "Project Name": ["Projeto Teste"] * num_rows,
            "Line identifier": [f"L{i}" for i in range(num_rows)],
            "Horas_Alocadas": [10.0, 20.0, 30.0][:num_rows],
            "Planned start": [date(2025, 1, 1)] * num_rows,
            "Planned finish": [date(2025, 3, 31)] * num_rows,
            "Mes": ["01/2025", "02/2025", "03/2025"][:num_rows],
        }
    )


class TestSalvarCenarioOdycNoBanco:
    def test_creates_scenario_record(self, db_session):
        df = _make_df_master()
        salvar_cenario_odyc_no_banco(df, nome_cenario="Baseline OdyC", autor="Tester")

        scenario = db_session.query(Scenario).filter_by(name="Baseline OdyC").first()
        assert scenario is not None

    def test_scenario_mode_is_odyc(self, db_session):
        df = _make_df_master()
        salvar_cenario_odyc_no_banco(df, nome_cenario="Cenário OdyC")

        scenario = db_session.query(Scenario).filter_by(name="Cenário OdyC").first()
        assert scenario.mode == "OdyC"

    def test_scenario_author_is_saved(self, db_session):
        df = _make_df_master()
        salvar_cenario_odyc_no_banco(df, nome_cenario="Cenário OdyC", autor="Maria")

        scenario = db_session.query(Scenario).filter_by(name="Cenário OdyC").first()
        assert scenario.author == "Maria"

    def test_saves_correct_number_of_tasks(self, db_session):
        df = _make_df_master(num_rows=3)
        salvar_cenario_odyc_no_banco(df, nome_cenario="Cenário OdyC")

        tasks = db_session.query(TaskOdyc).all()
        assert len(tasks) == 3

    def test_tasks_have_correct_workload_hours(self, db_session):
        df = _make_df_master(num_rows=3)
        salvar_cenario_odyc_no_banco(df, nome_cenario="Cenário OdyC")

        hours = sorted(t.workload_hours for t in db_session.query(TaskOdyc).all())
        assert hours == [10.0, 20.0, 30.0]

    def test_tasks_linked_to_created_scenario(self, db_session):
        df = _make_df_master(num_rows=2)
        scenario_id = salvar_cenario_odyc_no_banco(df, nome_cenario="Cenário OdyC")

        tasks = db_session.query(TaskOdyc).all()
        assert all(t.scenario_id == scenario_id for t in tasks)

    def test_returns_integer_scenario_id(self, db_session):
        df = _make_df_master()
        result = salvar_cenario_odyc_no_banco(df, nome_cenario="Cenário OdyC")

        assert result is not None
        assert isinstance(result, int)
        assert result > 0

    def test_returns_none_when_commit_fails(self, monkeypatch):
        """Retorna None quando o commit lança uma exceção."""
        import data_processing

        mock_db = MagicMock()
        mock_db.commit.side_effect = Exception("Erro simulado de commit")

        monkeypatch.setattr(data_processing, "SessionLocal", lambda: mock_db)

        df = _make_df_master()
        result = salvar_cenario_odyc_no_banco(df, nome_cenario="Erro Test")
        assert result is None

    def test_tasks_resource_names_are_saved(self, db_session):
        df = _make_df_master(num_rows=2)
        salvar_cenario_odyc_no_banco(df, nome_cenario="Cenário OdyC")

        names = {t.resource_name for t in db_session.query(TaskOdyc).all()}
        assert names == {"Recurso 0", "Recurso 1"}

    def test_single_task_df(self, db_session):
        df = _make_df_master(num_rows=1)
        scenario_id = salvar_cenario_odyc_no_banco(df, nome_cenario="Single Task")

        assert scenario_id is not None
        assert db_session.query(TaskOdyc).count() == 1
