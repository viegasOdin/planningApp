"""
Testes unitários para visualizations.py

Cobre calcular_dias_uteis_ferias: cálculo de dias úteis de férias dentro de
um determinado mês, usada para descontar capacidade no Heatmap.
"""

import pandas as pd
import pytest

from visualizations import calcular_dias_uteis_ferias


class TestCalcularDiasUteisFerias:
    """
    Testes para calcular_dias_uteis_ferias(mes_str, start_date, end_date)

    A função retorna a quantidade de dias úteis de um período de ausência
    que caem dentro do mês informado.
    """

    def test_no_overlap_vacation_before_month(self):
        """Férias terminam antes do mês: deve retornar 0."""
        result = calcular_dias_uteis_ferias("02/2025", "2025-01-01", "2025-01-31")
        assert result == 0

    def test_no_overlap_vacation_after_month(self):
        """Férias começam depois do mês: deve retornar 0."""
        result = calcular_dias_uteis_ferias("01/2025", "2025-02-01", "2025-02-28")
        assert result == 0

    def test_full_month_coverage(self):
        """Férias cobrindo o mês inteiro: retorna todos os dias úteis do mês."""
        result = calcular_dias_uteis_ferias("01/2025", "2025-01-01", "2025-01-31")
        expected = len(pd.bdate_range("2025-01-01", "2025-01-31"))
        assert result == expected

    def test_partial_month_first_two_weeks(self):
        """Férias apenas nas primeiras duas semanas do mês."""
        result = calcular_dias_uteis_ferias("01/2025", "2025-01-01", "2025-01-15")
        expected = len(pd.bdate_range("2025-01-01", "2025-01-15"))
        assert result == expected

    def test_vacation_spanning_into_next_month_counts_only_current(self):
        """Férias que cruzam o fim do mês: conta somente dias úteis no mês alvo."""
        # Férias de 20/01 a 10/02 — verificando em janeiro
        result = calcular_dias_uteis_ferias("01/2025", "2025-01-20", "2025-02-10")
        expected = len(pd.bdate_range("2025-01-20", "2025-01-31"))
        assert result == expected

    def test_vacation_spanning_from_previous_month_counts_only_current(self):
        """Férias que começam no mês anterior: conta somente dias úteis no mês alvo."""
        # Férias de 20/01 a 10/02 — verificando em fevereiro
        result = calcular_dias_uteis_ferias("02/2025", "2025-01-20", "2025-02-10")
        expected = len(pd.bdate_range("2025-02-01", "2025-02-10"))
        assert result == expected

    def test_weekend_only_vacation_returns_zero(self):
        """Férias apenas em fim de semana: nenhum dia útil."""
        # 04-05/01/2025 é sábado e domingo
        result = calcular_dias_uteis_ferias("01/2025", "2025-01-04", "2025-01-05")
        assert result == 0

    def test_single_business_day(self):
        """Férias de exatamente um dia útil."""
        # 06/01/2025 é segunda-feira
        result = calcular_dias_uteis_ferias("01/2025", "2025-01-06", "2025-01-06")
        assert result == 1

    def test_result_is_integer(self):
        """O tipo de retorno deve ser int."""
        result = calcular_dias_uteis_ferias("01/2025", "2025-01-06", "2025-01-10")
        assert isinstance(result, int)

    def test_vacation_exactly_on_month_boundary_start(self):
        """Férias começando exatamente no primeiro dia do mês."""
        result = calcular_dias_uteis_ferias("03/2025", "2025-03-01", "2025-03-15")
        expected = len(pd.bdate_range("2025-03-01", "2025-03-15"))
        assert result == expected

    def test_vacation_exactly_on_month_boundary_end(self):
        """Férias terminando exatamente no último dia do mês."""
        result = calcular_dias_uteis_ferias("03/2025", "2025-03-15", "2025-03-31")
        expected = len(pd.bdate_range("2025-03-15", "2025-03-31"))
        assert result == expected
