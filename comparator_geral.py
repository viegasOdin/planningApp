import streamlit as st
import pandas as pd
import plotly.express as px

def render_comparator_geral(df_base, df_atual):
    st.subheader("⚖️ Comparativo: Baseline vs. Simulação Atual")
    st.caption("Analise a evolução do Workload em relação ao baseline. Valores positivos indicam aumento de horas, negativos indicam redução.")

    # 1. KPIs Principais
    total_base = df_base['Horas_Alocadas'].sum()
    total_atual = df_atual['Horas_Alocadas'].sum()
    delta_total = total_atual - total_base

    col1, col2, col3 = st.columns(3)
    col1.metric("Horas — Baseline", f"{total_base:,.1f}h")
    col2.metric("Horas — Simulação Atual", f"{total_atual:,.1f}h")
    col3.metric("Variação Global", f"{delta_total:+,.1f}h", delta=round(delta_total, 1), delta_color="inverse")

    st.divider()

    # 2. Agrupamentos para Gráficos (Variação)
    # Variação por Recurso
    base_rec = df_base.groupby('Resource Name')['Horas_Alocadas'].sum().reset_index().rename(columns={'Horas_Alocadas': 'Horas_Base'})
    atual_rec = df_atual.groupby('Resource Name')['Horas_Alocadas'].sum().reset_index().rename(columns={'Horas_Alocadas': 'Horas_Atual'})
    df_comp_rec = pd.merge(base_rec, atual_rec, on='Resource Name', how='outer').fillna(0)
    df_comp_rec['Delta'] = df_comp_rec['Horas_Atual'] - df_comp_rec['Horas_Base']
    df_comp_rec = df_comp_rec[df_comp_rec['Delta'] != 0].sort_values('Delta', ascending=True)

    # Variação por Projeto
    base_proj = df_base.groupby('Project Name')['Horas_Alocadas'].sum().reset_index().rename(columns={'Horas_Alocadas': 'Horas_Base'})
    atual_proj = df_atual.groupby('Project Name')['Horas_Alocadas'].sum().reset_index().rename(columns={'Horas_Alocadas': 'Horas_Atual'})
    df_comp_proj = pd.merge(base_proj, atual_proj, on='Project Name', how='outer').fillna(0)
    df_comp_proj['Delta'] = df_comp_proj['Horas_Atual'] - df_comp_proj['Horas_Base']
    df_comp_proj = df_comp_proj[df_comp_proj['Delta'] != 0].sort_values('Delta', ascending=True)

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.write("**Variação de Horas por Recurso**")
        if not df_comp_rec.empty:
            fig_rec = px.bar(
                df_comp_rec, y='Resource Name', x='Delta', orientation='h', text_auto='.1f', 
                color='Delta', color_continuous_scale=['#e74c3c', '#2ecc71'], color_continuous_midpoint=0
            )
            fig_rec.update_layout(coloraxis_showscale=False, height=max(300, len(df_comp_rec) * 30))
            st.plotly_chart(fig_rec, use_container_width=True, key="comp_rec")
        else:
            st.info("Nenhuma variação de horas por recurso.")

    with col_g2:
        st.write("**Variação de Horas por Projeto**")
        if not df_comp_proj.empty:
            fig_proj = px.bar(
                df_comp_proj, y='Project Name', x='Delta', orientation='h', text_auto='.1f', 
                color='Delta', color_continuous_scale=['#e74c3c', '#2ecc71'], color_continuous_midpoint=0
            )
            fig_proj.update_layout(coloraxis_showscale=False, height=max(300, len(df_comp_proj) * 30))
            st.plotly_chart(fig_proj, use_container_width=True, key="comp_proj")
        else:
            st.info("Nenhuma variação de horas por projeto.")

    st.divider()
    st.write("### 🔍 Entradas e Saídas de Alocações")

    # 3. Identificar tarefas Novas e Removidas
    base_tasks = df_base[['Project Name', 'Activity Name', 'Resource Name']].drop_duplicates()
    base_tasks['Status'] = 'Baseline'
    
    atual_tasks = df_atual[['Project Name', 'Activity Name', 'Resource Name']].drop_duplicates()
    atual_tasks['Status'] = 'Atual'

    df_tasks = pd.merge(base_tasks, atual_tasks, on=['Project Name', 'Activity Name', 'Resource Name'], how='outer', suffixes=('_base', '_atual'))
    
    novas = df_tasks[df_tasks['Status_base'].isna()][['Project Name', 'Activity Name', 'Resource Name']]
    removidas = df_tasks[df_tasks['Status_atual'].isna()][['Project Name', 'Activity Name', 'Resource Name']]

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.success(f"**➕ Novas Alocações ({len(novas)})**\n\nTarefas/Recursos que **não existiam** na Baseline e entraram neste mês.")
        if not novas.empty:
            st.dataframe(novas, use_container_width=True, hide_index=True)
        else:
            st.write("Nenhuma alocação nova.")
            
    with col_t2:
        st.error(f"**➖ Alocações Removidas ({len(removidas)})**\n\nTarefas/Recursos que estavam na Baseline e **sumiram** neste mês.")
        if not removidas.empty:
            st.dataframe(removidas, use_container_width=True, hide_index=True)
        else:
            st.write("Nenhuma alocação removida.")