"""
Testes de integração para data_processing_geral.py (modo Workload Geral)

Verifica que salvar_cenario_geral_no_banco:
- Cria um Scenario com mode='Geral' (não 'Workload Geral')
- Salva todas as tarefas (TaskGeral) vinculadas ao cenário
- Preserva campos como cost_center_name e activity_name
- Retorna o ID do cenário criado
- Retorna None em caso de erro interno
"""

from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import pytest

from data_processing_geral import salvar_cenario_geral_no_banco
from database import Scenario, TaskGeral


def _make_df_geral(num_rows: int = 3) -> pd.DataFrame:
    """DataFrame mínimo simulando a saída de load_and_process_geral."""
    return pd.DataFrame(
        {
            "Project Name": ["Projeto Geral"] * num_rows,
            "Activity Name": [f"Atividade {i}" for i in range(num_rows)],
            "CostCenter Name": ["CC 001"] * num_rows,
            "Resource Name": [f"Recurso {i}" for i in range(num_rows)],
            "Horas_Alocadas": [15.0, 25.0, 35.0][:num_rows],
            "Planned start": [date(2025, 2, 1)] * num_rows,
            "Planned finish": [date(2025, 4, 30)] * num_rows,
            "Mes": ["02/2025", "03/2025", "04/2025"][:num_rows],
        }
    )


class TestSalvarCenarioGeralNoBanco:
    def test_creates_scenario_record(self, db_session):
        df = _make_df_geral()
        salvar_cenario_geral_no_banco(df, nome_cenario="Baseline Geral", autor="Tester")

        scenario = db_session.query(Scenario).filter_by(name="Baseline Geral").first()
        assert scenario is not None

    def test_scenario_mode_is_geral_not_workload_geral(self, db_session):
        """
        O modo deve ser 'Geral', não 'Workload Geral'.
        Este teste documenta o requisito que garante compatibilidade com o
        comparador de versões, que filtra por Scenario.mode == 'Geral'.
        """
        df = _make_df_geral()
        salvar_cenario_geral_no_banco(df, nome_cenario="Cenário Geral")

        scenario = db_session.query(Scenario).filter_by(name="Cenário Geral").first()
        assert scenario.mode == "Geral"
        assert scenario.mode != "Workload Geral"

    def test_scenario_author_is_saved(self, db_session):
        df = _make_df_geral()
        salvar_cenario_geral_no_banco(df, nome_cenario="Cenário Geral", autor="Pedro")

        scenario = db_session.query(Scenario).filter_by(name="Cenário Geral").first()
        assert scenario.author == "Pedro"

    def test_saves_correct_number_of_tasks(self, db_session):
        df = _make_df_geral(num_rows=3)
        salvar_cenario_geral_no_banco(df, nome_cenario="Cenário Geral")

        tasks = db_session.query(TaskGeral).all()
        assert len(tasks) == 3

    def test_tasks_have_correct_workload_hours(self, db_session):
        df = _make_df_geral(num_rows=3)
        salvar_cenario_geral_no_banco(df, nome_cenario="Cenário Geral")

        hours = sorted(t.workload_hours for t in db_session.query(TaskGeral).all())
        assert hours == [15.0, 25.0, 35.0]

    def test_tasks_cost_center_is_saved(self, db_session):
        df = _make_df_geral(num_rows=2)
        salvar_cenario_geral_no_banco(df, nome_cenario="Cenário Geral")

        tasks = db_session.query(TaskGeral).all()
        assert all(t.cost_center_name == "CC 001" for t in tasks)

    def test_tasks_linked_to_created_scenario(self, db_session):
        df = _make_df_geral(num_rows=2)
        scenario_id = salvar_cenario_geral_no_banco(df, nome_cenario="Cenário Geral")

        tasks = db_session.query(TaskGeral).all()
        assert all(t.scenario_id == scenario_id for t in tasks)

    def test_returns_integer_scenario_id(self, db_session):
        df = _make_df_geral()
        result = salvar_cenario_geral_no_banco(df, nome_cenario="Cenário Geral")

        assert result is not None
        assert isinstance(result, int)
        assert result > 0

    def test_returns_none_when_commit_fails(self, monkeypatch):
        """Retorna None quando o commit lança uma exceção."""
        import data_processing_geral

        mock_db = MagicMock()
        mock_db.commit.side_effect = Exception("Erro simulado de commit")

        monkeypatch.setattr(data_processing_geral, "SessionLocal", lambda: mock_db)

        df = _make_df_geral()
        result = salvar_cenario_geral_no_banco(df, nome_cenario="Erro Test")
        assert result is None

    def test_activity_names_are_saved(self, db_session):
        df = _make_df_geral(num_rows=2)
        salvar_cenario_geral_no_banco(df, nome_cenario="Cenário Geral")

        activity_names = {t.activity_name for t in db_session.query(TaskGeral).all()}
        assert activity_names == {"Atividade 0", "Atividade 1"}

    def test_single_task_df(self, db_session):
        df = _make_df_geral(num_rows=1)
        scenario_id = salvar_cenario_geral_no_banco(df, nome_cenario="Single Task Geral")

        assert scenario_id is not None
        assert db_session.query(TaskGeral).count() == 1
