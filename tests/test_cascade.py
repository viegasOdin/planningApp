import pytest
import pandas as pd
import sys
import os
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import parse_dependencies, aplicar_cascata

def test_parse_dependencies():
    """Testa se o regex entende os padrões do MS Project (FS, SS, FF, SF e Lag)."""
    # Padrão normal (assume FS)
    assert parse_dependencies("15") == [{'id': '15', 'type': 'FS', 'lag': 0}]
    
    # Com tipo explícito
    assert parse_dependencies("12SS") == [{'id': '12', 'type': 'SS', 'lag': 0}]
    
    # Com tipo e Lag positivo
    assert parse_dependencies("10FS+2") == [{'id': '10', 'type': 'FS', 'lag': 2}]
    
    # Com Lag negativo e espaços
    assert parse_dependencies("8 FF - 1") == [{'id': '8', 'type': 'FF', 'lag': -1}]
    
    # Múltiplas dependências
    res = parse_dependencies("15; 16SS+2")
    assert len(res) == 2
    assert res[0] == {'id': '15', 'type': 'FS', 'lag': 0}
    assert res[1] == {'id': '16', 'type': 'SS', 'lag': 2}

@patch('utils.registrar_log')
def test_aplicar_cascata_inteligente(mock_log):
    """Testa se a cascata respeita as regras de FS e SS."""
    df_mock = pd.DataFrame({
        'Line identifier': ['1', '2', '3'],
        'Task Code': ['TC1', 'TC2', 'TC3'],
        'Activity Name': ['A1', 'A2', 'A3'],
        'Resource Name': ['R1', 'R2', 'R3'],
        'Planned start': [pd.to_datetime('2024-01-01'), pd.to_datetime('2024-01-05'), pd.to_datetime('2024-01-01')],
        'Planned finish': [pd.to_datetime('2024-01-04'), pd.to_datetime('2024-01-10'), pd.to_datetime('2024-01-10')],
        'Horas_Alocadas': [40, 20, 20],
        'Mes': ['01/2024', '01/2024', '01/2024'],
        'Predecessor': ['', '1FS', '1SS'], # 2 é FS de 1. 3 é SS de 1.
        'Successor': ['2;3', '', ''],
        'RTC_ID': ['', '', '']
    })
    
    # Simulamos que a Tarefa 1 atrasou o FIM em 2 dias úteis, mas o INÍCIO continuou igual (0 dias)
    df_novo, qtd = aplicar_cascata(df_mock, '1', delta_start_bdays=0, delta_finish_bdays=2, usuario='victor')
    
    # A tarefa 2 (FS) deve ter se movido 2 dias para frente
    df_succ_fs = df_novo[df_novo['Line identifier'] == '2']
    nova_data_inicio_fs = pd.to_datetime(df_succ_fs['Planned start'].iloc[0]).date()
    assert nova_data_inicio_fs == pd.to_datetime('2024-01-09').date() # 05/01 + 2 dias úteis = 09/01
    
    # A tarefa 3 (SS) NÃO deve ter se movido, pois o início da Tarefa 1 não mudou (delta_start = 0)
    df_succ_ss = df_novo[df_novo['Line identifier'] == '3']
    nova_data_inicio_ss = pd.to_datetime(df_succ_ss['Planned start'].iloc[0]).date()
    assert nova_data_inicio_ss == pd.to_datetime('2024-01-01').date() # Ficou igual!