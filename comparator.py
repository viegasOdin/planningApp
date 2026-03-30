import streamlit as st
import pandas as pd
from database import SessionLocal, Scenario, TaskOdyc, TaskGeral

def get_scenarios(modo):
    """Busca todos os cenários salvos no banco de dados para o modo atual."""
    db = SessionLocal()
    try:
        scenarios = db.query(Scenario).filter(Scenario.mode == modo).order_by(Scenario.created_at.desc()).all()
        # Cria um dicionário amigável para o Selectbox: "ID | Nome (Data) - por Autor" -> ID
        return {f"ID {s.id} | {s.name} ({s.created_at.strftime('%d/%m/%Y %H:%M')}) - por {s.author}": s.id for s in scenarios}
    finally:
        db.close()

def get_tasks_df(scenario_id, modo):
    """Busca as tarefas de um cenário específico e transforma em DataFrame."""
    db = SessionLocal()
    try:
        if modo == "OdyC":
            tasks = db.query(TaskOdyc).filter(TaskOdyc.scenario_id == scenario_id).all()
            data = [{
                'Line identifier': t.line_identifier,
                'Task Code': t.task_code,
                'Resource Name': t.resource_name,
                'Planned start': t.planned_start,
                'Planned finish': t.planned_finish,
                'Horas_Alocadas': t.workload_hours
            } for t in tasks]
        else:
            tasks = db.query(TaskGeral).filter(TaskGeral.scenario_id == scenario_id).all()
            data = [{
                'Project Name': t.project_name,
                'Activity Name': t.activity_name,
                'Resource Name': t.resource_name,
                'Planned start': t.planned_start,
                'Planned finish': t.planned_finish,
                'Horas_Alocadas': t.workload_hours
            } for t in tasks]
        return pd.DataFrame(data)
    finally:
        db.close()

def render_comparator(modo):
    st.subheader(f"⚖️ Comparador de Versões ({modo})")
    st.write("Selecione duas versões salvas no banco de dados para comparar as diferenças de alocação e prazos.")
    
    scenarios_dict = get_scenarios(modo)
    
    if len(scenarios_dict) < 2:
        st.warning("⚠️ Você precisa ter pelo menos **2 versões salvas** no banco de dados para usar o comparador.")
        st.info("💡 **Dica:** Vá no menu lateral esquerdo e clique em '💾 Salvar Nova Versão no Banco' para criar um ponto de comparação.")
        return
        
    col1, col2 = st.columns(2)
    with col1:
        # Pega o mais antigo como base por padrão (último da lista)
        cenario_a_nome = st.selectbox("📌 Versão Base (Antiga):", list(scenarios_dict.keys()), index=len(scenarios_dict)-1)
    with col2:
        # Pega o mais novo como comparado por padrão (primeiro da lista)
        cenario_b_nome = st.selectbox("🎯 Versão Comparada (Nova):", list(scenarios_dict.keys()), index=0)
        
    if st.button("🚀 Comparar Versões", use_container_width=True):
        id_a = scenarios_dict[cenario_a_nome]
        id_b = scenarios_dict[cenario_b_nome]
        
        if id_a == id_b:
            st.warning("Você selecionou a mesma versão nas duas caixas. Selecione versões diferentes para comparar.")
            return
            
        with st.spinner("Buscando dados no banco e calculando diferenças..."):
            df_a = get_tasks_df(id_a, modo)
            df_b = get_tasks_df(id_b, modo)
            
            if df_a.empty or df_b.empty:
                st.error("Uma das versões não possui dados válidos para comparação.")
                return
                
            # Agrupa os dados dependendo do modo
            if modo == "OdyC":
                df_a_grp = df_a.groupby(['Line identifier', 'Task Code']).agg({
                    'Planned start': 'min', 'Planned finish': 'max', 'Horas_Alocadas': 'sum',
                    'Resource Name': lambda x: ', '.join(sorted(set(x.dropna().astype(str))))
                }).reset_index()
                
                df_b_grp = df_b.groupby(['Line identifier', 'Task Code']).agg({
                    'Planned start': 'min', 'Planned finish': 'max', 'Horas_Alocadas': 'sum',
                    'Resource Name': lambda x: ', '.join(sorted(set(x.dropna().astype(str))))
                }).reset_index()
                merge_cols = ['Line identifier', 'Task Code']
            else:
                df_a_grp = df_a.groupby(['Project Name', 'Activity Name']).agg({
                    'Planned start': 'min', 'Planned finish': 'max', 'Horas_Alocadas': 'sum',
                    'Resource Name': lambda x: ', '.join(sorted(set(x.dropna().astype(str))))
                }).reset_index()
                
                df_b_grp = df_b.groupby(['Project Name', 'Activity Name']).agg({
                    'Planned start': 'min', 'Planned finish': 'max', 'Horas_Alocadas': 'sum',
                    'Resource Name': lambda x: ', '.join(sorted(set(x.dropna().astype(str))))
                }).reset_index()
                merge_cols = ['Project Name', 'Activity Name']
                
            # Cruza as duas versões
            df_compare = pd.merge(df_a_grp, df_b_grp, on=merge_cols, how='outer', suffixes=('_Base', '_Nova'))
            
            # Formata as datas e preenche vazios
            df_compare['Planned start_Base_str'] = pd.to_datetime(df_compare['Planned start_Base']).dt.date.fillna('N/A').astype(str)
            df_compare['Planned finish_Base_str'] = pd.to_datetime(df_compare['Planned finish_Base']).dt.date.fillna('N/A').astype(str)
            df_compare['Planned start_Nova_str'] = pd.to_datetime(df_compare['Planned start_Nova']).dt.date.fillna('N/A').astype(str)
            df_compare['Planned finish_Nova_str'] = pd.to_datetime(df_compare['Planned finish_Nova']).dt.date.fillna('N/A').astype(str)
            
            df_compare['Resource Name_Base'] = df_compare['Resource Name_Base'].fillna('N/A')
            df_compare['Resource Name_Nova'] = df_compare['Resource Name_Nova'].fillna('N/A')
            df_compare['Horas_Alocadas_Base'] = df_compare['Horas_Alocadas_Base'].fillna(0)
            df_compare['Horas_Alocadas_Nova'] = df_compare['Horas_Alocadas_Nova'].fillna(0)
            
            # Filtra apenas o que mudou
            mudancas = df_compare[
                (df_compare['Planned start_Base_str'] != df_compare['Planned start_Nova_str']) |
                (df_compare['Planned finish_Base_str'] != df_compare['Planned finish_Nova_str']) |
                (round(df_compare['Horas_Alocadas_Base'], 1) != round(df_compare['Horas_Alocadas_Nova'], 1)) |
                (df_compare['Resource Name_Base'] != df_compare['Resource Name_Nova'])
            ].copy()
            
            # Cards de Resumo no topo
            st.write("---")
            col_r1, col_r2, col_r3 = st.columns(3)
            col_r1.metric("Total Horas (Versão Base)", f"{df_a['Horas_Alocadas'].sum():.1f}h")
            col_r2.metric("Total Horas (Versão Nova)", f"{df_b['Horas_Alocadas'].sum():.1f}h")
            variacao_total = df_b['Horas_Alocadas'].sum() - df_a['Horas_Alocadas'].sum()
            col_r3.metric("Variação Total de Horas", f"{variacao_total:+.1f}h", delta=float(variacao_total), delta_color="inverse")
            st.write("---")
            
            if mudancas.empty:
                st.success("✅ As duas versões são exatamente iguais! Nenhuma alteração de data, recurso ou horas foi encontrada.")
            else:
                st.warning(f"⚠️ Encontramos diferenças em **{len(mudancas)}** tarefas/atividades.")
                
                mudancas['Início (Base -> Nova)'] = mudancas['Planned start_Base_str'] + " ➡️ " + mudancas['Planned start_Nova_str']
                mudancas['Fim (Base -> Nova)'] = mudancas['Planned finish_Base_str'] + " ➡️ " + mudancas['Planned finish_Nova_str']
                mudancas['Horas (Base -> Nova)'] = mudancas['Horas_Alocadas_Base'].round(1).astype(str) + "h ➡️ " + mudancas['Horas_Alocadas_Nova'].round(1).astype(str) + "h"
                mudancas['Recursos (Base -> Nova)'] = mudancas['Resource Name_Base'].astype(str) + " ➡️ " + mudancas['Resource Name_Nova'].astype(str)
                
                mudancas['Variação (Horas)'] = mudancas['Horas_Alocadas_Nova'] - mudancas['Horas_Alocadas_Base']
                
                cols_display = merge_cols + ['Recursos (Base -> Nova)', 'Início (Base -> Nova)', 'Fim (Base -> Nova)', 'Horas (Base -> Nova)', 'Variação (Horas)']
                df_display = mudancas[cols_display].copy()
                
                # Função para colorir a coluna de variação (Vermelho se aumentou, Verde se diminuiu)
                def color_variation(val):
                    if val > 0: return 'color: #e74c3c; font-weight: bold'
                    elif val < 0: return 'color: #2ecc71; font-weight: bold'
                    return ''
                
                st.dataframe(
                    df_display.style.map(color_variation, subset=['Variação (Horas)']).format({'Variação (Horas)': '{:+.1f}h'}), 
                    use_container_width=True, 
                    hide_index=True
                )
                
                csv = df_display.to_csv(index=False, sep=';', encoding='utf-8-sig')
                st.download_button(label="📥 Exportar Comparativo (CSV)", data=csv, file_name=f"comparativo_versoes_{modo}.csv", mime="text/csv")