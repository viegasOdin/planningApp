import pandas as pd
import numpy as np
from datetime import datetime

def load_and_process_geral(arquivo_geral):
    df_capacity_raw = pd.read_excel(arquivo_geral, sheet_name="Hours by Month", skiprows=3)
    
    col_class = df_capacity_raw.columns[0]
    df_capacity_raw = df_capacity_raw.rename(columns={col_class: 'ClassBR'})
    
    colunas_data_cap = [col for col in df_capacity_raw.columns if col != 'ClassBR' and not str(col).startswith('Unnamed')]
    
    df_capacidade = pd.melt(df_capacity_raw, id_vars=['ClassBR'], value_vars=colunas_data_cap, var_name='Mes_Raw', value_name='Horas_Uteis')
    
    def format_month(val):
        try:
            if isinstance(val, datetime):
                return val.strftime('%m/%Y')
            return pd.to_datetime(val).strftime('%m/%Y')
        except:
            return str(val)
            
    df_capacidade['Mes'] = df_capacidade['Mes_Raw'].apply(format_month)
    df_capacidade['Horas_Uteis'] = pd.to_numeric(df_capacidade['Horas_Uteis'], errors='coerce').fillna(180)
    df_capacidade = df_capacidade.drop(columns=['Mes_Raw'])

    df_db = pd.read_excel(arquivo_geral, sheet_name="DataBase-Hours")
    
    colunas_fixas = [
        'ClassBR', 'OBS code & desc', 'CT |BO ID |PG |OH', 'Project Name', 'Local ID', 
        'Schedule Name', 'Task Code', 'Activity Name', 'Start', 'Finish', 'Resource ID', 
        'Resource Name', 'SoA', 'Filters', 'CostCenter', 'CostCenter Name', 'DH', 
        'Resource Category', 'Free text1', 'Free text2'
    ]
    
    colunas_fixas_existentes = [col for col in colunas_fixas if col in df_db.columns]
    colunas_meses = [col for col in df_db.columns if col not in colunas_fixas_existentes and not str(col).startswith('Unnamed')]
    
    df_alocacao = pd.melt(df_db, id_vars=colunas_fixas_existentes, value_vars=colunas_meses, var_name='Mes_Raw', value_name='Horas_Alocadas')
    
    df_alocacao['Horas_Alocadas'] = df_alocacao['Horas_Alocadas'].astype(str).str.replace(',', '.')
    df_alocacao['Horas_Alocadas'] = pd.to_numeric(df_alocacao['Horas_Alocadas'], errors='coerce').fillna(0)
    df_alocacao = df_alocacao[df_alocacao['Horas_Alocadas'] > 0]
    
    df_alocacao['Planned start'] = pd.to_datetime(df_alocacao['Start'], errors='coerce').dt.date
    df_alocacao['Planned finish'] = pd.to_datetime(df_alocacao['Finish'], errors='coerce').dt.date
    df_alocacao['Mes'] = df_alocacao['Mes_Raw'].apply(format_month)
    
    df_alocacao['Project Name'] = df_alocacao['Project Name'].fillna('Sem Projeto').astype(str)
    df_alocacao['Activity Name'] = df_alocacao['Activity Name'].fillna('N/A').astype(str)
    df_alocacao['Resource Name'] = df_alocacao['Resource Name'].fillna('Não Atribuído').astype(str)
    df_alocacao['CostCenter Name'] = df_alocacao['CostCenter Name'].fillna('N/A').astype(str)
    
    df_alocacao['RTC_ID'] = ""
    
    return df_alocacao, df_capacidade