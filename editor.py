import streamlit as st
import pandas as pd
import numpy as np
import math
from utils import registrar_log, extract_ids, aplicar_cascata

def clear_ui_state():
    prefixos = ['mat_', 'editor_', 'visao_', 'busca_', 'sel_', 'task_', 'proj_']
    for key in list(st.session_state.keys()):
        if any(key.startswith(p) for p in prefixos):
            del st.session_state[key]

def get_bdays_delta(date_old, date_new):
    """Calcula a diferença em dias úteis entre duas datas (positivo se atrasou, negativo se adiantou)"""
    d_old = pd.to_datetime(date_old)
    d_new = pd.to_datetime(date_new)
    if d_new >= d_old:
        return len(pd.bdate_range(d_old, d_new)) - 1
    else:
        return -(len(pd.bdate_range(d_new, d_old)) - 1)

def render_editor():
    st.subheader("✏️ Simulador de Cenários Avançado")
    
    if 'msg_cascata' in st.session_state:
        st.success(st.session_state['msg_cascata'])
        del st.session_state['msg_cascata']
        
    df_simulado = st.session_state['df_simulado']
    usuario = st.session_state.get("usuario_logado", "Desconhecido") 
    
    if 'Line identifier' not in df_simulado.columns:
        st.error("⚠️ A coluna 'Line identifier' não foi encontrada. Recarregue os dados originais.")
        return

    todos_recursos = sorted(df_simulado['Resource Name'].dropna().unique())
    
    tab_editar, tab_nova, tab_visao, tab_dividir = st.tabs(["📝 Editar Existente", "➕ Criar Nova Tarefa", "📅 Visão por Recurso/Mês", "✂️ Dividir Horas por Mês"])
    
    with tab_nova:
        st.write("Adicione uma nova atividade vinculada a um recurso e pacote existente.")
        with st.form("form_nova_tarefa"):
            col_n1, col_n2 = st.columns(2)
            novo_rec = col_n1.selectbox("1️⃣ Recurso:", todos_recursos)
            
            task_codes_recurso = df_simulado[df_simulado['Resource Name'] == novo_rec]['Task Code'].dropna().unique()
            if len(task_codes_recurso) == 0:
                task_codes_recurso = df_simulado['Task Code'].dropna().unique()
                
            novo_task_code = col_n2.selectbox("2️⃣ Task Code (Pacote):", sorted(task_codes_recurso))
            novo_activity = st.text_input("3️⃣ Nome da Atividade:", "Nova Atividade")
            
            col_n4, col_n5 = st.columns(2)
            nova_data_ini = col_n4.date_input("Data Início:")
            novas_horas = col_n5.number_input("Total de Horas:", min_value=1.0, value=40.0)
            
            st.write("---")
            tipo_fim = st.radio("Definição da Data Fim:", ["Automático (9,18h/dia útil)", "Data Fixa Manual"])
            nova_data_fim = None
            
            if tipo_fim == "Data Fixa Manual":
                nova_data_fim = st.date_input("Data Fim:")
            else:
                dias_necessarios = math.ceil(novas_horas / 9.18)
                nova_data_fim_calc = pd.to_datetime(nova_data_ini) + pd.offsets.BDay(max(1, dias_necessarios) - 1)
                st.info(f"💡 Data Fim Calculada: **{nova_data_fim_calc.strftime('%d/%m/%Y')}** ({max(1, dias_necessarios)} dias úteis)")
                nova_data_fim = nova_data_fim_calc.date()
            
            novo_rtc = st.text_input("🔗 ID da Tarefa no RTC (Opcional):", "")
            
            if st.form_submit_button("Criar Tarefa"):
                dias_uteis = pd.date_range(start=nova_data_ini, end=nova_data_fim, freq='B')
                if len(dias_uteis) == 0: dias_uteis = [pd.to_datetime(nova_data_ini)]
                horas_por_dia = novas_horas / len(dias_uteis)
                
                df_dias = pd.DataFrame({'Data': dias_uteis})
                df_dias['Mes'] = df_dias['Data'].dt.strftime('%m/%Y')
                df_dias['Horas'] = horas_por_dia
                df_meses = df_dias.groupby('Mes')['Horas'].sum().reset_index()
                
                novas_linhas = []
                novo_id_linha = f"NEW-{np.random.randint(1000,9999)}"
                
                for _, row_mes in df_meses.iterrows():
                    novas_linhas.append({
                        'Line identifier': novo_id_linha,
                        'Task Code': novo_task_code,
                        'Activity Name': novo_activity,
                        'Resource Name': novo_rec,
                        'Planned start': nova_data_ini,
                        'Planned finish': nova_data_fim,
                        'Horas_Alocadas': row_mes['Horas'],
                        'Mes': row_mes['Mes'],
                        'Predecessor': '', 'Successor': '',
                        'RTC_ID': novo_rtc
                    })
                    
                st.session_state['df_simulado'] = pd.concat([df_simulado, pd.DataFrame(novas_linhas)], ignore_index=True)
                registrar_log(usuario, "CREATE", "tasks_odyc", novo_id_linha, "Nova Tarefa", "", f"{novas_horas}h para {novo_rec}")
                st.success("Tarefa criada com sucesso! O aplicativo será recarregado...")
                clear_ui_state()
                st.rerun()

    with tab_editar:
        st.info("💡 **Dica para Dividir Tarefas:** Para alocar mais de um recurso na mesma tarefa, basta adicionar uma nova linha na tabela abaixo, escolher o novo recurso e definir as horas dele!")
        col_busca1, col_busca2, col_busca3 = st.columns(3)
        with col_busca1: busca_nome = st.text_input("🔍 Buscar por Nome da Tarefa:", "")
        with col_busca2: busca_id = st.text_input("🔍 Buscar por Line ID:", "")
        with col_busca3:
            task_codes_list = [""] + sorted(df_simulado['Task Code'].dropna().unique().tolist())
            busca_task = st.selectbox("📁 Filtrar por Task Code:", task_codes_list)
            
        df_tarefas = df_simulado.dropna(subset=['Planned start', 'Planned finish']).copy()
        
        if df_tarefas.empty:
            st.warning("Não há tarefas com datas válidas para editar.")
            return
            
        df_agrupado = df_tarefas.groupby(['Task Code', 'Activity Name']).agg({
            'Line identifier': 'first', 'Planned start': 'first', 'Planned finish': 'first', 'Predecessor': 'first', 'Successor': 'first'
        }).reset_index()
        df_agrupado['Display'] = df_agrupado['Task Code'] + " | " + df_agrupado['Activity Name']
        
        if busca_nome: df_agrupado = df_agrupado[df_agrupado['Display'].str.contains(busca_nome, case=False, na=False)]
        if busca_id: df_agrupado = df_agrupado[df_agrupado['Line identifier'].astype(str).str.contains(busca_id, case=False, na=False)]
        if busca_task: df_agrupado = df_agrupado[df_agrupado['Task Code'] == busca_task]
            
        if df_agrupado.empty:
            st.info("Nenhuma tarefa encontrada com esses filtros combinados.")
            return
            
        tarefa_selecionada = st.selectbox("1️⃣ Selecione a Tarefa Principal:", [""] + df_agrupado['Display'].tolist())
        
        if tarefa_selecionada:
            linha_atual = df_agrupado[df_agrupado['Display'] == tarefa_selecionada].iloc[0]
            current_id = str(linha_atual['Line identifier'])
            task_code = linha_atual['Task Code']
            activity_name = linha_atual['Activity Name']
            
            pred_ids = extract_ids(linha_atual['Predecessor'])
            succ_ids = extract_ids(linha_atual['Successor'])
            todos_ids_contexto = [id for id in [current_id] + pred_ids + succ_ids if id != 'N/A' and id != 'nan']
            
            st.write("---")
            st.write(f"### 🔗 Contexto Direto da Tarefa")
            
            df_contexto_full = df_tarefas[
                (df_tarefas['Line identifier'].astype(str).isin(todos_ids_contexto)) |
                ((df_tarefas['Task Code'] == task_code) & (df_tarefas['Activity Name'] == activity_name))
            ]
            
            df_contexto = df_contexto_full.groupby(
                ['Line identifier', 'Task Code', 'Activity Name', 'Planned start', 'Planned finish', 'Predecessor', 'Successor']
            ).size().reset_index().drop(columns=[0])
            
            def tipo_relacao(row):
                row_id = str(row['Line identifier'])
                if row['Task Code'] == task_code and row['Activity Name'] == activity_name: return "🎯 Principal"
                elif row_id in pred_ids: return "⬅️ Antecessora"
                elif row_id in succ_ids: return "➡️ Sucessora"
                return "Outro"
                
            df_contexto['Relação'] = df_contexto.apply(tipo_relacao, axis=1)
            df_contexto['Início'] = pd.to_datetime(df_contexto['Planned start']).dt.strftime('%d/%m/%Y')
            df_contexto['Fim'] = pd.to_datetime(df_contexto['Planned finish']).dt.strftime('%d/%m/%Y')
            
            cols_ordem = ['Relação', 'Line identifier', 'Task Code', 'Activity Name', 'Início', 'Fim', 'Predecessor', 'Successor']
            df_contexto_exibicao = df_contexto[cols_ordem].sort_values('Início')
            
            def highlight_current(row):
                if row['Task Code'] == task_code and row['Activity Name'] == activity_name:
                    return ['background-color: rgba(46, 204, 113, 0.3)'] * len(row)
                return [''] * len(row)
                
            st.dataframe(df_contexto_exibicao.style.apply(highlight_current, axis=1), use_container_width=True, hide_index=True)
            
            st.write("---")
            st.write("### 👥 Edição de Recursos (Cálculo Automático)")
            
            opcoes_edicao = df_contexto['Task Code'] + " | " + df_contexto['Activity Name']
            idx_principal = next((i for i, val in enumerate(opcoes_edicao) if val == tarefa_selecionada), 0)
                    
            tarefa_para_editar = st.selectbox("2️⃣ Qual destas atividades do contexto você deseja editar?", opcoes_edicao.tolist(), index=idx_principal)
            
            if tarefa_para_editar:
                edit_task_code, edit_activity_name = tarefa_para_editar.split(" | ")
                
                df_alocacoes = df_simulado[(df_simulado['Task Code'] == edit_task_code) & (df_simulado['Activity Name'] == edit_activity_name)]
                edit_line_id = str(df_alocacoes['Line identifier'].iloc[0])
                
                df_edit = df_alocacoes.groupby('Resource Name').agg({
                    'Planned start': 'first', 'Planned finish': 'first', 'Horas_Alocadas': 'sum'
                }).reset_index()
                
                with st.form("form_edicao_multipla"):
                    st.write("💡 **Dica de UX:** Se você alterar a **Data Início**, a Data Fim será recalculada automaticamente para manter as mesmas horas!")
                    empurrar_sucessoras = st.checkbox("🔗 Empurrar tarefas sucessoras automaticamente (respeitando FS, SS, FF)", value=True)
                    st.write("---")
                    
                    config_colunas = {
                        "Resource Name": st.column_config.SelectboxColumn("Recurso", options=todos_recursos, required=True),
                        "Planned start": st.column_config.DateColumn("Data Início", required=True),
                        "Planned finish": st.column_config.DateColumn("Data Fim (Opcional)"),
                        "Horas_Alocadas": st.column_config.NumberColumn("Total de Horas", min_value=0.0, required=True, format="%.1f")
                    }
                    
                    df_editado = st.data_editor(
                        df_edit[['Resource Name', 'Planned start', 'Planned finish', 'Horas_Alocadas']], 
                        column_config=config_colunas, num_rows="dynamic", use_container_width=True
                    )
                    
                    if st.form_submit_button("💾 Salvar Simulação"):
                        erros = False
                        for idx, row in df_editado.iterrows():
                            if pd.isnull(row['Resource Name']):
                                st.error(f"A linha {idx+1} está sem recurso selecionado.")
                                erros = True
                                
                        if not erros:
                            mask_remover = (df_simulado['Task Code'] == edit_task_code) & (df_simulado['Activity Name'] == edit_activity_name)
                            df_novo = df_simulado[~mask_remover].copy()
                            info_estatica = df_alocacoes.iloc[0].copy()
                            novas_linhas = []
                            
                            old_min_start = pd.to_datetime(df_alocacoes['Planned start']).min().date()
                            old_max_finish = pd.to_datetime(df_alocacoes['Planned finish']).max().date()
                            
                            for idx, row in df_editado.iterrows():
                                orig_row = df_edit.iloc[idx] if idx < len(df_edit) else None
                                
                                rec = row['Resource Name']
                                inicio = row['Planned start']
                                horas = row['Horas_Alocadas']
                                fim_manual = row['Planned finish']
                                
                                if horas <= 0: continue 
                                
                                if orig_row is not None:
                                    if inicio != orig_row['Planned start'] and fim_manual == orig_row['Planned finish'] and horas == orig_row['Horas_Alocadas']:
                                        fim_manual = None 
                                
                                if pd.isnull(fim_manual):
                                    dias_necessarios = math.ceil(horas / 9.18)
                                    fim_calculado = pd.to_datetime(inicio) + pd.offsets.BDay(max(1, dias_necessarios) - 1)
                                    fim = fim_calculado.date()
                                else:
                                    fim = fim_manual
                                
                                dias_uteis = pd.date_range(start=inicio, end=fim, freq='B')
                                if len(dias_uteis) == 0: dias_uteis = [pd.to_datetime(inicio)]
                                horas_por_dia = horas / len(dias_uteis)
                                
                                df_dias = pd.DataFrame({'Data': dias_uteis})
                                df_dias['Mes'] = df_dias['Data'].dt.strftime('%m/%Y')
                                df_dias['Horas'] = horas_por_dia
                                df_meses = df_dias.groupby('Mes')['Horas'].sum().reset_index()
                                
                                for _, row_mes in df_meses.iterrows():
                                    nova_linha = info_estatica.copy()
                                    nova_linha['Mes'] = row_mes['Mes']
                                    nova_linha['Horas_Alocadas'] = row_mes['Horas']
                                    nova_linha['Planned start'] = inicio
                                    nova_linha['Planned finish'] = fim
                                    nova_linha['Resource Name'] = rec
                                    if 'RTC_ID' in info_estatica: nova_linha['RTC_ID'] = info_estatica['RTC_ID']
                                    novas_linhas.append(nova_linha)
                                    
                            if novas_linhas:
                                df_novo = pd.concat([df_novo, pd.DataFrame(novas_linhas)], ignore_index=True)
                                
                                new_min_start = min([pd.to_datetime(r['Planned start']).date() for r in novas_linhas])
                                new_max_finish = max([pd.to_datetime(r['Planned finish']).date() for r in novas_linhas])
                                
                                delta_start = get_bdays_delta(old_min_start, new_min_start)
                                delta_finish = get_bdays_delta(old_max_finish, new_max_finish)
                                
                                if empurrar_sucessoras and (delta_start != 0 or delta_finish != 0):
                                    df_novo, qtd_afetadas = aplicar_cascata(df_novo, edit_line_id, delta_start, delta_finish, usuario)
                                    if qtd_afetadas > 0:
                                        st.session_state['msg_cascata'] = f"🔄 Cascata: {qtd_afetadas} tarefas sucessoras foram ajustadas."
                                
                                st.session_state['df_simulado'] = df_novo
                                registrar_log(usuario, "UPDATE", "tasks_odyc", edit_task_code, "Edição em Lote (Recursos/Horas)", "Valores antigos", "Novos valores de simulação")
                                clear_ui_state()
                                st.rerun()

    # --- ABA 3: VISAO POR RECURSO / MES ---
    with tab_visao:
        st.write("### 📅 Atividades por Recurso e Mês (OdyC)")
        st.write("Edite o **Recurso**, **Datas**, **Horas** ou **RTC ID** diretamente na tabela.")
        
        col_v1, col_v2 = st.columns(2)
        with col_v1: rec_visao = st.selectbox("👤 Selecione o Recurso:", [""] + todos_recursos, key="visao_rec_odyc")
        with col_v2:
            meses_disp = sorted(df_simulado['Mes'].unique(), key=lambda x: pd.to_datetime(x, format='%m/%Y'))
            mes_visao = st.selectbox("📅 Selecione o Mês:", [""] + meses_disp, key="visao_mes_odyc")
            
        if rec_visao and mes_visao:
            mask_visao = (df_simulado['Resource Name'] == rec_visao) & (df_simulado['Mes'] == mes_visao)
            df_visao = df_simulado[mask_visao]
            
            if not df_visao.empty:
                if 'RTC_ID' not in df_visao.columns: df_visao['RTC_ID'] = ""
                df_visao_show = df_visao[['Line identifier', 'Task Code', 'Activity Name', 'Resource Name', 'Planned start', 'Planned finish', 'Horas_Alocadas', 'RTC_ID']].copy()
                df_visao_show = df_visao_show.sort_values('Horas_Alocadas', ascending=False).reset_index(drop=True)
                
                st.success(f"Total de horas alocadas: **{df_visao_show['Horas_Alocadas'].sum():.1f}h**")
                
                with st.form("form_visao_mes_odyc"):
                    config_colunas_visao = {
                        "Line identifier": st.column_config.TextColumn(disabled=True),
                        "Task Code": st.column_config.TextColumn(disabled=True),
                        "Activity Name": st.column_config.TextColumn(disabled=True),
                        "Resource Name": st.column_config.SelectboxColumn("Recurso", options=todos_recursos),
                        "Planned start": st.column_config.DateColumn("Data Início"),
                        "Planned finish": st.column_config.DateColumn("Data Fim"),
                        "Horas_Alocadas": st.column_config.NumberColumn("Horas no Mês", min_value=0.0, format="%.1f"),
                        "RTC_ID": st.column_config.TextColumn("ID do RTC")
                    }
                    
                    df_editado_visao = st.data_editor(df_visao_show, column_config=config_colunas_visao, use_container_width=True, hide_index=True, key="editor_visao_mes_odyc")
                    
                    if st.form_submit_button("💾 Salvar Alterações do Mês"):
                        df_novo = st.session_state['df_simulado'].copy()
                        if 'RTC_ID' not in df_novo.columns: df_novo['RTC_ID'] = ""
                        mudancas_feitas = 0
                        
                        for idx, row in df_editado_visao.iterrows():
                            l_id = row['Line identifier']
                            t_code = row['Task Code']
                            a_name = row['Activity Name']
                            novo_rec = row['Resource Name']
                            novo_inicio = row['Planned start']
                            novo_fim = row['Planned finish']
                            novas_horas = row['Horas_Alocadas']
                            novo_rtc = row['RTC_ID']
                            
                            linha_antiga = df_visao_show.iloc[idx]
                            if (linha_antiga['Resource Name'] != novo_rec or linha_antiga['Horas_Alocadas'] != novas_horas or
                                linha_antiga['Planned start'] != novo_inicio or linha_antiga['Planned finish'] != novo_fim or linha_antiga['RTC_ID'] != novo_rtc):
                                
                                mudancas_feitas += 1
                                registrar_log(usuario, "UPDATE", "tasks_odyc", str(l_id), "Visão Mensal", f"{linha_antiga['Horas_Alocadas']}h", f"{novas_horas}h")
                            
                            mask_linha = (df_novo['Line identifier'] == l_id) & (df_novo['Task Code'] == t_code) & (df_novo['Activity Name'] == a_name) & (df_novo['Resource Name'] == rec_visao) & (df_novo['Mes'] == mes_visao)
                            df_novo.loc[mask_linha, 'Resource Name'] = novo_rec
                            df_novo.loc[mask_linha, 'Horas_Alocadas'] = novas_horas
                            
                            mask_tarefa_rec = (df_novo['Line identifier'] == l_id) & (df_novo['Task Code'] == t_code) & (df_novo['Activity Name'] == a_name) & (df_novo['Resource Name'] == novo_rec)
                            df_novo.loc[mask_tarefa_rec, 'Planned start'] = novo_inicio
                            df_novo.loc[mask_tarefa_rec, 'Planned finish'] = novo_fim
                            
                            mask_tarefa = (df_novo['Line identifier'] == l_id) & (df_novo['Task Code'] == t_code) & (df_novo['Activity Name'] == a_name)
                            df_novo.loc[mask_tarefa, 'RTC_ID'] = novo_rtc
                            
                        st.session_state['df_simulado'] = df_novo
                        st.success(f"✅ {mudancas_feitas} alterações salvas com sucesso!")
                        clear_ui_state()
                        st.rerun()
            else:
                st.info("Nenhuma atividade encontrada para este recurso neste mês.")

    # --- ABA 4: DIVISÃO MANUAL POR MÊS ---
    with tab_dividir:
        st.write("### ✂️ Distribuição Manual por Mês")
        st.write("Ajuste exatamente quantas horas um recurso vai gastar em cada mês para uma tarefa específica. Ideal para tarefas longas que precisam de distribuição irregular.")
        
        col_d1, col_d2 = st.columns(2)
        with col_d1: busca_nome_d = st.text_input("🔍 Buscar Tarefa:", "", key="busca_dividir")
        with col_d2:
            task_codes_list_d = [""] + sorted(df_simulado['Task Code'].dropna().unique().tolist())
            busca_task_d = st.selectbox("📁 Filtrar Task Code:", task_codes_list_d, key="task_dividir")
            
        df_agrupado_d = df_simulado.groupby(['Task Code', 'Activity Name']).size().reset_index()
        df_agrupado_d['Display'] = df_agrupado_d['Task Code'] + " | " + df_agrupado_d['Activity Name']
        
        if busca_nome_d: df_agrupado_d = df_agrupado_d[df_agrupado_d['Display'].str.contains(busca_nome_d, case=False, na=False)]
        if busca_task_d: df_agrupado_d = df_agrupado_d[df_agrupado_d['Task Code'] == busca_task_d]
            
        tarefa_selecionada_d = st.selectbox("1️⃣ Selecione a Tarefa:", [""] + df_agrupado_d['Display'].tolist(), key="sel_task_dividir")
        
        if tarefa_selecionada_d:
            t_code, a_name = tarefa_selecionada_d.split(" | ")
            recursos_tarefa = df_simulado[(df_simulado['Task Code'] == t_code) & (df_simulado['Activity Name'] == a_name)]['Resource Name'].dropna().unique()
            rec_selecionado_d = st.selectbox("2️⃣ Selecione o Recurso:", [""] + list(recursos_tarefa), key="sel_rec_dividir")
            
            if rec_selecionado_d:
                df_aloc = df_simulado[(df_simulado['Task Code'] == t_code) & (df_simulado['Activity Name'] == a_name) & (df_simulado['Resource Name'] == rec_selecionado_d)]
                df_meses_edit = df_aloc.groupby('Mes')['Horas_Alocadas'].sum().reset_index()
                
                st.write(f"**Total de Horas Atual desta Tarefa:** {df_meses_edit['Horas_Alocadas'].sum():.1f}h")
                meses_disponiveis = sorted(df_simulado['Mes'].dropna().unique(), key=lambda x: pd.to_datetime(x, format='%m/%Y'))
                
                with st.form("form_dividir_meses"):
                    st.write("Adicione ou remova linhas para distribuir as horas nos meses desejados:")
                    config_meses = {
                        "Mes": st.column_config.SelectboxColumn("Mês", options=meses_disponiveis, required=True),
                        "Horas_Alocadas": st.column_config.NumberColumn("Horas no Mês", min_value=0.0, format="%.1f", required=True)
                    }
                    
                    df_meses_editado = st.data_editor(df_meses_edit, column_config=config_meses, num_rows="dynamic", use_container_width=True, key="editor_dividir_meses")
                    
                    if st.form_submit_button("💾 Salvar Distribuição Manual"):
                        mask_remover = (df_simulado['Task Code'] == t_code) & (df_simulado['Activity Name'] == a_name) & (df_simulado['Resource Name'] == rec_selecionado_d)
                        df_novo = df_simulado[~mask_remover].copy()
                        info_estatica = df_aloc.iloc[0].copy()
                        
                        novas_linhas = []
                        for _, row in df_meses_editado.iterrows():
                            if row['Horas_Alocadas'] > 0:
                                nova_linha = info_estatica.copy()
                                nova_linha['Mes'] = row['Mes']
                                nova_linha['Horas_Alocadas'] = row['Horas_Alocadas']
                                novas_linhas.append(nova_linha)
                                
                        if novas_linhas:
                            df_novo = pd.concat([df_novo, pd.DataFrame(novas_linhas)], ignore_index=True)
                            
                        st.session_state['df_simulado'] = df_novo
                        registrar_log(usuario, "UPDATE", "tasks_odyc", t_code, "Distribuição Manual", f"{df_meses_edit['Horas_Alocadas'].sum():.1f}h", f"{df_meses_editado['Horas_Alocadas'].sum():.1f}h")
                        st.success("✅ Distribuição salva com sucesso!")
                        clear_ui_state()
                        st.rerun()