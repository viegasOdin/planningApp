import streamlit as st
import pandas as pd
import numpy as np
import math
from utils import registrar_log  # <-- NOVIDADE: Importando nosso espião de logs

def clear_ui_state():
    # Limpa apenas os estados dos filtros internos e editores
    prefixos = ['mat_', 'editor_', 'visao_', 'busca_', 'sel_', 'task_', 'proj_']
    for key in list(st.session_state.keys()):
        if any(key.startswith(p) for p in prefixos):
            del st.session_state[key]

def render_editor_geral():
    st.subheader("✏️ Simulador de Cenários (Geral)")
    df_geral = st.session_state['df_geral']
    
    # Pega o nome do usuário logado para colocar no Log
    usuario = st.session_state.get("usuario_logado", "Desconhecido") 
    
    todos_recursos = sorted(df_geral['Resource Name'].dropna().unique())
    
    tab_editar, tab_nova, tab_visao, tab_dividir = st.tabs(["📝 Editar Existente", "➕ Criar Nova Tarefa", "📅 Visão por Recurso/Mês", "✂️ Dividir Horas por Mês"])
    
    with tab_nova:
        st.write("Adicione uma nova atividade vinculada a um recurso e projeto existente.")
        with st.form("form_nova_tarefa_geral"):
            col_n1, col_n2 = st.columns(2)
            
            novo_rec = col_n1.selectbox("1️⃣ Recurso:", todos_recursos)
            
            projetos_recurso = df_geral[df_geral['Resource Name'] == novo_rec]['Project Name'].dropna().unique()
            if len(projetos_recurso) == 0:
                projetos_recurso = df_geral['Project Name'].dropna().unique()
                
            novo_projeto = col_n2.selectbox("2️⃣ Projeto:", sorted(projetos_recurso))
            novo_activity = st.text_input("3️⃣ Nome da Atividade:", "Nova Atividade")
            
            col_n4, col_n5 = st.columns(2)
            nova_data_ini = col_n4.date_input("Data Início:")
            novas_horas = col_n5.number_input("Total de Horas:", min_value=1.0, value=40.0)
            
            st.write("---")
            tipo_fim = st.radio("Definição da Data Fim:", ["Automático (9,18h/dia útil)", "Data Fixa Manual"], key="radio_fim_geral")
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
                
                class_br = df_geral[df_geral['Project Name'] == novo_projeto]['ClassBR'].iloc[0] if not df_geral[df_geral['Project Name'] == novo_projeto].empty else "Unknown"
                cc_name = df_geral[df_geral['Project Name'] == novo_projeto]['CostCenter Name'].iloc[0] if not df_geral[df_geral['Project Name'] == novo_projeto].empty else "N/A"
                
                novas_linhas = []
                for _, row_mes in df_meses.iterrows():
                    novas_linhas.append({
                        'Project Name': novo_projeto,
                        'Activity Name': novo_activity,
                        'Resource Name': novo_rec,
                        'Planned start': nova_data_ini,
                        'Planned finish': nova_data_fim,
                        'Horas_Alocadas': row_mes['Horas'],
                        'Mes': row_mes['Mes'],
                        'RTC_ID': novo_rtc,
                        'ClassBR': class_br,
                        'CostCenter Name': cc_name
                    })
                    
                st.session_state['df_geral'] = pd.concat([df_geral, pd.DataFrame(novas_linhas)], ignore_index=True)
                
                # --- REGISTRO DE LOG ---
                registrar_log(
                    user_id=usuario,
                    action="CREATE",
                    table_affected="tasks_geral",
                    record_id=f"{novo_projeto} | {novo_activity}",
                    field_changed="Nova Tarefa",
                    old_value="",
                    new_value=f"{novas_horas}h para {novo_rec}"
                )
                
                st.success("Tarefa criada com sucesso! O aplicativo será recarregado...")
                clear_ui_state()
                st.rerun()

    with tab_editar:
        st.info("💡 **Dica para Dividir Tarefas:** Para alocar mais de um recurso na mesma tarefa, basta adicionar uma nova linha na tabela abaixo, escolher o novo recurso e definir as horas dele!")
        col_busca1, col_busca2, col_busca3 = st.columns(3)
        with col_busca1:
            busca_nome = st.text_input("🔍 Buscar por Nome da Tarefa:", "")
        with col_busca2:
            projetos_list = [""] + sorted(df_geral['Project Name'].dropna().unique().tolist())
            busca_proj = st.selectbox("📁 Filtrar por Projeto:", projetos_list)
        with col_busca3:
            cc_list = [""] + sorted(df_geral['CostCenter Name'].dropna().unique().tolist())
            busca_cc = st.selectbox("🏢 Filtrar por CostCenter:", cc_list)
            
        df_tarefas = df_geral.dropna(subset=['Planned start', 'Planned finish']).copy()
        
        if df_tarefas.empty:
            st.warning("Não há tarefas com datas válidas para editar.")
            return
            
        df_agrupado = df_tarefas.groupby(['Project Name', 'Activity Name']).agg({
            'Planned start': 'first', 'Planned finish': 'first', 'CostCenter Name': 'first'
        }).reset_index()
        df_agrupado['Display'] = df_agrupado['Project Name'] + " | " + df_agrupado['Activity Name']
        
        if busca_nome: df_agrupado = df_agrupado[df_agrupado['Display'].str.contains(busca_nome, case=False, na=False)]
        if busca_proj: df_agrupado = df_agrupado[df_agrupado['Project Name'] == busca_proj]
        if busca_cc: df_agrupado = df_agrupado[df_agrupado['CostCenter Name'] == busca_cc]
            
        if df_agrupado.empty:
            st.info("Nenhuma tarefa encontrada com esses filtros combinados.")
            return
            
        tarefa_selecionada = st.selectbox("1️⃣ Selecione a Tarefa para Editar:", [""] + df_agrupado['Display'].tolist())
        
        if tarefa_selecionada:
            linha_atual = df_agrupado[df_agrupado['Display'] == tarefa_selecionada].iloc[0]
            p_name = linha_atual['Project Name']
            a_name = linha_atual['Activity Name']
            
            st.write("---")
            st.write("### 👥 Edição de Recursos (Cálculo Automático)")
            
            df_alocacoes = df_geral[(df_geral['Project Name'] == p_name) & (df_geral['Activity Name'] == a_name)]
            df_edit = df_alocacoes.groupby('Resource Name').agg({
                'Planned start': 'first', 'Planned finish': 'first', 'Horas_Alocadas': 'sum'
            }).reset_index()
            
            with st.form("form_edicao_multipla_geral"):
                st.write("💡 **Dica de Data Fim:** Se você deixar a **Data Fim vazia**, o sistema vai calcular automaticamente os dias úteis necessários considerando **9,18h por dia**.")
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
                        mask_remover = (df_geral['Project Name'] == p_name) & (df_geral['Activity Name'] == a_name)
                        df_novo = df_geral[~mask_remover].copy()
                        info_estatica = df_alocacoes.iloc[0].copy()
                        novas_linhas = []
                        
                        for _, row in df_editado.iterrows():
                            rec = row['Resource Name']
                            inicio = row['Planned start']
                            horas = row['Horas_Alocadas']
                            fim_manual = row['Planned finish']
                            
                            if horas <= 0: continue 
                            
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
                            
                        st.session_state['df_geral'] = df_novo
                        
                        # --- REGISTRO DE LOG ---
                        registrar_log(
                            user_id=usuario,
                            action="UPDATE",
                            table_affected="tasks_geral",
                            record_id=f"{p_name} | {a_name}",
                            field_changed="Edição em Lote (Recursos/Horas)",
                            old_value="Valores antigos",
                            new_value="Novos valores de simulação"
                        )
                        
                        st.success("✅ Simulação salva!")
                        clear_ui_state()
                        st.rerun()

    with tab_visao:
        st.write("### 📅 Atividades por Recurso e Mês")
        st.write("Edite o **Recurso**, **Datas**, **Horas** ou **RTC ID** diretamente na tabela.")
        
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            rec_visao = st.selectbox("👤 Selecione o Recurso:", [""] + todos_recursos, key="visao_rec")
        with col_v2:
            meses_disp = sorted(df_geral['Mes'].unique(), key=lambda x: pd.to_datetime(x, format='%m/%Y'))
            mes_visao = st.selectbox("📅 Selecione o Mês:", [""] + meses_disp, key="visao_mes")
            
        if rec_visao and mes_visao:
            mask_visao = (df_geral['Resource Name'] == rec_visao) & (df_geral['Mes'] == mes_visao)
            df_visao = df_geral[mask_visao]
            
            if not df_visao.empty:
                df_visao_show = df_visao[['Project Name', 'Activity Name', 'CostCenter Name', 'Resource Name', 'Planned start', 'Planned finish', 'Horas_Alocadas', 'RTC_ID']].copy()
                
                # CORREÇÃO: reset_index(drop=True) para evitar o erro "out-of-bounds"
                df_visao_show = df_visao_show.sort_values('Horas_Alocadas', ascending=False).reset_index(drop=True)
                
                st.success(f"Total de horas alocadas: **{df_visao_show['Horas_Alocadas'].sum():.1f}h**")
                
                with st.form("form_visao_mes"):
                    config_colunas_visao = {
                        "Project Name": st.column_config.TextColumn(disabled=True),
                        "Activity Name": st.column_config.TextColumn(disabled=True),
                        "CostCenter Name": st.column_config.TextColumn(disabled=True),
                        "Resource Name": st.column_config.SelectboxColumn("Recurso", options=todos_recursos),
                        "Planned start": st.column_config.DateColumn("Data Início"),
                        "Planned finish": st.column_config.DateColumn("Data Fim"),
                        "Horas_Alocadas": st.column_config.NumberColumn("Horas no Mês", min_value=0.0, format="%.1f"),
                        "RTC_ID": st.column_config.TextColumn("ID do RTC")
                    }
                    
                    df_editado_visao = st.data_editor(
                        df_visao_show,
                        column_config=config_colunas_visao,
                        use_container_width=True,
                        hide_index=True,
                        key="editor_visao_mes"
                    )
                    
                    if st.form_submit_button("💾 Salvar Alterações do Mês"):
                        df_novo = st.session_state['df_geral'].copy()
                        mudancas_feitas = 0
                        
                        for idx, row in df_editado_visao.iterrows():
                            p_name = row['Project Name']
                            a_name = row['Activity Name']
                            novo_rec = row['Resource Name']
                            novo_inicio = row['Planned start']
                            novo_fim = row['Planned finish']
                            novas_horas = row['Horas_Alocadas']
                            novo_rtc = row['RTC_ID']
                            
                            # Verifica se houve mudança para logar
                            linha_antiga = df_visao_show.iloc[idx]
                            if (linha_antiga['Resource Name'] != novo_rec or 
                                linha_antiga['Horas_Alocadas'] != novas_horas or
                                linha_antiga['Planned start'] != novo_inicio or
                                linha_antiga['Planned finish'] != novo_fim or
                                linha_antiga['RTC_ID'] != novo_rtc):
                                
                                mudancas_feitas += 1
                                # --- REGISTRO DE LOG ---
                                registrar_log(
                                    user_id=usuario,
                                    action="UPDATE",
                                    table_affected="tasks_geral",
                                    record_id=f"{p_name} | {a_name}",
                                    field_changed="Visão Mensal",
                                    old_value=f"{linha_antiga['Horas_Alocadas']}h",
                                    new_value=f"{novas_horas}h"
                                )
                            
                            mask_linha = (df_novo['Project Name'] == p_name) & \
                                         (df_novo['Activity Name'] == a_name) & \
                                         (df_novo['Resource Name'] == rec_visao) & \
                                         (df_novo['Mes'] == mes_visao)
                            
                            df_novo.loc[mask_linha, 'Resource Name'] = novo_rec
                            df_novo.loc[mask_linha, 'Horas_Alocadas'] = novas_horas
                            
                            mask_tarefa_rec = (df_novo['Project Name'] == p_name) & \
                                              (df_novo['Activity Name'] == a_name) & \
                                              (df_novo['Resource Name'] == novo_rec)
                            
                            df_novo.loc[mask_tarefa_rec, 'Planned start'] = novo_inicio
                            df_novo.loc[mask_tarefa_rec, 'Planned finish'] = novo_fim
                            
                            mask_tarefa = (df_novo['Project Name'] == p_name) & (df_novo['Activity Name'] == a_name)
                            df_novo.loc[mask_tarefa, 'RTC_ID'] = novo_rtc
                            
                        st.session_state['df_geral'] = df_novo
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
        with col_d1:
            busca_nome_d = st.text_input("🔍 Buscar Tarefa:", "", key="busca_dividir_g")
        with col_d2:
            projetos_list_d = [""] + sorted(df_geral['Project Name'].dropna().unique().tolist())
            busca_proj_d = st.selectbox("📁 Filtrar Projeto:", projetos_list_d, key="proj_dividir_g")
            
        df_agrupado_d = df_geral.groupby(['Project Name', 'Activity Name']).size().reset_index()
        df_agrupado_d['Display'] = df_agrupado_d['Project Name'] + " | " + df_agrupado_d['Activity Name']
        
        if busca_nome_d: df_agrupado_d = df_agrupado_d[df_agrupado_d['Display'].str.contains(busca_nome_d, case=False, na=False)]
        if busca_proj_d: df_agrupado_d = df_agrupado_d[df_agrupado_d['Project Name'] == busca_proj_d]
            
        tarefa_selecionada_d = st.selectbox("1️⃣ Selecione a Tarefa:", [""] + df_agrupado_d['Display'].tolist(), key="sel_task_dividir_g")
        
        if tarefa_selecionada_d:
            p_name, a_name = tarefa_selecionada_d.split(" | ")
            recursos_tarefa = df_geral[(df_geral['Project Name'] == p_name) & (df_geral['Activity Name'] == a_name)]['Resource Name'].dropna().unique()
            
            rec_selecionado_d = st.selectbox("2️⃣ Selecione o Recurso:", [""] + list(recursos_tarefa), key="sel_rec_dividir_g")
            
            if rec_selecionado_d:
                df_aloc = df_geral[(df_geral['Project Name'] == p_name) & (df_geral['Activity Name'] == a_name) & (df_geral['Resource Name'] == rec_selecionado_d)]
                
                df_meses_edit = df_aloc.groupby('Mes')['Horas_Alocadas'].sum().reset_index()
                
                st.write(f"**Total de Horas Atual desta Tarefa:** {df_meses_edit['Horas_Alocadas'].sum():.1f}h")
                
                meses_disponiveis = sorted(df_geral['Mes'].dropna().unique(), key=lambda x: pd.to_datetime(x, format='%m/%Y'))
                
                with st.form("form_dividir_meses_g"):
                    st.write("Adicione ou remova linhas para distribuir as horas nos meses desejados:")
                    config_meses = {
                        "Mes": st.column_config.SelectboxColumn("Mês", options=meses_disponiveis, required=True),
                        "Horas_Alocadas": st.column_config.NumberColumn("Horas no Mês", min_value=0.0, format="%.1f", required=True)
                    }
                    
                    df_meses_editado = st.data_editor(
                        df_meses_edit,
                        column_config=config_meses,
                        num_rows="dynamic",
                        use_container_width=True,
                        key="editor_dividir_meses_g"
                    )
                    
                    if st.form_submit_button("💾 Salvar Distribuição Manual"):
                        mask_remover = (df_geral['Project Name'] == p_name) & (df_geral['Activity Name'] == a_name) & (df_geral['Resource Name'] == rec_selecionado_d)
                        df_novo = df_geral[~mask_remover].copy()
                        
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
                            
                        st.session_state['df_geral'] = df_novo
                        
                        # --- REGISTRO DE LOG ---
                        registrar_log(
                            user_id=usuario,
                            action="UPDATE",
                            table_affected="tasks_geral",
                            record_id=f"{p_name} | {a_name}",
                            field_changed="Distribuição Manual",
                            old_value=f"{df_meses_edit['Horas_Alocadas'].sum():.1f}h",
                            new_value=f"{df_meses_editado['Horas_Alocadas'].sum():.1f}h"
                        )
                        
                        st.success("✅ Distribuição salva com sucesso!")
                        clear_ui_state()
                        st.rerun()