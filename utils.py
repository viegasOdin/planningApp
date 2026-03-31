import pandas as pd
import math
import re
from database import SessionLocal, AuditLog
from datetime import datetime

def registrar_log(user_id, action, table_affected, record_id, field_changed, old_value, new_value):
    db = SessionLocal()
    try:
        novo_log = AuditLog(
            user_id=user_id,
            action=action,
            table_affected=table_affected,
            record_id=str(record_id),
            field_changed=field_changed,
            old_value=str(old_value),
            new_value=str(new_value),
            timestamp=datetime.now()
        )
        db.add(novo_log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Erro ao salvar log de auditoria: {e}")
    finally:
        db.close()

def extract_ids(dependency_string):
    """Extrai apenas os IDs numéricos (mantido para compatibilidade visual)."""
    if pd.isna(dependency_string) or str(dependency_string).strip() == '': 
        return []
    parts = str(dependency_string).split(';')
    ids = []
    for p in parts:
        match = re.match(r'^[\d\.]+', str(p).strip())
        if match: 
            ids.append(match.group())
    return ids

def parse_dependencies(dependency_string):
    """Extrai ID, Tipo (FS, SS, FF, SF) e Lag de uma string de dependência."""
    if pd.isna(dependency_string) or str(dependency_string).strip() == '': 
        return []
    parts = str(dependency_string).split(';')
    deps = []
    for p in parts:
        p = p.strip().upper()
        # Regex: Pega o ID (números), o Tipo (letras opcionais) e o Lag (+/- números opcionais)
        match = re.match(r'^([\d\.]+)\s*(FS|SS|FF|SF)?\s*([+-]\s*\d+)?', p)
        if match:
            dep_id = match.group(1)
            dep_type = match.group(2) if match.group(2) else 'FS' # Padrão é FS
            lag_str = match.group(3)
            lag = int(lag_str.replace(' ', '')) if lag_str else 0
            deps.append({'id': dep_id, 'type': dep_type, 'lag': lag})
    return deps

def aplicar_cascata(df, start_line_id, delta_start_bdays, delta_finish_bdays, usuario, table_affected="tasks_odyc"):
    """
    Empurra as sucessoras baseando-se no tipo de dependência (FS, SS, FF, SF).
    """
    if delta_start_bdays == 0 and delta_finish_bdays == 0:
        return df, 0
        
    df_novo = df.copy()
    qtd_afetadas = 0
    
    # Fila de processamento: (ID da tarefa que mudou, delta_start, delta_finish)
    to_process = [(str(start_line_id), delta_start_bdays, delta_finish_bdays)]
    processed_ids = set([str(start_line_id)])
    
    # Mapeamento de Predecessora -> Lista de Sucessoras com seus Tipos
    dep_map = {}
    for _, row in df_novo[['Line identifier', 'Predecessor']].drop_duplicates().iterrows():
        l_id = str(row['Line identifier'])
        deps = parse_dependencies(row['Predecessor'])
        for d in deps:
            p_id = d['id']
            if p_id not in dep_map:
                dep_map[p_id] = []
            dep_map[p_id].append({'id': l_id, 'type': d['type']})
            
    while to_process:
        current_id, d_start, d_finish = to_process.pop(0)
        
        if current_id in dep_map:
            for succ in dep_map[current_id]:
                s_id = succ['id']
                rel_type = succ['type']
                
                if s_id in processed_ids:
                    continue
                    
                # Determina o quanto a sucessora vai andar baseado no tipo de relação
                shift_bdays = 0
                if rel_type in ['FS', 'FF']:
                    shift_bdays = d_finish
                elif rel_type in ['SS', 'SF']:
                    shift_bdays = d_start
                    
                if shift_bdays != 0:
                    df_succ = df_novo[df_novo['Line identifier'] == s_id]
                    if df_succ.empty: continue
                    
                    succ_res_group = df_succ.groupby('Resource Name').agg({
                        'Planned start': 'first', 'Planned finish': 'first',
                        'Horas_Alocadas': 'sum', 'Task Code': 'first',
                        'Activity Name': 'first', 'RTC_ID': 'first',
                        'Predecessor': 'first', 'Successor': 'first'
                    }).reset_index()
                    
                    df_novo = df_novo[df_novo['Line identifier'] != s_id]
                    novas_linhas_succ = []
                    
                    for _, s_row in succ_res_group.iterrows():
                        if pd.isnull(s_row['Planned start']) or pd.isnull(s_row['Planned finish']):
                            continue
                            
                        old_start_succ = pd.to_datetime(s_row['Planned start'])
                        old_finish_succ = pd.to_datetime(s_row['Planned finish'])
                        horas_totais_succ = s_row['Horas_Alocadas']
                        
                        # Empurra as datas usando dias úteis
                        new_start_succ = (old_start_succ + pd.offsets.BDay(shift_bdays)).date()
                        new_finish_succ = (old_finish_succ + pd.offsets.BDay(shift_bdays)).date()
                        
                        dias_uteis_succ = pd.date_range(start=new_start_succ, end=new_finish_succ, freq='B')
                        if len(dias_uteis_succ) == 0: dias_uteis_succ = [pd.to_datetime(new_start_succ)]
                        horas_por_dia_succ = horas_totais_succ / len(dias_uteis_succ)
                        
                        df_dias_succ = pd.DataFrame({'Data': dias_uteis_succ})
                        df_dias_succ['Mes'] = df_dias_succ['Data'].dt.strftime('%m/%Y')
                        df_dias_succ['Horas'] = horas_por_dia_succ
                        df_meses_succ = df_dias_succ.groupby('Mes')['Horas'].sum().reset_index()
                        
                        for _, row_mes_succ in df_meses_succ.iterrows():
                            novas_linhas_succ.append({
                                'Line identifier': s_id,
                                'Task Code': s_row['Task Code'],
                                'Activity Name': s_row['Activity Name'],
                                'Resource Name': s_row['Resource Name'],
                                'Planned start': new_start_succ,
                                'Planned finish': new_finish_succ,
                                'Horas_Alocadas': row_mes_succ['Horas'],
                                'Mes': row_mes_succ['Mes'],
                                'Predecessor': s_row['Predecessor'],
                                'Successor': s_row['Successor'],
                                'RTC_ID': s_row['RTC_ID']
                            })
                    
                    if novas_linhas_succ:
                        df_novo = pd.concat([df_novo, pd.DataFrame(novas_linhas_succ)], ignore_index=True)
                        qtd_afetadas += 1
                        processed_ids.add(s_id)
                        # A sucessora andou, então ela passa esse shift para frente
                        to_process.append((s_id, shift_bdays, shift_bdays))
                        
                        registrar_log(
                            user_id=usuario,
                            action="UPDATE",
                            table_affected=table_affected,
                            record_id=s_id,
                            field_changed=f"Datas (Cascata {rel_type})",
                            old_value=f"Início: {old_start_succ.date().strftime('%d/%m/%Y')}",
                            new_value=f"Início: {new_start_succ.strftime('%d/%m/%Y')} ({shift_bdays:+} dias úteis)"
                        )
                        
    return df_novo, qtd_afetadas