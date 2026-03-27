import pandas as pd
import numpy as np

def load_and_process_data(arquivo_wkl, arquivo_schedule):
    df_wkl = pd.read_excel(arquivo_wkl, sheet_name="DB_WKL")
    df_capacity_raw = pd.read_excel(arquivo_wkl, sheet_name="ByResource", header=None, nrows=2)
    df_planning = pd.read_excel(arquivo_wkl, sheet_name="Planning")
    df_schedule = pd.read_excel(arquivo_schedule, sheet_name="View 01")
    
    meses = df_capacity_raw.iloc[0, 4:].values
    horas = df_capacity_raw.iloc[1, 4:].values
    df_capacidade = pd.DataFrame({'Mes': meses, 'Horas_Uteis': horas}).dropna()
    df_capacidade['Mes'] = pd.to_datetime(df_capacidade['Mes']).dt.strftime('%m/%Y')
    
    df_wkl.columns = df_wkl.columns.astype(str)
    
    colunas_fixas = ['Task Code', 'Activity Name', 'Resource Name', 'Resource Category']
    if 'Start' in df_wkl.columns: colunas_fixas.append('Start')
    if 'Finish' in df_wkl.columns: colunas_fixas.append('Finish')
        
    colunas_meses = [col for col in df_wkl.columns if '202' in col or '203' in col]
    
    df_alocacao = pd.melt(df_wkl, id_vars=colunas_fixas, value_vars=colunas_meses, var_name='Mes', value_name='Horas_Alocadas')
    
    df_alocacao['Horas_Alocadas'] = df_alocacao['Horas_Alocadas'].astype(str).str.replace(',', '.')
    df_alocacao['Horas_Alocadas'] = pd.to_numeric(df_alocacao['Horas_Alocadas'], errors='coerce').fillna(0)
    df_alocacao = df_alocacao[df_alocacao['Horas_Alocadas'] > 0]
    df_alocacao['Mes'] = pd.to_datetime(df_alocacao['Mes']).dt.strftime('%m/%Y')
    
    df_alocacao['Task Code'] = df_alocacao['Task Code'].astype(str).str.strip().str.upper()
    df_alocacao['Activity Name'] = df_alocacao['Activity Name'].astype(str).str.strip().str.upper()
    df_planning['OdyC Task Code Name Task'] = df_planning['OdyC Task Code Name Task'].astype(str).str.strip().str.upper()
    df_planning['Description Activity'] = df_planning['Description Activity'].astype(str).str.strip().str.upper()
    df_planning['Line identifier Task'] = df_planning['Line identifier Task'].astype(str).str.replace('.0', '', regex=False).str.strip()
    df_schedule['Line identifier'] = df_schedule['Line identifier'].astype(str).str.replace('.0', '', regex=False).str.strip()
    
    df_ponte = df_planning[['OdyC Task Code Name Task', 'Description Activity', 'Line identifier Task']].drop_duplicates()
    df_master_step1 = pd.merge(df_alocacao, df_ponte, left_on=['Task Code', 'Activity Name'], right_on=['OdyC Task Code Name Task', 'Description Activity'], how='left')
    
    colunas_do_schedule = ['Line identifier', 'Planned start', 'Planned finish', 'Predecessor', 'Successor']
    df_master = pd.merge(df_master_step1, df_schedule[colunas_do_schedule], left_on='Line identifier Task', right_on='Line identifier', how='left')
    
    colunas_para_remover = ['OdyC Task Code Name Task', 'Description Activity', 'Line identifier Task']
    df_master = df_master.drop(columns=[col for col in colunas_para_remover if col in df_master.columns])
    
    if 'Start' in df_master.columns and 'Finish' in df_master.columns:
        df_master['Planned start'] = df_master['Planned start'].fillna(df_master['Start'])
        df_master['Planned finish'] = df_master['Planned finish'].fillna(df_master['Finish'])
        df_master = df_master.drop(columns=['Start', 'Finish'])
        
    df_master['Planned start'] = pd.to_datetime(df_master['Planned start'], errors='coerce').dt.date
    df_master['Planned finish'] = pd.to_datetime(df_master['Planned finish'], errors='coerce').dt.date
    
    df_master['Line identifier'] = df_master['Line identifier'].fillna('N/A')
    
    # NOVIDADE: Coluna para rastreio no RTC
    df_master['RTC_ID'] = ""
    
    return df_master, df_capacidade