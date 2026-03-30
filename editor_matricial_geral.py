import streamlit as st
import pandas as pd
import numpy as np
from utils import registrar_log  # <-- NOVIDADE: Importando nosso espião de logs

def render_editor_matricial_geral():
    st.subheader("📁 Visão e Edição Matricial por Projeto")
    st.write("Edite as horas diretamente. A tabela exibe a partir do mês inicial até **4 meses depois** da última entrega. Use os filtros de data para focar em um período específico.")
    
    df_geral = st.session_state['df_geral']
    
    # Pega o nome do usuário logado para colocar no Log
    usuario = st.session_state.get("usuario_logado", "Desconhecido") 
    
    col1, col2 = st.columns(2)
    projetos = ["Todos"] + sorted(df_geral['Project Name'].dropna().unique().tolist())
    proj_selecionado = col1.selectbox("🔍 Filtrar por Projeto:", projetos, key="mat_proj_geral")
    
    recursos = ["Todos"] + sorted(df_geral['Resource Name'].dropna().unique().tolist())
    rec_selecionado = col2.selectbox("👤 Filtrar por Recurso:", recursos, key="mat_rec_geral")
    
    # --- NOVIDADE: Filtros de Data ---
    col3, col4 = st.columns(2)
    data_inicio_filtro = col3.date_input("📅 Filtrar a partir de (Início):", value=None, key="mat_dt_ini_geral")
    data_fim_filtro = col4.date_input("📅 Filtrar até (Fim):", value=None, key="mat_dt_fim_geral")
    
    df_filtrado = df_geral.copy()
    if proj_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Project Name'] == proj_selecionado]
    if rec_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Resource Name'] == rec_selecionado]
        
    # Aplicar filtro de datas
    if data_inicio_filtro:
        df_filtrado = df_filtrado[pd.to_datetime(df_filtrado['Planned finish']).dt.date >= data_inicio_filtro]
    if data_fim_filtro:
        df_filtrado = df_filtrado[pd.to_datetime(df_filtrado['Planned start']).dt.date <= data_fim_filtro]
        
    if df_filtrado.empty:
        st.info("Nenhum dado encontrado para os filtros selecionados.")
        return

    # 1. Determinar o range de meses
    df_datas = df_filtrado.dropna(subset=['Planned start', 'Planned finish'])
    if df_datas.empty:
        st.warning("As tarefas filtradas não possuem datas válidas.")
        return
        
    min_date = pd.to_datetime(df_datas['Planned start'].min())
    max_date = pd.to_datetime(df_datas['Planned finish'].max())
    
    # Começa na data mais antiga (sem os 4 meses antes) ou na data do filtro
    start_range = min_date
    if data_inicio_filtro and pd.to_datetime(data_inicio_filtro) > min_date:
        start_range = pd.to_datetime(data_inicio_filtro)
        
    # Termina 4 meses após a data mais distante
    end_range = max_date + pd.DateOffset(months=4)
    
    todos_meses_dt = pd.date_range(start=start_range.replace(day=1), end=end_range, freq='MS')
    todos_meses_str = [dt.strftime('%m/%Y') for dt in todos_meses_dt]

    df_grouped = df_filtrado.groupby(['Project Name', 'Activity Name', 'Resource Name', 'Mes'])['Horas_Alocadas'].sum().reset_index()
    df_pivot = df_grouped.pivot_table(
        index=['Project Name', 'Activity Name', 'Resource Name'],
        columns='Mes',
        values='Horas_Alocadas',
        aggfunc='sum',
        fill_value=0.0
    ).reset_index()
    
    # 3. Garantir colunas apenas para o range visível
    for mes in todos_meses_str:
        if mes not in df_pivot.columns:
            df_pivot[mes] = 0.0
            
    meses_cols = todos_meses_str
    
    # Puxar o total geral da tarefa
    total_por_tarefa = df_grouped.groupby(['Project Name', 'Activity Name', 'Resource Name'])['Horas_Alocadas'].sum().reset_index()
    total_por_tarefa.rename(columns={'Horas_Alocadas': 'Total (Horas)'}, inplace=True)
    
    df_pivot = pd.merge(df_pivot, total_por_tarefa, on=['Project Name', 'Activity Name', 'Resource Name'], how='left')
    
    cols_exibicao = ['Project Name', 'Activity Name', 'Resource Name', 'Total (Horas)'] + meses_cols
    for col in cols_exibicao:
        if col not in df_pivot.columns:
            df_pivot[col] = 0.0
            
    df_pivot = df_pivot[cols_exibicao]
    
    config_colunas = {
        "Project Name": st.column_config.TextColumn(disabled=True),
        "Activity Name": st.column_config.TextColumn(disabled=True),
        "Resource Name": st.column_config.TextColumn(disabled=True),
        "Total (Horas)": st.column_config.NumberColumn("Total (Geral)", disabled=True, format="%.1f")
    }
    for mes in meses_cols:
        config_colunas[mes] = st.column_config.NumberColumn(mes, min_value=0.0, format="%.1f")
        
    with st.form("form_matricial_geral"):
        df_editado = st.data_editor(
            df_pivot,
            column_config=config_colunas,
            use_container_width=True,
            hide_index=True,
            key="editor_mat_geral_ui"
        )
        
        if st.form_submit_button("💾 Salvar Alterações Matriciais"):
            df_novo = st.session_state['df_geral'].copy()
            
            df_melted_original = df_pivot.melt(id_vars=['Project Name', 'Activity Name', 'Resource Name'], value_vars=meses_cols, var_name='Mes', value_name='Horas_Alocadas_orig')
            df_melted_editado = df_editado.melt(id_vars=['Project Name', 'Activity Name', 'Resource Name'], value_vars=meses_cols, var_name='Mes', value_name='Horas_Alocadas_novo')
            
            df_diff = pd.merge(df_melted_original, df_melted_editado, on=['Project Name', 'Activity Name', 'Resource Name', 'Mes'])
            df_changed = df_diff[df_diff['Horas_Alocadas_orig'] != df_diff['Horas_Alocadas_novo']]
            
            if df_changed.empty:
                st.warning("Nenhuma alteração detectada.")
            else:
                mudancas_feitas = 0
                
                for _, row in df_changed.iterrows():
                    p_name = row['Project Name']
                    a_name = row['Activity Name']
                    rec = row['Resource Name']
                    mes = row['Mes']
                    nova_hora = row['Horas_Alocadas_novo']
                    hora_antiga = row['Horas_Alocadas_orig']
                    
                    # --- REGISTRO DE LOG ---
                    registrar_log(
                        user_id=usuario,
                        action="UPDATE",
                        table_affected="tasks_geral",
                        record_id=f"{p_name} | {a_name}",
                        field_changed=f"Matriz: Horas de {rec} em {mes}",
                        old_value=f"{hora_antiga}h",
                        new_value=f"{nova_hora}h"
                    )
                    mudancas_feitas += 1
                    
                    mask = (df_novo['Project Name'] == p_name) & (df_novo['Activity Name'] == a_name) & (df_novo['Resource Name'] == rec) & (df_novo['Mes'] == mes)
                    
                    if mask.any():
                        indices = df_novo[mask].index
                        df_novo.loc[indices[0], 'Horas_Alocadas'] = nova_hora
                        if len(indices) > 1:
                            df_novo.loc[indices[1:], 'Horas_Alocadas'] = 0
                    else:
                        if nova_hora > 0:
                            mask_base = (df_novo['Project Name'] == p_name) & (df_novo['Activity Name'] == a_name) & (df_novo['Resource Name'] == rec)
                            if mask_base.any():
                                info_base = df_novo[mask_base].iloc[0].copy()
                                info_base['Mes'] = mes
                                info_base['Horas_Alocadas'] = nova_hora
                                df_novo = pd.concat([df_novo, pd.DataFrame([info_base])], ignore_index=True)
                
                # 4. RECALCULAR DATAS
                tarefas_alteradas = df_changed[['Project Name', 'Activity Name', 'Resource Name']].drop_duplicates()
                
                for _, row in tarefas_alteradas.iterrows():
                    p_name = row['Project Name']
                    a_name = row['Activity Name']
                    rec = row['Resource Name']
                    
                    mask_tarefa = (df_novo['Project Name'] == p_name) & (df_novo['Activity Name'] == a_name) & (df_novo['Resource Name'] == rec) & (df_novo['Horas_Alocadas'] > 0)
                    
                    if mask_tarefa.any():
                        meses_ativos = df_novo[mask_tarefa]['Mes'].tolist()
                        meses_dt = [pd.to_datetime(m, format='%m/%Y') for m in meses_ativos]
                        
                        novo_inicio = min(meses_dt).date()
                        novo_fim = (max(meses_dt) + pd.offsets.MonthEnd(0)).date()
                        
                        mask_update = (df_novo['Project Name'] == p_name) & (df_novo['Activity Name'] == a_name) & (df_novo['Resource Name'] == rec)
                        df_novo.loc[mask_update, 'Planned start'] = novo_inicio
                        df_novo.loc[mask_update, 'Planned finish'] = novo_fim

                st.session_state['df_geral'] = df_novo

                # Limpa cache de UI focado apenas nos editores
                prefixos = ['mat_', 'editor_', 'visao_', 'busca_', 'sel_', 'task_', 'proj_']
                for key in list(st.session_state.keys()):
                    if any(key.startswith(p) for p in prefixos):
                        del st.session_state[key]
                
                # Adicionado 'usuario_logado' aqui para não perder a sessão no log
                keys_to_keep = ['df_simulado', 'df_original', 'df_capacidade', 'ignored_conflicts', 'df_geral', 'df_original_geral', 'df_cap_geral', 'df_baseline_geral', 'logado', 'seletor_modo_global', 'usuario_logado']
                for key in list(st.session_state.keys()):
                    if key not in keys_to_keep and not key.startswith('FormSubmitter'):
                        del st.session_state[key]
                        
                st.success(f"✅ {mudancas_feitas} alterações salvas e datas recalculadas com sucesso!")
                st.rerun()