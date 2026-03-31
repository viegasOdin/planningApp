import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
from database import SessionLocal, AuditLog, ResourceAbsence
from datetime import datetime

def get_absences_df():
    """Busca as ausências no banco de dados e converte para DataFrame."""
    db = SessionLocal()
    try:
        absences = db.query(ResourceAbsence).all()
        if not absences:
            return pd.DataFrame()
        data = [{
            'Resource Name': a.resource_name,
            'Start': pd.to_datetime(a.start_date),
            'End': pd.to_datetime(a.end_date)
        } for a in absences]
        return pd.DataFrame(data)
    finally:
        db.close()

def calcular_dias_uteis_ferias(mes_str, start_date, end_date):
    """Calcula quantos dias úteis de férias caem dentro de um mês específico."""
    inicio_mes = pd.to_datetime(mes_str, format='%m/%Y')
    fim_mes = inicio_mes + pd.offsets.MonthEnd(0)
    
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    start_calc = max(inicio_mes, start_dt)
    end_calc = min(fim_mes, end_dt)
    
    if start_calc <= end_calc:
        return len(pd.bdate_range(start_calc, end_calc))
    return 0

def render_dashboard_geral(df_geral):
    st.subheader("📈 Visão Geral de Horas (Workload Geral)")
    df_valid = df_geral.copy()
    if df_valid.empty:
        st.warning("Sem dados para exibir.")
        return
        
    df_valid['Mes_Date'] = pd.to_datetime(df_valid['Mes'], format='%m/%Y')
    min_date = df_valid['Mes_Date'].min().date()
    max_date = df_valid['Mes_Date'].max().date()
    
    col_filt1, col_filt2 = st.columns([1, 2])
    with col_filt1:
        datas_selecionadas = st.date_input("📅 Filtrar por Período:", value=(min_date, max_date), min_value=min_date, max_value=max_date, key="dash_date_geral")
        
    if len(datas_selecionadas) == 2:
        data_inicio, data_fim = datas_selecionadas
        df_valid = df_valid[(df_valid['Mes_Date'].dt.date >= data_inicio.replace(day=1)) & (df_valid['Mes_Date'].dt.date <= data_fim)]
        
    total_horas = df_valid['Horas_Alocadas'].sum()
    total_projetos = df_valid['Project Name'].nunique()
    total_recursos = df_valid['Resource Name'].nunique()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Horas Alocadas", f"{total_horas:,.1f}h")
    col2.metric("Projetos Ativos", total_projetos)
    col3.metric("Recursos Envolvidos", total_recursos)
    
    st.write("---")
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        st.write("**Horas por Mês**")
        df_mes = df_valid.groupby('Mes')['Horas_Alocadas'].sum().reset_index()
        df_mes['Mes_Date'] = pd.to_datetime(df_mes['Mes'], format='%m/%Y')
        df_mes = df_mes.sort_values('Mes_Date')
        fig_mes = px.bar(df_mes, x='Mes', y='Horas_Alocadas', text_auto='.1f', color_discrete_sequence=['#2ecc71'])
        st.plotly_chart(fig_mes, use_container_width=True)
        
    with col_graf2:
        st.write("**Horas por Recurso (Top 10)**")
        df_rec = df_valid.groupby('Resource Name')['Horas_Alocadas'].sum().reset_index().sort_values('Horas_Alocadas', ascending=True).tail(10)
        fig_rec = px.bar(df_rec, y='Resource Name', x='Horas_Alocadas', orientation='h', text_auto='.1f', color_discrete_sequence=['#e67e22'])
        st.plotly_chart(fig_rec, use_container_width=True)

def render_gantt_geral(df_geral):
    st.subheader("📊 Gráfico de Gantt (Workload Geral)")
    df_valid_dates = df_geral.dropna(subset=['Planned start', 'Planned finish']).copy()
    
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
        data_inicio_ts = pd.to_datetime(data_inicio)
        data_fim_ts = pd.to_datetime(data_fim)
        
        df_filtrado = df_filtrado[(pd.to_datetime(df_filtrado['Planned start']) <= data_fim_ts) & (pd.to_datetime(df_filtrado['Planned finish']) >= data_inicio_ts)].copy()
        df_filtrado['Visual_Start'] = pd.to_datetime(df_filtrado['Planned start']).apply(lambda x: max(x, data_inicio_ts))
        df_filtrado['Visual_Finish'] = pd.to_datetime(df_filtrado['Planned finish']).apply(lambda x: min(x, data_fim_ts))
    else:
        df_filtrado['Visual_Start'] = pd.to_datetime(df_filtrado['Planned start'])
        df_filtrado['Visual_Finish'] = pd.to_datetime(df_filtrado['Planned finish'])

    if df_filtrado.empty:
        st.warning("Nenhuma tarefa encontrada com os filtros atuais.")
        return

    df_filtrado['Task_Label'] = df_filtrado['Project Name'] + " - " + df_filtrado['Activity Name']

    fig = px.timeline(
        df_filtrado, x_start="Visual_Start", x_end="Visual_Finish", y="Task_Label", color="Resource Name", hover_name="Task_Label",
        hover_data={"Visual_Start": False, "Visual_Finish": False, "Planned start": True, "Planned finish": True, "Resource Name": True, "Horas_Alocadas": True}
    )
    
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=max(400, len(df_filtrado) * 30), showlegend=True)
    st.plotly_chart(fig, use_container_width=True, key="chart_gantt_geral")

def render_heatmap_geral(df_geral, df_cap_geral):
    st.subheader("🔥 Heatmap de Capacidade vs. Demanda (Workload Geral)")
    
    df_simulado_copy = df_geral.copy()
    df_simulado_copy['Mes_Date'] = pd.to_datetime(df_simulado_copy['Mes'], format='%m/%Y')
        
    recursos_disponiveis = sorted(df_simulado_copy['Resource Name'].dropna().unique())
    min_date = df_simulado_copy['Mes_Date'].min().date()
    max_date = df_simulado_copy['Mes_Date'].max().date()
    
    with st.form(key='form_filtros_heatmap_geral'):
        col1, col2 = st.columns(2)
        with col1:
            recursos_selecionados = st.multiselect("👥 Selecione os Recursos:", options=recursos_disponiveis, default=[], key="heat_rec_filter_geral")
        with col2:
            periodo_selecionado = st.date_input("📅 Período (Mês):", value=(min_date, max_date), min_value=min_date, max_value=max_date, key="heat_date_filter_geral")
        submit_button = st.form_submit_button(label='🚀 Aplicar Filtros')
        
    df_filtrado = df_simulado_copy.copy()
    
    if recursos_selecionados:
        df_filtrado = df_filtrado[df_filtrado['Resource Name'].isin(recursos_selecionados)]
        
    if len(periodo_selecionado) == 2:
        data_inicio, data_fim = periodo_selecionado
        df_filtrado = df_filtrado[(df_filtrado['Mes_Date'].dt.date >= data_inicio) & (df_filtrado['Mes_Date'].dt.date <= data_fim)]
        
    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado com os filtros atuais.")
        return

    df_uso = df_filtrado.groupby(['Resource Name', 'Mes', 'Mes_Date'])['Horas_Alocadas'].sum().reset_index()
    
    # --- CORREÇÃO: BLINDAGEM DO MERGE DE CAPACIDADE ---
    # Verifica se as colunas existem antes de tentar o merge
    if not df_cap_geral.empty and 'Resource Name' in df_cap_geral.columns and 'Horas_Uteis' in df_cap_geral.columns:
        df_uso = pd.merge(df_uso, df_cap_geral[['Resource Name', 'Horas_Uteis']], on='Resource Name', how='left')
        df_uso['Horas_Uteis'] = df_uso['Horas_Uteis'].fillna(180.0)
    else:
        df_uso['Horas_Uteis'] = 180.0
    
    # --- LÓGICA DE DESCONTO DE FÉRIAS NO GERAL ---
    df_absences = get_absences_df()
    
    if not df_absences.empty:
        for idx, row in df_uso.iterrows():
            rec = row['Resource Name']
            mes = row['Mes']
            
            ferias_rec = df_absences[df_absences['Resource Name'] == rec]
            dias_desconto = 0
            
            for _, f_row in ferias_rec.iterrows():
                dias_desconto += calcular_dias_uteis_ferias(mes, f_row['Start'], f_row['End'])
            
            if dias_desconto > 0:
                horas_desconto = dias_desconto * 9.18
                nova_capacidade = max(0, row['Horas_Uteis'] - horas_desconto)
                df_uso.at[idx, 'Horas_Uteis'] = nova_capacidade
    
    df_heatmap_agg = df_uso.copy()
    
    df_heatmap_agg['Taxa_Ocupacao'] = np.where(
        df_heatmap_agg['Horas_Uteis'] > 0,
        (df_heatmap_agg['Horas_Alocadas'] / df_heatmap_agg['Horas_Uteis']) * 100,
        np.where(df_heatmap_agg['Horas_Alocadas'] > 0, 999, 0)
    )
    
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

def render_changelog_geral(df_original, df_simulado):
    st.subheader("🕵️‍♂️ Histórico de Auditoria (Logs - Geral)")
    st.write("Acompanhe todas as alterações feitas no sistema, quem fez e quando.")
    
    db = SessionLocal()
    try:
        logs = db.query(AuditLog).filter(AuditLog.table_affected == "tasks_geral").order_by(AuditLog.timestamp.desc()).all()
        
        if not logs:
            st.info("Nenhuma alteração registrada no banco de dados ainda.")
        else:
            dados_log = []
            for log in logs:
                dados_log.append({
                    "Data/Hora": log.timestamp.strftime("%d/%m/%Y %H:%M:%S"),
                    "Usuário": log.user_id.title(),
                    "Ação": "➕ Criação" if log.action == "CREATE" else "✏️ Edição" if log.action == "UPDATE" else "❌ Exclusão",
                    "Registro (ID/Task)": log.record_id,
                    "Campo Alterado": log.field_changed,
                    "Valor Antigo": log.old_value,
                    "Novo Valor": log.new_value
                })
            
            df_logs = pd.DataFrame(dados_log)
            
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
            
            csv = df_logs.to_csv(index=False, sep=';', encoding='utf-8-sig')
            st.download_button(label="📥 Exportar Histórico Completo (CSV)", data=csv, file_name="historico_auditoria_geral.csv", mime="text/csv")
            
    except Exception as e:
        st.error(f"Erro ao carregar logs: {e}")
    finally:
        db.close()