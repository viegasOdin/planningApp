import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
import sys
import os

# Adiciona a pasta principal ao caminho do Python para ele achar os arquivos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_processing import load_and_process_data, salvar_cenario_odyc_no_banco

def test_load_and_process_data():
    """
    Testa se a função de limpeza e processamento de dados do OdyC funciona corretamente
    simulando a leitura de abas do Excel.
    """
    # 1. Criamos DataFrames falsos para simular as abas do Excel
    df_wkl_mock = pd.DataFrame({
        'Task Code': ['TC1', 'TC2'],
        'Activity Name': ['Act 1', 'Act 2'],
        'Resource Name': ['Rec A', 'Rec B'],
        'Resource Category': ['Cat 1', 'Cat 2'],
        'Start': ['2023-01-01', '2023-02-01'],
        'Finish': ['2023-01-31', '2023-02-28'],
        '01/2023': ['10,5', '0'],   # Simulando a vírgula brasileira
        '02/2023': ['0', '20,0']
    })
    
    df_capacity_mock = pd.DataFrame([
        ['lixo', 'lixo', 'lixo', 'lixo', '2023-01-01', '2023-02-01'],
        ['lixo', 'lixo', 'lixo', 'lixo', 160, 160]
    ])
    
    df_planning_mock = pd.DataFrame({
        'OdyC Task Code Name Task': ['TC1', 'TC2'],
        'Description Activity': ['ACT 1', 'ACT 2'],
        'Line identifier Task': ['ID1.0', 'ID2.0'] # Simulando o .0 chato do Excel
    })
    
    df_schedule_mock = pd.DataFrame({
        'Line identifier': ['ID1.0', 'ID2.0'],
        'Planned start': ['2023-01-01', '2023-02-01'],
        'Planned finish': ['2023-01-31', '2023-02-28'],
        'Predecessor': ['', 'ID1'],
        'Successor': ['ID2', '']
    })

    # 2. Função que decide qual DataFrame falso retornar dependendo da aba solicitada
    def mock_read_excel(*args, **kwargs):
        sheet = kwargs.get('sheet_name')
        if sheet == "DB_WKL": return df_wkl_mock
        elif sheet == "ByResource": return df_capacity_mock
        elif sheet == "Planning": return df_planning_mock
        elif sheet == "View 01": return df_schedule_mock
        return pd.DataFrame()

    # 3. Usamos o patch para substituir o pd.read_excel verdadeiro pelo nosso mock
    with patch('pandas.read_excel', side_effect=mock_read_excel):
        # Executamos a sua função original
        df_master, df_cap = load_and_process_data("dummy_wkl.xlsx", "dummy_schedule.xlsx")
        
        # 4. Verificações (Asserts) - Garantindo que a limpeza funcionou!
        assert not df_master.empty
        assert len(df_master) == 2 # Duas alocações válidas (>0)
        assert 'RTC_ID' in df_master.columns # Garante que a coluna nova foi criada
        assert df_master.iloc[0]['Horas_Alocadas'] == 10.5 # Garante que converteu vírgula pra ponto
        assert df_master.iloc[1]['Horas_Alocadas'] == 20.0
        assert df_master.iloc[0]['Line identifier'] == 'ID1' # Garante que limpou o .0

        assert not df_cap.empty
        assert len(df_cap) == 2
        assert df_cap.iloc[0]['Horas_Uteis'] == 160

@patch('data_processing.SessionLocal')
def test_salvar_cenario_odyc_no_banco(mock_session_local):
    """
    Testa se a função de salvar cenário OdyC interage corretamente com o banco.
    """
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    
    # Simula o retorno do ID do cenário gerado pelo banco
    def mock_refresh(obj):
        obj.id = 99
    mock_db.refresh.side_effect = mock_refresh
    
    # Dados falsos já limpos
    df_mock = pd.DataFrame({
        'Project Name': ['Proj 1'],
        'Task Code': ['TC1'],
        'Line identifier': ['ID1'],
        'Resource Name': ['Rec A'],
        'Planned start': ['2023-01-01'],
        'Planned finish': ['2023-01-31'],
        'Horas_Alocadas': [10.5]
    })
    
    # Executa a função
    cenario_id = salvar_cenario_odyc_no_banco(df_mock, "Cenário Teste", "victor")
    
    # Verifica se salvou e retornou o ID correto
    assert cenario_id == 99
    mock_db.add.assert_called_once() # Adicionou o cenário
    mock_db.bulk_save_objects.assert_called_once() # Adicionou as tarefas em lote
    assert mock_db.commit.call_count == 2 # Fez commit 2 vezes (cenário e tarefas)