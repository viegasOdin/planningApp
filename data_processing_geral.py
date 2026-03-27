import pandas as pd
import numpy as np
from database import SessionLocal, Scenario, TaskGeral
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

def salvar_cenario_geral_no_banco(df_alocacao, nome_cenario="Baseline Inicial Geral", autor="Sistema"):
    """
    Pega o DataFrame Geral processado e salva no banco de dados SQLite.
    """
    db = SessionLocal()
    
    try:
        # 1. Cria o Cenário
        novo_cenario = Scenario(
            name=nome_cenario,
            mode="Geral",
            author=autor,
            is_baseline=True
        )
        db.add(novo_cenario)
        db.commit()
        db.refresh(novo_cenario)
        
        # 2. Converte o DataFrame para dicionários
        registros = df_alocacao.to_dict(orient='records')
        
        # 3. Cria os objetos TaskGeral
        tarefas_para_salvar = []
        for row in registros:
            tarefa = TaskGeral(
                scenario_id=novo_cenario.id,
                project_name=str(row.get('Project Name', '')),
                activity_name=str(row.get('Activity Name', '')),
                cost_center_name=str(row.get('CostCenter Name', '')),
                resource_name=str(row.get('Resource Name', '')),
                planned_start=pd.to_datetime(row.get('Planned start')) if pd.notnull(row.get('Planned start')) else None,
                planned_finish=pd.to_datetime(row.get('Planned finish')) if pd.notnull(row.get('Planned finish')) else None,
                workload_hours=float(row.get('Horas_Alocadas', 0))
            )
            tarefas_para_salvar.append(tarefa)
            
        # 4. Salva tudo de uma vez
        db.bulk_save_objects(tarefas_para_salvar)
        db.commit()
        print(f"Sucesso! {len(tarefas_para_salvar)} tarefas do Workload Geral salvas no cenário '{nome_cenario}'.")
        return novo_cenario.id
        
    except Exception as e:
        db.rollback()
        print(f"Erro ao salvar no banco Geral: {e}")
        return None
    finally:
        db.close()