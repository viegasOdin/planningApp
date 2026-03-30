import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Adiciona a pasta principal ao caminho do Python para ele achar o utils.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import registrar_log

@patch('utils.SessionLocal')
def test_registrar_log_sucesso(mock_session_local):
    """
    Testa se a função registrar_log cria o objeto corretamente e tenta salvar no banco.
    """
    # 1. Configura o mock (simulador) do banco de dados
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    
    # 2. Executa a função que queremos testar
    registrar_log(
        user_id="victor",
        action="UPDATE",
        table_affected="tasks_odyc",
        record_id="TASK-123",
        field_changed="Horas_Alocadas",
        old_value="10.5",
        new_value="20.0"
    )
    
    # 3. Verifica se os comandos do banco foram chamados na ordem certa
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.close.assert_called_once()
    
    # 4. Verifica se os dados que a função tentou salvar estão corretos
    args, kwargs = mock_db.add.call_args
    log_adicionado = args[0]
    
    assert log_adicionado.user_id == "victor"
    assert log_adicionado.action == "UPDATE"
    assert log_adicionado.table_affected == "tasks_odyc"
    assert log_adicionado.record_id == "TASK-123"
    assert log_adicionado.field_changed == "Horas_Alocadas"
    assert log_adicionado.old_value == "10.5"
    assert log_adicionado.new_value == "20.0"

@patch('utils.SessionLocal')
def test_registrar_log_erro_banco(mock_session_local):
    """
    Testa se a função lida corretamente com um erro no banco de dados (fazendo rollback).
    """
    # 1. Configura o mock para simular uma falha (ex: banco caiu)
    mock_db = MagicMock()
    mock_db.commit.side_effect = Exception("Erro simulado de conexão")
    mock_session_local.return_value = mock_db
    
    # 2. Executa a função
    registrar_log(
        user_id="victor",
        action="DELETE",
        table_affected="tasks_geral",
        record_id="PROJ-999",
        field_changed="Status",
        old_value="Ativo",
        new_value="Excluído"
    )
    
    # 3. Verifica se o sistema foi inteligente e fez o rollback para não corromper o banco
    mock_db.add.assert_called_once()
    mock_db.rollback.assert_called_once() # O mais importante: garantiu que fez rollback!
    mock_db.close.assert_called_once()