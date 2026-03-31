"""
Testes unitários para as funções puras de filtragem do comparator.py

Cobre:
- get_filter_options: geração da união das opções de A e B
- apply_comparator_filters: aplicação dos filtros de recurso e projeto
"""

import pandas as pd
import pytest

from comparator import apply_comparator_filters, get_filter_options


# ---------------------------------------------------------------------------
# Fixtures de DataFrames reutilizáveis
# ---------------------------------------------------------------------------

@pytest.fixture
def df_odyc_a():
    return pd.DataFrame(
        {
            "Line identifier": ["L1", "L1", "L2", "L3"],
            "Task Code": ["TC-001", "TC-001", "TC-002", "TC-003"],
            "Resource Name": ["Alice", "Bob", "Alice", "Carlos"],
            "Horas_Alocadas": [40.0, 20.0, 30.0, 50.0],
        }
    )


@pytest.fixture
def df_odyc_b():
    return pd.DataFrame(
        {
            "Line identifier": ["L1", "L2", "L4"],
            "Task Code": ["TC-001", "TC-002", "TC-004"],
            "Resource Name": ["Alice", "Diana", "Bob"],
            "Horas_Alocadas": [45.0, 35.0, 25.0],
        }
    )


@pytest.fixture
def df_geral_a():
    return pd.DataFrame(
        {
            "Project Name": ["Projeto X", "Projeto X", "Projeto Y"],
            "Activity Name": ["Ativ A", "Ativ B", "Ativ C"],
            "Resource Name": ["Alice", "Bob", "Carlos"],
            "Horas_Alocadas": [60.0, 40.0, 80.0],
        }
    )


@pytest.fixture
def df_geral_b():
    return pd.DataFrame(
        {
            "Project Name": ["Projeto X", "Projeto Z"],
            "Activity Name": ["Ativ A", "Ativ D"],
            "Resource Name": ["Alice", "Diana"],
            "Horas_Alocadas": [70.0, 30.0],
        }
    )


# ---------------------------------------------------------------------------
# Testes de get_filter_options
# ---------------------------------------------------------------------------

class TestGetFilterOptions:
    def test_recursos_are_union_of_both_dfs_odyc(self, df_odyc_a, df_odyc_b):
        recursos_opts, _ = get_filter_options(df_odyc_a, df_odyc_b, "OdyC")
        assert set(recursos_opts) == {"Alice", "Bob", "Carlos", "Diana"}

    def test_recursos_are_union_of_both_dfs_geral(self, df_geral_a, df_geral_b):
        recursos_opts, _ = get_filter_options(df_geral_a, df_geral_b, "Geral")
        assert set(recursos_opts) == {"Alice", "Bob", "Carlos", "Diana"}

    def test_proj_options_use_task_code_for_odyc(self, df_odyc_a, df_odyc_b):
        _, proj_opts = get_filter_options(df_odyc_a, df_odyc_b, "OdyC")
        # A tem TC-001, TC-002, TC-003; B tem TC-001, TC-002, TC-004
        assert set(proj_opts) == {"TC-001", "TC-002", "TC-003", "TC-004"}

    def test_proj_options_use_project_name_for_geral(self, df_geral_a, df_geral_b):
        _, proj_opts = get_filter_options(df_geral_a, df_geral_b, "Geral")
        assert set(proj_opts) == {"Projeto X", "Projeto Y", "Projeto Z"}

    def test_result_is_sorted(self, df_odyc_a, df_odyc_b):
        recursos_opts, proj_opts = get_filter_options(df_odyc_a, df_odyc_b, "OdyC")
        assert recursos_opts == sorted(recursos_opts)
        assert proj_opts == sorted(proj_opts)

    def test_no_duplicates_when_same_resource_in_both(self, df_odyc_a, df_odyc_b):
        # "Alice" aparece em A e B — deve aparecer só uma vez
        recursos_opts, _ = get_filter_options(df_odyc_a, df_odyc_b, "OdyC")
        assert recursos_opts.count("Alice") == 1

    def test_exclusive_to_a_is_included(self, df_odyc_a, df_odyc_b):
        # "Carlos" está só em A
        recursos_opts, _ = get_filter_options(df_odyc_a, df_odyc_b, "OdyC")
        assert "Carlos" in recursos_opts

    def test_exclusive_to_b_is_included(self, df_odyc_a, df_odyc_b):
        # "Diana" está só em B
        recursos_opts, _ = get_filter_options(df_odyc_a, df_odyc_b, "OdyC")
        assert "Diana" in recursos_opts

    def test_handles_nan_in_resource_name(self):
        df_a = pd.DataFrame({"Resource Name": ["Alice", None], "Task Code": ["T1", "T2"], "Horas_Alocadas": [10.0, 5.0]})
        df_b = pd.DataFrame({"Resource Name": ["Bob"], "Task Code": ["T3"], "Horas_Alocadas": [20.0]})
        recursos_opts, _ = get_filter_options(df_a, df_b, "OdyC")
        assert None not in recursos_opts
        assert "Alice" in recursos_opts
        assert "Bob" in recursos_opts

    def test_empty_b_uses_only_a_options(self, df_odyc_a):
        df_b_empty = pd.DataFrame(columns=["Line identifier", "Task Code", "Resource Name", "Horas_Alocadas"])
        recursos_opts, _ = get_filter_options(df_odyc_a, df_b_empty, "OdyC")
        assert set(recursos_opts) == {"Alice", "Bob", "Carlos"}


# ---------------------------------------------------------------------------
# Testes de apply_comparator_filters
# ---------------------------------------------------------------------------

class TestApplyComparatorFilters:
    def test_empty_filters_return_full_dfs(self, df_odyc_a, df_odyc_b):
        df_a_f, df_b_f = apply_comparator_filters(df_odyc_a, df_odyc_b, "OdyC", [], [])
        assert len(df_a_f) == len(df_odyc_a)
        assert len(df_b_f) == len(df_odyc_b)

    def test_resource_filter_keeps_only_selected(self, df_odyc_a, df_odyc_b):
        df_a_f, df_b_f = apply_comparator_filters(df_odyc_a, df_odyc_b, "OdyC", ["Alice"], [])
        assert set(df_a_f["Resource Name"].unique()) == {"Alice"}
        assert set(df_b_f["Resource Name"].unique()) == {"Alice"}

    def test_resource_filter_applied_to_both_dfs(self, df_odyc_a, df_odyc_b):
        df_a_f, df_b_f = apply_comparator_filters(df_odyc_a, df_odyc_b, "OdyC", ["Bob"], [])
        # Bob está em A (1 linha) e B (1 linha)
        assert len(df_a_f) == 1
        assert len(df_b_f) == 1

    def test_resource_filter_not_in_df_returns_empty(self, df_odyc_a, df_odyc_b):
        df_a_f, df_b_f = apply_comparator_filters(df_odyc_a, df_odyc_b, "OdyC", ["Inexistente"], [])
        assert df_a_f.empty
        assert df_b_f.empty

    def test_proj_filter_odyc_uses_task_code(self, df_odyc_a, df_odyc_b):
        df_a_f, df_b_f = apply_comparator_filters(df_odyc_a, df_odyc_b, "OdyC", [], ["TC-001"])
        assert set(df_a_f["Task Code"].unique()) == {"TC-001"}
        assert set(df_b_f["Task Code"].unique()) == {"TC-001"}

    def test_proj_filter_geral_uses_project_name(self, df_geral_a, df_geral_b):
        df_a_f, df_b_f = apply_comparator_filters(df_geral_a, df_geral_b, "Geral", [], ["Projeto X"])
        assert set(df_a_f["Project Name"].unique()) == {"Projeto X"}
        assert set(df_b_f["Project Name"].unique()) == {"Projeto X"}

    def test_combined_filters_apply_both(self, df_odyc_a, df_odyc_b):
        # Recurso Alice + Task Code TC-001
        df_a_f, _ = apply_comparator_filters(df_odyc_a, df_odyc_b, "OdyC", ["Alice"], ["TC-001"])
        assert set(df_a_f["Resource Name"].unique()) == {"Alice"}
        assert set(df_a_f["Task Code"].unique()) == {"TC-001"}

    def test_original_dfs_not_mutated(self, df_odyc_a, df_odyc_b):
        original_len_a = len(df_odyc_a)
        original_len_b = len(df_odyc_b)
        apply_comparator_filters(df_odyc_a, df_odyc_b, "OdyC", ["Alice"], ["TC-001"])
        assert len(df_odyc_a) == original_len_a
        assert len(df_odyc_b) == original_len_b

    def test_multiple_resources_filter(self, df_odyc_a, df_odyc_b):
        df_a_f, _ = apply_comparator_filters(df_odyc_a, df_odyc_b, "OdyC", ["Alice", "Bob"], [])
        assert set(df_a_f["Resource Name"].unique()).issubset({"Alice", "Bob"})

    def test_proj_filter_exclusive_to_one_df(self, df_odyc_a, df_odyc_b):
        # TC-003 só existe em A, não em B
        df_a_f, df_b_f = apply_comparator_filters(df_odyc_a, df_odyc_b, "OdyC", [], ["TC-003"])
        assert not df_a_f.empty
        assert df_b_f.empty
