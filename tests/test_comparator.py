import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
import sys
import os
from datetime import datetime

# Adiciona a pasta principal ao caminho do Python para ele achar o comparator.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comparator import get_scenarios, get_tasks_df

@patch('comparator.SessionLocal')
def test_get_scenarios(mock_session_local):
    """
    Testa se a função get_scenarios busca os cenários e formata o dicionário corretamente.
    """
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    
    # Criamos cenários falsos para simular o retorno do banco de dados
    mock_scenario_1 = MagicMock()
    mock_scenario_1.id = 1
    mock_scenario_1.name = "Cenário Inicial"
    mock_scenario_1.created_at = datetime(2024, 5, 10, 10, 0)
    mock_scenario_1.author = "victor"
    
    mock_scenario_2 = MagicMock()
    mock_scenario_2.id = 2
    mock_scenario_2.name = "Cenário Ajustado"
    mock_scenario_2.created_at = datetime(2024, 5, 12, 15, 30)
    mock_scenario_2.author = "joao"
    
    # Simulamos a query retornando os cenários
    mock_db.query().filter().order_by().all.return_value = [mock_scenario_2, mock_scenario_1]
    
    # Executamos a função
    resultado = get_scenarios("OdyC")
    
    # Verificamos se o dicionário foi montado corretamente para o Selectbox do Streamlit
    assert len(resultado) == 2
    chave_esperada = "ID 2 | Cenário Ajustado (12/05/2024 15:30) - por joao"
    assert chave_esperada in resultado
    assert resultado[chave_esperada] == 2

@patch('comparator.SessionLocal')
def test_get_tasks_df_odyc(mock_session_local):
    """
    Testa se a função get_tasks_df busca as tarefas do OdyC e converte para DataFrame.
    """
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    
    # Criamos uma tarefa falsa
    mock_task = MagicMock()
    mock_task.line_identifier = "ID-123"
    mock_task.task_code = "TC-99"
    mock_task.resource_name = "Recurso A"
    mock_task.planned_start = "2024-01-01"
    mock_task.planned_finish = "2024-01-31"
    mock_task.workload_hours = 40.5
    
    mock_db.query().filter().all.return_value = [mock_task]
    
    # Executamos a função
    df = get_tasks_df(1, "OdyC")
    
    # Verificamos se o DataFrame foi criado corretamente
    assert not df.empty
    assert len(df) == 1
    assert df.iloc[0]['Task Code'] == "TC-99"
    assert df.iloc[0]['Horas_Alocadas'] == 40.5
    assert df.iloc[0]['Line identifier'] == "ID-123"