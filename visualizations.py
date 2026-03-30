import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import re
from database import SessionLocal, AuditLog  # <-- NOVIDADE: Importando o banco de dados

def extract_ids(dependency_string):
    if pd.isna(dependency_string) or str(dependency_string).strip() == '':
        return []
    parts = str(dependency_string).split(';')
    ids = []
    for p in parts:
        match = re.match(r'^[\d\.]+', str(p).strip())
        if match:
            ids.append(match.group())
    return ids

def render_dashboard(df_master, key_suffix=""):
    st.subheader("📈 Visão Geral de Horas (SCADA)")
    
    df_valid = df_master.dropna(subset=['Planned start', 'Planned finish']).copy()
    if df_valid.empty:
        st.warning("Sem dados para exibir.")
        return
        
    df_valid['Mes_Date'] = pd.to_datetime(df_valid['Mes'], format='%m/%Y')
    min_date = df_valid['Mes_Date'].min().date()
    max_date = df_valid['Mes_Date'].max().date()
    
    col_filt1, col_filt2 = st.columns([1, 2])
    with col_filt1:
        datas_selecionadas = st.date_input("📅 Filtrar por Período:", value=(min_date, max_date), min_value=min_date, max_value=max_date, key=f"data_dash_{key_suffix}")
        
    if len(datas_selecionadas) == 2:
        data_inicio, data_fim = datas_selecionadas
        df_valid = df_valid[(df_valid['Mes_Date'].dt.date >= data_inicio.replace(day=1)) & (df_valid['Mes_Date'].dt.date <= data_fim)]
        
    if df_valid.empty:
        st.warning("Nenhum dado encontrado para o período selecionado.")
        return

    total_horas = df_valid['Horas_Alocadas'].sum()
    total_tarefas = df_valid[['Task Code', 'Activity Name']].drop_duplicates().shape[0]
    total_recursos = df_valid['Resource Name'].nunique()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Horas Alocadas", f"{total_horas:,.1f}h")
    col2.metric("Total de Tarefas", total_tarefas)
    col3.metric("Recursos Envolvidos", total_recursos)
    
    st.write("---")
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        st.write("**Horas por Mês**")
        df_mes = df_valid.groupby('Mes')['Horas_Alocadas'].sum().reset_index()
        df_mes['Mes_Date'] = pd.to_datetime(df_mes['Mes'], format='%m/%Y')
        df_mes = df_mes.sort_values('Mes_Date')
        fig_mes = px.bar(df_mes, x='Mes', y='Horas_Alocadas', text_auto='.1f', color_discrete_sequence=['#3498db'])
        st.plotly_chart(fig_mes, use_container_width=True, key=f"dash_mes_{key_suffix}")
        
    with col_graf2:
        st.write("**Horas por Recurso**")
        df_rec = df_valid.groupby('Resource Name')['Horas_Alocadas'].sum().reset_index().sort_values('Horas_Alocadas', ascending=True)
        fig_rec = px.bar(df_rec, y='Resource Name', x='Horas_Alocadas', orientation='h', text_auto='.1f', color_discrete_sequence=['#9b59b6'])
        st.plotly_chart(fig_rec, use_container_width=True, key=f"dash_rec_{key_suffix}")

def render_changelog(df_original, df_simulado):
    st.subheader("🕵️‍♂️ Histórico de Auditoria (Logs)")
    st.write("Acompanhe todas as alterações feitas no sistema, quem fez e quando.")
    
    # --- NOVIDADE: BUSCA DIRETO DO BANCO DE DADOS ---
    db = SessionLocal()
    try:
        # Busca os logs da tabela OdyC, ordenados do mais recente para o mais antigo
        logs = db.query(AuditLog).filter(AuditLog.table_affected == "tasks_odyc").order_by(AuditLog.timestamp.desc()).all()
        
        if not logs:
            st.info("Nenhuma alteração registrada no banco de dados ainda.")
        else:
            # Converte os logs do banco para uma lista de dicionários para o Pandas
            dados_log = []
            for log in logs:
                dados_log.append({
                    "Data/Hora": log.timestamp.strftime("%d/%m/%Y %H:%M:%S"),
                    "Usuário": log.user_id.title(),
                    "Ação": "➕ Criação" if log.action == "CREATE" else "✏️ Edição" if log.action == "UPDATE" else "❌ Exclusão",
                    "ID/Tarefa Afetada": log.record_id,
                    "Campo Alterado": log.field_changed,
                    "Valor Antigo": log.old_value,
                    "Novo Valor": log.new_value
                })
            
            df_logs = pd.DataFrame(dados_log)
            
            # Filtros rápidos para a tabela de logs
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                busca_user = st.selectbox("Filtrar por Usuário:", ["Todos"] + sorted(df_logs['Usuário'].unique().tolist()))
            with col_f2:
                busca_acao = st.selectbox("Filtrar por Ação:", ["Todas", "➕ Criação", "✏️ Edição", "❌ Exclusão"])
                
            if busca_user != "Todos":
                df_logs = df_logs[df_logs['Usuário'] == busca_user]
            if busca_acao != "Todas":
                df_logs = df_logs[df_logs['Ação'] == busca_acao]
            
            st.dataframe(df_logs, use_container_width=True, hide_index=True)
            
            # Botão de exportação
            csv = df_logs.to_csv(index=False, sep=';', encoding='utf-8-sig')
            st.download_button(label="📥 Exportar Histórico Completo (CSV)", data=csv, file_name="historico_auditoria_odyc.csv", mime="text/csv")
            
    except Exception as e:
        st.error(f"Erro ao carregar logs: {e}")
    finally:
        db.close()
            
    st.write("---")
    st.write("### 🚨 Alertas de Conflito (Predecessoras)")
    
    if 'ignored_conflicts' not in st.session_state:
        st.session_state['ignored_conflicts'] = []
        
    df_tarefas = df_simulado.groupby(['Line identifier', 'Task Code', 'Activity Name']).agg({
        'Planned start': 'first', 'Planned finish': 'first', 'Predecessor': 'first'
    }).reset_index()
    
    conflitos = []
    dict_fins = dict(zip(df_tarefas['Line identifier'].astype(str), df_tarefas['Planned finish']))
    
    for _, row in df_tarefas.iterrows():
        inicio_atual = row['Planned start']
        preds = extract_ids(row['Predecessor'])
        
        for p_id in preds:
            if p_id in dict_fins:
                fim_predecessora = dict_fins[p_id]
                if pd.notnull(inicio_atual) and pd.notnull(fim_predecessora) and inicio_atual < fim_predecessora:
                    nome_pred = df_tarefas[df_tarefas['Line identifier'].astype(str) == p_id]['Activity Name'].values[0]
                    conflitos.append({
                        'Tarefa com Problema': f"[{row['Line identifier']}] {row['Activity Name']}",
                        'Início Planejado': inicio_atual.strftime('%d/%m/%Y'),
                        'Predecessora (Causa)': f"[{p_id}] {nome_pred}",
                        'Fim da Predecessora': fim_predecessora.strftime('%d/%m/%Y'),
                        'Conflict_ID': f"{row['Line identifier']}_{p_id}"
                    })
                    
    if conflitos:
        df_conflitos = pd.DataFrame(conflitos)
        df_conflitos_ativos = df_conflitos[~df_conflitos['Conflict_ID'].isin(st.session_state['ignored_conflicts'])].copy()
        
        if not df_conflitos_ativos.empty:
            st.error(f"Foram encontrados {len(df_conflitos_ativos)} conflitos de dependência ativos!")
            
            df_conflitos_ativos.insert(0, 'Ignorar', False)
            
            edited_conflitos = st.data_editor(
                df_conflitos_ativos.drop(columns=['Conflict_ID']), hide_index=True, use_container_width=True,
                column_config={"Ignorar": st.column_config.CheckboxColumn("Ocultar?", default=False)}
            )
            
            col_ign1, col_ign2, col_ign3 = st.columns([2, 2, 2])
            with col_ign1:
                if st.button("👁️ Ocultar Selecionados"):
                    mask_ignore = edited_conflitos['Ignorar'] == True
                    if mask_ignore.any():
                        ignored_to_add = df_conflitos_ativos[mask_ignore]['Conflict_ID'].tolist()
                        st.session_state['ignored_conflicts'].extend(ignored_to_add)
                        st.success("Alertas ocultados!")
                        st.rerun()
            with col_ign2:
                if st.button("🙈 Ocultar TODOS os Alertas"):
                    st.session_state['ignored_conflicts'].extend(df_conflitos_ativos['Conflict_ID'].tolist())
                    st.success("Todos os alertas foram ocultados!")
                    st.rerun()
            with col_ign3:
                if len(st.session_state['ignored_conflicts']) > 0:
                    if st.button("🔄 Restaurar Alertas"):
                        st.session_state['ignored_conflicts'] = []
                        st.rerun()
        else:
            st.success("✅ Todos os conflitos detectados foram marcados como ignorados.")
            if st.button("🔄 Restaurar Alertas Ocultos"):
                st.session_state['ignored_conflicts'] = []
                st.rerun()
    else:
        st.success("✅ O cronograma está íntegro. Nenhuma tarefa inicia antes de sua predecessora terminar.")
        if len(st.session_state['ignored_conflicts']) > 0:
            st.session_state['ignored_conflicts'] = []

def render_gantt(df_master, key_suffix=""):
    st.subheader("📊 Gráfico de Gantt (Cronograma)")
    
    df_valid_dates = df_master.dropna(subset=['Planned start', 'Planned finish']).copy()
    
    if df_valid_dates.empty:
        st.warning("Nenhuma tarefa com datas válidas encontrada.")
        return

    df_gantt = df_valid_dates.groupby(['Line identifier', 'Task Code', 'Activity Name', 'Planned start', 'Planned finish']).agg({
        'Resource Name': lambda x: ', '.join(x.unique()),
        'Horas_Alocadas': 'sum'
    }).reset_index()

    col1, col2 = st.columns(2)
    
    with col1:
        recurso_busca = st.text_input("🔍 Filtrar por Recurso (digite parte do nome):", "", key=f"busca_gantt_{key_suffix}").strip().lower()
        
    with col2:
        min_date = df_gantt['Planned start'].min()
        max_date = df_gantt['Planned finish'].max()
        datas_selecionadas = st.date_input("📅 Filtrar por Período:", value=(min_date, max_date), min_value=min_date, max_value=max_date, key=f"data_gantt_{key_suffix}")

    df_filtrado = df_gantt.copy()
    
    if recurso_busca:
        df_filtrado = df_filtrado[df_filtrado['Resource Name'].str.lower().str.contains(recurso_busca, na=False)]
        
    if len(datas_selecionadas) == 2:
        data_inicio, data_fim = datas_selecionadas
        df_filtrado = df_filtrado[(df_filtrado['Planned start'] <= data_fim) & (df_filtrado['Planned finish'] >= data_inicio)].copy()
        df_filtrado['Visual_Start'] = df_filtrado['Planned start'].apply(lambda x: max(x, data_inicio))
        df_filtrado['Visual_Finish'] = df_filtrado['Planned finish'].apply(lambda x: min(x, data_fim))
    else:
        df_filtrado['Visual_Start'] = df_filtrado['Planned start']
        df_filtrado['Visual_Finish'] = df_filtrado['Planned finish']

    if df_filtrado.empty:
        st.warning("Nenhuma tarefa encontrada com os filtros atuais.")
        return

    fig = px.timeline(
        df_filtrado, x_start="Visual_Start", x_end="Visual_Finish", y="Activity Name", color="Task Code", hover_name="Activity Name",
        hover_data={"Visual_Start": False, "Visual_Finish": False, "Planned start": True, "Planned finish": True, "Line identifier": True, "Resource Name": True, "Horas_Alocadas": True, "Task Code": True, "Activity Name": False}
    )
    
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=max(400, len(df_filtrado) * 30), showlegend=True, xaxis_title="Período", yaxis_title="Atividades")
    st.plotly_chart(fig, use_container_width=True, key=f"gantt_chart_{key_suffix}")

def render_heatmap(df_master, df_capacidade, key_suffix=""):
    st.subheader("🔥 Heatmap de Capacidade vs. Demanda")
    st.write("Visão de sobrecarga da equipe baseada nas horas úteis do mês.")
    
    df_master_copy = df_master.copy()
    df_master_copy['Mes_Date'] = pd.to_datetime(df_master_copy['Mes'], format='%m/%Y')
    
    # Garante que a coluna RTC_ID existe (caso venha de um save antigo)
    if 'RTC_ID' not in df_master_copy.columns:
        df_master_copy['RTC_ID'] = ""
        
    recursos_disponiveis = sorted(df_master_copy['Resource Name'].dropna().unique())
    min_date = df_master_copy['Mes_Date'].min().date()
    max_date = df_master_copy['Mes_Date'].max().date()
    
    with st.form(key=f'form_filtros_heatmap_{key_suffix}'):
        col1, col2 = st.columns(2)
        with col1:
            recursos_selecionados = st.multiselect("👥 Selecione os Recursos (Deixe vazio para ver todos):", options=recursos_disponiveis, default=[], key=f"recursos_heatmap_{key_suffix}")
        with col2:
            periodo_selecionado = st.date_input("📅 Período (Mês):", value=(min_date, max_date), min_value=min_date, max_value=max_date, key=f"data_heatmap_{key_suffix}")
        submit_button = st.form_submit_button(label='🚀 Aplicar Filtros')
        
    df_filtrado = df_master_copy.copy()
    
    if recursos_selecionados: df_filtrado = df_filtrado[df_filtrado['Resource Name'].isin(recursos_selecionados)]
        
    if len(periodo_selecionado) == 2:
        data_inicio, data_fim = periodo_selecionado
        df_filtrado = df_filtrado[(df_filtrado['Mes_Date'].dt.date >= data_inicio) & (df_filtrado['Mes_Date'].dt.date <= data_fim)]
        
    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    df_uso = df_filtrado.groupby(['Resource Name', 'Mes', 'Mes_Date'])['Horas_Alocadas'].sum().reset_index()
    df_heatmap = pd.merge(df_uso, df_capacidade, on='Mes', how='left')
    df_heatmap['Horas_Uteis'] = pd.to_numeric(df_heatmap['Horas_Uteis'], errors='coerce').fillna(180)
    df_heatmap['Taxa_Ocupacao'] = (df_heatmap['Horas_Alocadas'] / df_heatmap['Horas_Uteis']) * 100
    df_heatmap['Saldo_Horas'] = df_heatmap['Horas_Uteis'] - df_heatmap['Horas_Alocadas']
    df_heatmap = df_heatmap.sort_values('Mes_Date')
    
    matriz_uso = df_heatmap.pivot(index='Resource Name', columns='Mes', values='Taxa_Ocupacao').fillna(0)
    matriz_alocadas = df_heatmap.pivot(index='Resource Name', columns='Mes', values='Horas_Alocadas').fillna(0)
    matriz_uteis = df_heatmap.pivot(index='Resource Name', columns='Mes', values='Horas_Uteis').fillna(180)
    matriz_saldo = df_heatmap.pivot(index='Resource Name', columns='Mes', values='Saldo_Horas').fillna(180)
    
    meses_ordenados = df_heatmap['Mes'].unique()
    matriz_uso = matriz_uso[meses_ordenados]
    matriz_alocadas = matriz_alocadas[meses_ordenados]
    matriz_uteis = matriz_uteis[meses_ordenados]
    matriz_saldo = matriz_saldo[meses_ordenados]
    
    customdata = np.dstack((matriz_alocadas.values, matriz_uteis.values, matriz_saldo.values))
    escala_cores = [[0.0, '#f1c40f'], [0.533, '#f1c40f'], [0.533, '#2ecc71'], [0.799, '#2ecc71'], [0.799, '#e74c3c'], [1.0, '#e74c3c']]
    
    fig = px.imshow(
        matriz_uso, labels=dict(x="Mês", y="Recurso", color="% Ocupação"), x=matriz_uso.columns, y=matriz_uso.index,
        color_continuous_scale=escala_cores, zmin=0, zmax=150, aspect="auto", text_auto=".0f"
    )
    fig.update_traces(
        customdata=customdata,
        hovertemplate="<b>Recurso:</b> %{y}<br><b>Mês:</b> %{x}<br><b>Ocupação:</b> %{z:.0f}%<br><b>Horas Alocadas:</b> %{customdata[0]:.1f}h<br><b>Horas Úteis:</b> %{customdata[1]:.0f}h<br><b>Saldo:</b> %{customdata[2]:.1f}h<extra></extra>"
    )
    fig.update_xaxes(side="top")
    fig.update_layout(height=max(400, len(matriz_uso) * 40))
    st.plotly_chart(fig, use_container_width=True, key=f"heatmap_chart_{key_suffix}")

    # --- NOVIDADE: DRILL-DOWN COM EDIÇÃO DE RTC_ID ---
    st.write("---")
    st.write("### 🔍 Detalhamento do Mês e Inserção de RTC")
    st.write("Selecione um recurso e um mês. Você pode digitar o ID do RTC diretamente na tabela abaixo e salvar.")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        recursos_drill = sorted(df_filtrado['Resource Name'].unique())
        rec_selecionado = st.selectbox("👤 Recurso:", [""] + recursos_drill, key=f"drill_rec_{key_suffix}")
    with col_d2:
        meses_drill = sorted(df_filtrado['Mes'].unique(), key=lambda x: pd.to_datetime(x, format='%m/%Y'))
        mes_selecionado = st.selectbox("📅 Mês:", [""] + meses_drill, key=f"drill_mes_{key_suffix}")
        
    if rec_selecionado and mes_selecionado:
        df_drill = df_filtrado[(df_filtrado['Resource Name'] == rec_selecionado) & (df_filtrado['Mes'] == mes_selecionado)]
        if not df_drill.empty:
            # Trazemos o RTC_ID para a tabela
            df_drill_show = df_drill[['Line identifier', 'Task Code', 'Activity Name', 'Horas_Alocadas', 'RTC_ID']].copy()
            df_drill_show = df_drill_show[df_drill_show['Horas_Alocadas'] > 0].sort_values('Horas_Alocadas', ascending=False)
            
            total_mes = df_drill_show['Horas_Alocadas'].sum()
            st.success(f"**Total alocado para {rec_selecionado} em {mes_selecionado}:** {total_mes:.1f}h")
            
            with st.form(key=f"form_rtc_{key_suffix}"):
                # Configura a tabela para que APENAS a coluna RTC_ID seja editável
                config_colunas = {
                    "Line identifier": st.column_config.TextColumn(disabled=True),
                    "Task Code": st.column_config.TextColumn(disabled=True),
                    "Activity Name": st.column_config.TextColumn(disabled=True),
                    "Horas_Alocadas": st.column_config.NumberColumn(disabled=True, format="%.1f"),
                    "RTC_ID": st.column_config.TextColumn("ID do RTC (Editável)")
                }
                
                df_editado_rtc = st.data_editor(
                    df_drill_show, 
                    column_config=config_colunas, 
                    use_container_width=True, 
                    hide_index=True,
                    key=f"editor_rtc_{key_suffix}"
                )
                
                if st.form_submit_button("💾 Salvar IDs do RTC"):
                    df_novo = st.session_state['df_simulado'].copy()
                    
                    # Atualiza o RTC_ID no banco de dados principal para cada linha editada
                    for _, row in df_editado_rtc.iterrows():
                        l_id = row['Line identifier']
                        t_code = row['Task Code']
                        a_name = row['Activity Name']
                        novo_rtc = row['RTC_ID']
                        
                        # Aplica o RTC_ID em TODAS as linhas dessa tarefa (independente do mês)
                        mask = (df_novo['Line identifier'] == l_id) & (df_novo['Task Code'] == t_code) & (df_novo['Activity Name'] == a_name)
                        df_novo.loc[mask, 'RTC_ID'] = novo_rtc
                        
                    st.session_state['df_simulado'] = df_novo
                    st.success("✅ IDs do RTC atualizados com sucesso e vinculados às tarefas!")
                    st.rerun()
        else:
            st.info("Nenhuma hora alocada para este recurso neste mês.")