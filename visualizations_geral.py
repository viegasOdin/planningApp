import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
from database import SessionLocal, AuditLog  # <-- NOVIDADE: Importando o banco de dados

def render_dashboard_geral(df_master):
    st.subheader("📈 Visão Geral de Horas (Workload Geral)")
    
    df_valid = df_master.copy()
    if df_valid.empty:
        st.warning("Sem dados para exibir.")
        return
        
    df_valid['Mes_Date'] = pd.to_datetime(df_valid['Mes'], format='%m/%Y')
    min_date = df_valid['Mes_Date'].min().date()
    max_date = df_valid['Mes_Date'].max().date()
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        projetos_disponiveis = sorted(df_valid['Project Name'].unique())
        projetos_selecionados = st.multiselect("📁 Filtrar por Projeto(s):", options=projetos_disponiveis, default=[], key="dash_proj_filter")
    with col_f2:
        cc_disponiveis = sorted(df_valid['CostCenter Name'].unique())
        cc_selecionados = st.multiselect("🏢 Filtrar por CostCenter Name:", options=cc_disponiveis, default=[], key="dash_cc_filter")
    
    if projetos_selecionados:
        df_valid = df_valid[df_valid['Project Name'].isin(projetos_selecionados)]
    if cc_selecionados:
        df_valid = df_valid[df_valid['CostCenter Name'].isin(cc_selecionados)]
    
    col_filt1, col_filt2 = st.columns([1, 2])
    with col_filt1:
        datas_selecionadas = st.date_input("📅 Filtrar por Período:", value=(min_date, max_date), min_value=min_date, max_value=max_date, key="data_dash_geral")
        
    if len(datas_selecionadas) == 2:
        data_inicio, data_fim = datas_selecionadas
        df_valid = df_valid[(df_valid['Mes_Date'].dt.date >= data_inicio.replace(day=1)) & (df_valid['Mes_Date'].dt.date <= data_fim)]
        
    total_horas = df_valid['Horas_Alocadas'].sum()
    total_tarefas = df_valid[['Project Name', 'Activity Name']].drop_duplicates().shape[0]
    total_recursos = df_valid['Resource Name'].nunique()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Horas Alocadas", f"{total_horas:,.1f}h")
    col2.metric("Total de Atividades", total_tarefas)
    col3.metric("Recursos Envolvidos", total_recursos)
    
    st.write("---")
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        st.write("**Horas por Mês**")
        df_mes = df_valid.groupby('Mes')['Horas_Alocadas'].sum().reset_index()
        df_mes['Mes_Date'] = pd.to_datetime(df_mes['Mes'], format='%m/%Y')
        df_mes = df_mes.sort_values('Mes_Date')
        fig_mes = px.bar(df_mes, x='Mes', y='Horas_Alocadas', text_auto='.1f', color_discrete_sequence=['#2ecc71'])
        st.plotly_chart(fig_mes, use_container_width=True, key="dash_mes_geral")
        
    with col_graf2:
        st.write("**Horas por Projeto (Top 10)**")
        df_proj = df_valid.groupby('Project Name')['Horas_Alocadas'].sum().reset_index().sort_values('Horas_Alocadas', ascending=True).tail(10)
        fig_proj = px.bar(df_proj, y='Project Name', x='Horas_Alocadas', orientation='h', text_auto='.1f', color_discrete_sequence=['#e67e22'])
        st.plotly_chart(fig_proj, use_container_width=True, key="dash_proj_geral")

def render_gantt_geral(df_master):
    st.subheader("📊 Gráfico de Gantt (Workload Geral)")
    
    df_valid_dates = df_master.dropna(subset=['Planned start', 'Planned finish']).copy()
    
    if df_valid_dates.empty:
        st.warning("Nenhuma tarefa com datas válidas encontrada.")
        return

    df_gantt = df_valid_dates.groupby(['Project Name', 'Activity Name', 'Planned start', 'Planned finish']).agg({
        'Resource Name': lambda x: ', '.join(x.unique()),
        'Horas_Alocadas': 'sum'
    }).reset_index()

    col1, col2 = st.columns(2)
    with col1:
        recurso_busca = st.text_input("🔍 Filtrar por Recurso:", "", key="busca_gantt_geral").strip().lower()
    with col2:
        min_date = df_gantt['Planned start'].min()
        max_date = df_gantt['Planned finish'].max()
        datas_selecionadas = st.date_input("📅 Filtrar por Período:", value=(min_date, max_date), min_value=min_date, max_value=max_date, key="data_gantt_geral")

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
        df_filtrado, x_start="Visual_Start", x_end="Visual_Finish", y="Activity Name", color="Project Name", hover_name="Activity Name",
        hover_data={"Visual_Start": False, "Visual_Finish": False, "Planned start": True, "Planned finish": True, "Resource Name": True, "Horas_Alocadas": True, "Project Name": True, "Activity Name": False}
    )
    
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=max(400, len(df_filtrado) * 30), showlegend=True)
    st.plotly_chart(fig, use_container_width=True, key="gantt_chart_geral")

def render_heatmap_geral(df_master, df_capacidade):
    st.subheader("🔥 Heatmap de Capacidade vs. Demanda (Geral)")
    
    df_master_copy = df_master.copy()
    df_master_copy['Mes_Date'] = pd.to_datetime(df_master_copy['Mes'], format='%m/%Y')
    
    if 'RTC_ID' not in df_master_copy.columns:
        df_master_copy['RTC_ID'] = ""
        
    recursos_disponiveis = sorted(df_master_copy['Resource Name'].dropna().unique())
    min_date = df_master_copy['Mes_Date'].min().date()
    max_date = df_master_copy['Mes_Date'].max().date()
    
    with st.form(key='form_filtros_heatmap_geral'):
        col1, col2 = st.columns(2)
        with col1:
            recursos_selecionados = st.multiselect("👥 Selecione os Recursos:", options=recursos_disponiveis, default=[], key="heat_rec_filter_geral")
        with col2:
            periodo_selecionado = st.date_input("📅 Período (Mês):", value=(min_date, max_date), min_value=min_date, max_value=max_date, key="heat_date_filter_geral")
        submit_button = st.form_submit_button(label='🚀 Aplicar Filtros')
        
    df_filtrado = df_master_copy.copy()
    
    if recursos_selecionados: df_filtrado = df_filtrado[df_filtrado['Resource Name'].isin(recursos_selecionados)]
        
    if len(periodo_selecionado) == 2:
        data_inicio, data_fim = periodo_selecionado
        df_filtrado = df_filtrado[(df_filtrado['Mes_Date'].dt.date >= data_inicio) & (df_filtrado['Mes_Date'].dt.date <= data_fim)]
        
    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado.")
        return

    df_uso = df_filtrado.groupby(['Resource Name', 'ClassBR', 'Mes', 'Mes_Date'])['Horas_Alocadas'].sum().reset_index()
    df_heatmap = pd.merge(df_uso, df_capacidade, on=['ClassBR', 'Mes'], how='left')
    df_heatmap['Horas_Uteis'] = pd.to_numeric(df_heatmap['Horas_Uteis'], errors='coerce').fillna(180)
    
    df_heatmap_agg = df_heatmap.groupby(['Resource Name', 'Mes', 'Mes_Date']).agg({
        'Horas_Alocadas': 'sum',
        'Horas_Uteis': 'max' 
    }).reset_index()
    
    df_heatmap_agg['Taxa_Ocupacao'] = (df_heatmap_agg['Horas_Alocadas'] / df_heatmap_agg['Horas_Uteis']) * 100
    df_heatmap_agg['Saldo_Horas'] = df_heatmap_agg['Horas_Uteis'] - df_heatmap_agg['Horas_Alocadas']
    df_heatmap_agg = df_heatmap_agg.sort_values('Mes_Date')
    
    matriz_uso = df_heatmap_agg.pivot(index='Resource Name', columns='Mes', values='Taxa_Ocupacao').fillna(0)
    matriz_alocadas = df_heatmap_agg.pivot(index='Resource Name', columns='Mes', values='Horas_Alocadas').fillna(0)
    matriz_uteis = df_heatmap_agg.pivot(index='Resource Name', columns='Mes', values='Horas_Uteis').fillna(180)
    matriz_saldo = df_heatmap_agg.pivot(index='Resource Name', columns='Mes', values='Saldo_Horas').fillna(180)
    
    meses_ordenados = df_heatmap_agg['Mes'].unique()
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
    st.plotly_chart(fig, use_container_width=True, key="heatmap_chart_geral")
    
    st.write("---")
    st.write("### 🔍 Detalhamento do Mês e Inserção de RTC")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        recursos_drill = sorted(df_filtrado['Resource Name'].unique())
        rec_selecionado = st.selectbox("👤 Recurso:", [""] + recursos_drill, key="drill_rec_geral")
    with col_d2:
        meses_drill = sorted(df_filtrado['Mes'].unique(), key=lambda x: pd.to_datetime(x, format='%m/%Y'))
        mes_selecionado = st.selectbox("📅 Mês:", [""] + meses_drill, key="drill_mes_geral")
        
    if rec_selecionado and mes_selecionado:
        df_drill = df_filtrado[(df_filtrado['Resource Name'] == rec_selecionado) & (df_filtrado['Mes'] == mes_selecionado)]
        if not df_drill.empty:
            df_drill_show = df_drill[['Project Name', 'Activity Name', 'Horas_Alocadas', 'RTC_ID']].copy()
            df_drill_show = df_drill_show[df_drill_show['Horas_Alocadas'] > 0].sort_values('Horas_Alocadas', ascending=False)
            total_mes = df_drill_show['Horas_Alocadas'].sum()
            st.success(f"**Total alocado para {rec_selecionado} em {mes_selecionado}:** {total_mes:.1f}h")
            
            with st.form(key="form_rtc_geral"):
                config_colunas = {
                    "Project Name": st.column_config.TextColumn(disabled=True),
                    "Activity Name": st.column_config.TextColumn(disabled=True),
                    "Horas_Alocadas": st.column_config.NumberColumn(disabled=True, format="%.1f"),
                    "RTC_ID": st.column_config.TextColumn("ID do RTC (Editável)")
                }
                
                df_editado_rtc = st.data_editor(
                    df_drill_show, 
                    column_config=config_colunas, 
                    use_container_width=True, 
                    hide_index=True,
                    key="editor_rtc_geral"
                )
                
                if st.form_submit_button("💾 Salvar IDs do RTC"):
                    df_novo = st.session_state['df_geral'].copy()
                    
                    for _, row in df_editado_rtc.iterrows():
                        p_name = row['Project Name']
                        a_name = row['Activity Name']
                        novo_rtc = row['RTC_ID']
                        
                        mask = (df_novo['Project Name'] == p_name) & (df_novo['Activity Name'] == a_name)
                        df_novo.loc[mask, 'RTC_ID'] = novo_rtc
                        
                    st.session_state['df_geral'] = df_novo
                    st.success("✅ IDs do RTC atualizados com sucesso!")
                    st.rerun()
        else:
            st.info("Nenhuma hora alocada para este recurso neste mês.")

def render_changelog_geral(df_original, df_simulado):
    st.subheader("🕵️‍♂️ Histórico de Auditoria (Logs - Geral)")
    st.write("Acompanhe todas as alterações feitas no sistema, quem fez e quando.")
    
    # --- NOVIDADE: BUSCA DIRETO DO BANCO DE DADOS ---
    db = SessionLocal()
    try:
        # Busca os logs da tabela Geral, ordenados do mais recente para o mais antigo
        logs = db.query(AuditLog).filter(AuditLog.table_affected == "tasks_geral").order_by(AuditLog.timestamp.desc()).all()
        
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
                    "Projeto | Atividade": log.record_id,
                    "Campo Alterado": log.field_changed,
                    "Valor Antigo": log.old_value,
                    "Novo Valor": log.new_value
                })
            
            df_logs = pd.DataFrame(dados_log)
            
            # Filtros rápidos para a tabela de logs
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                busca_user = st.selectbox("Filtrar por Usuário:", ["Todos"] + sorted(df_logs['Usuário'].unique().tolist()), key="log_user_geral")
            with col_f2:
                busca_acao = st.selectbox("Filtrar por Ação:", ["Todas", "➕ Criação", "✏️ Edição", "❌ Exclusão"], key="log_acao_geral")
                
            if busca_user != "Todos":
                df_logs = df_logs[df_logs['Usuário'] == busca_user]
            if busca_acao != "Todas":
                df_logs = df_logs[df_logs['Ação'] == busca_acao]
            
            st.dataframe(df_logs, use_container_width=True, hide_index=True)
            
            # Botão de exportação
            csv = df_logs.to_csv(index=False, sep=';', encoding='utf-8-sig')
            st.download_button(label="📥 Exportar Histórico Completo (CSV)", data=csv, file_name="historico_auditoria_geral.csv", mime="text/csv", key="export_log_geral")
            
    except Exception as e:
        st.error(f"Erro ao carregar logs: {e}")
    finally:
        db.close()