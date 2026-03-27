import streamlit as st
import os
import sys
import pickle

# Importações Módulo OdyC (SCADA)
from data_processing_geral import load_and_process_geral, salvar_cenario_geral_no_banco
from datetime import datetime # Vamos precisar disso para gerar nomes de versões
from visualizations import render_gantt, render_heatmap, render_dashboard, render_changelog
from editor import render_editor
from editor_matricial import render_editor_matricial

# Importações Módulo Geral (Workload)
from data_processing_geral import load_and_process_geral
from visualizations_geral import render_dashboard_geral, render_gantt_geral, render_heatmap_geral, render_changelog_geral
from editor_geral import render_editor_geral
from editor_matricial_geral import render_editor_matricial_geral
# from comparator_geral import render_comparator_geral

st.set_page_config(page_title="Gerenciador de Projetos", layout="wide")

# 
# 🔒 SISTEMA DE LOGIN
# 
USUARIOS = {
    "victor": "admin123",
    "ikenaga": "tester",
    "usuario2": "senha2",
    "usuario3": "senha3"
}

def check_login():
    if "logado" not in st.session_state:
        st.session_state["logado"] = False

    if not st.session_state["logado"]:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            st.markdown("<h2 style='text-align: center;'>🔒 Acesso Restrito</h2>", unsafe_allow_html=True)
            st.write("Por favor, insira suas credenciais para acessar o sistema.")
            
            with st.form("login_form"):
                usuario = st.text_input("Usuário").strip().lower()
                senha = st.text_input("Senha", type="password")
                submit = st.form_submit_button("Entrar", use_container_width=True)
                
                if submit:
                    if usuario in USUARIOS and USUARIOS[usuario] == senha:
                        st.session_state["logado"] = True
                        st.session_state["usuario_logado"] = usuario 
                        st.success("Acesso liberado! Carregando...")
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
        return False
    
    if st.sidebar.button("🚪 Sair do Sistema"):
        st.session_state["logado"] = False
        st.rerun()
        
    return True

if not check_login():
    st.stop()

# 
# 🚀 INÍCIO DO APLICATIVO
# 

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()

st.title("📊 Gerenciador de Recursos e Planejamento v2.0")

st.sidebar.header("⚙️ Modo de Operação")
modo = st.sidebar.radio("Selecione o tipo de projeto:", ["OdyC", "Workload Geral"], key="seletor_modo_global")
st.sidebar.markdown("---")

if st.sidebar.button("🔄 Atualizar Visão / Limpar Filtros"):
    # Limpa apenas os filtros e editores, preservando uploaders e dados
    prefixos = ['mat_', 'editor_', 'visao_', 'busca_', 'sel_', 'task_', 'proj_', 'radio_grupo', 'multi_rec']
    for key in list(st.session_state.keys()):
        if any(key.startswith(p) for p in prefixos):
            del st.session_state[key]
    st.rerun()
st.sidebar.markdown("---")

GRUPOS = {
    "SCADA UHMI": ["LUCAS HENRIQUE MARQUES DOS SANTOS", "LUIZ GUILHERME SALVADOR DE OLIVEIRA"],
    "SCADA Dataprep": ["ROBSON LIKI ODA", "DAVI JOSE PEREZ MARTINS PEREIRA", "THAIS FAZOLIN BELINI", "OLIVEIRA JOAO"],
    "ATS - INFRA": ["VINICIUS HEIDI IKENAGA", "ARTHUR FERREIRA MATHIAS", "AUGUSTO LATANZE MENDES"]
}
GRUPOS["SCADA Geral"] = GRUPOS["SCADA UHMI"] + GRUPOS["SCADA Dataprep"]

if modo == "OdyC":
    ARQUIVO_PERSISTENCIA = os.path.join(BASE_DIR, "scada_projeto.pkl")
    
    st.sidebar.header("📥 Importação de Dados (OdyC)")
    arquivo_wkl = st.sidebar.file_uploader("1. Upload WKL (.xlsx, .xlsm)", type=["xlsx", "xlsm"])
    arquivo_schedule = st.sidebar.file_uploader("2. Upload Schedule (.xlsx, .xlsm)", type=["xlsx", "xlsm"])

    if st.sidebar.button("🔄 Iniciar do Zero (Limpar Tudo)"):
        keys_to_keep = ['logado', 'seletor_modo_global']
        for key in list(st.session_state.keys()):
            if key not in keys_to_keep:
                del st.session_state[key]
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("💾 Salvar / Carregar Projeto")

    # --- NOVIDADE: UPLOAD DE ARQUIVO PKL EXTERNO ---
    arquivo_pkl_externo = st.sidebar.file_uploader("📂 Importar Projeto Externo (.pkl)", type=["pkl"], key="pkl_odyc")
    if arquivo_pkl_externo is not None:
        if st.sidebar.button("📥 Carregar Arquivo Importado"):
            try:
                dados = pickle.load(arquivo_pkl_externo)
                st.session_state['df_simulado'] = dados['df_simulado']
                st.session_state['df_original'] = dados['df_original']
                st.session_state['df_capacidade'] = dados['df_capacidade']
                st.session_state['ignored_conflicts'] = dados.get('ignored_conflicts', [])
                st.sidebar.success("Projeto externo carregado com sucesso!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Erro ao carregar arquivo: {e}")

    # Carregar arquivo local (se existir)
    if os.path.exists(ARQUIVO_PERSISTENCIA):
        if st.sidebar.button("📂 Carregar Projeto Local"):
            with open(ARQUIVO_PERSISTENCIA, 'rb') as f:
                dados = pickle.load(f)
                st.session_state['df_simulado'] = dados['df_simulado']
                st.session_state['df_original'] = dados['df_original']
                st.session_state['df_capacidade'] = dados['df_capacidade']
                st.session_state['ignored_conflicts'] = dados.get('ignored_conflicts', [])
            st.sidebar.success("Projeto local carregado com sucesso!")
            st.rerun()

    if st.sidebar.button("💾 Salvar Projeto Atual"):
        if 'df_simulado' in st.session_state:
            with open(ARQUIVO_PERSISTENCIA, 'wb') as f:
                pickle.dump({
                    'df_simulado': st.session_state['df_simulado'],
                    'df_original': st.session_state['df_original'],
                    'df_capacidade': st.session_state['df_capacidade'],
                    'ignored_conflicts': st.session_state.get('ignored_conflicts', [])
                }, f)
            st.sidebar.success(f"Projeto salvo localmente em: {BASE_DIR}")
        else:
            st.sidebar.warning("Nenhum dado para salvar.")

    tem_arquivos = arquivo_wkl is not None and arquivo_schedule is not None
    tem_dados_memoria = 'df_simulado' in st.session_state

    if tem_arquivos or tem_dados_memoria:
        with st.spinner('Processando dados OdyC...'):
            try:
                if tem_arquivos and 'df_original' not in st.session_state:
                    df_master, df_capacidade = load_and_process_data(arquivo_wkl, arquivo_schedule)

                    # --- NOVIDADE: SALVA NO BANCO DE DADOS ---
                    autor = st.session_state.get("usuario_logado", "Sistema")
                    cenario_id = salvar_cenario_odyc_no_banco(df_master, nome_cenario="Carga Inicial Excel", autor=autor)
                    st.session_state['cenario_odyc_id'] = cenario_id # Guarda o ID atual
                    # -----------------------------------------

                    st.session_state['df_original'] = df_master.copy()
                    st.session_state['df_simulado'] = df_master.copy()
                    st.session_state['df_capacidade'] = df_capacidade.copy()
                
                df_simulado = st.session_state['df_simulado']
                df_original = st.session_state['df_original']
                df_capacidade = st.session_state['df_capacidade']
                
                st.sidebar.markdown("---")
                st.sidebar.header("👥 Filtro Global de Equipe")
                
                opcoes_filtro = ["Todas as Equipes"] + list(GRUPOS.keys()) + ["Personalizado"]
                opcao_grupo = st.sidebar.radio("Selecione a visão:", opcoes_filtro)
                
                recursos_disponiveis = sorted(df_simulado['Resource Name'].dropna().unique())
                recursos_filtro = recursos_disponiveis
                
                if opcao_grupo in GRUPOS:
                    recursos_filtro = GRUPOS[opcao_grupo]
                elif opcao_grupo == "Personalizado":
                    recursos_filtro = st.sidebar.multiselect("Selecione os recursos:", recursos_disponiveis, default=recursos_disponiveis)
                
                df_simulado_view = df_simulado[df_simulado['Resource Name'].isin(recursos_filtro)].copy() if recursos_filtro else df_simulado.copy()

                aba_dash, aba_gantt, aba_heatmap, aba_simulador, aba_matricial, aba_changelog = st.tabs([
                    "📈 Dashboard Geral", "📊 Gantt", "🔥 Capacidade", "✏️ Simulador", "📁 Matriz Editável", "⚠️ Resumo de Alterações"
                ])
                
                with aba_dash: render_dashboard(df_simulado_view)
                with aba_gantt: render_gantt(df_simulado_view, key_suffix="simulado")
                with aba_heatmap: render_heatmap(df_simulado_view, df_capacidade, key_suffix="simulado")
                with aba_simulador: render_editor()
                with aba_matricial: render_editor_matricial()
                with aba_changelog: render_changelog(df_original, df_simulado)
                    
            except Exception as e:
                st.error(f"Erro no processamento OdyC: {e}")
    else:
        st.info("👈 Faça o upload dos arquivos ou carregue um projeto salvo para começar.")

elif modo == "Workload Geral":
    ARQUIVO_PERSISTENCIA_GERAL = os.path.join(BASE_DIR, "geral_projeto.pkl")
    ARQUIVO_BASELINE_GERAL = os.path.join(BASE_DIR, "baseline_geral.pkl")
    
    st.sidebar.header("📥 Importação de Dados (Geral)")
    arquivo_geral = st.sidebar.file_uploader("Upload Planilha Workload (.xlsx, .xlsm)", type=["xlsx", "xlsm"])
    
    if st.sidebar.button("🔄 Iniciar do Zero (Limpar Tudo)"):
        keys_to_keep = ['logado', 'seletor_modo_global']
        for key in list(st.session_state.keys()):
            if key not in keys_to_keep:
                del st.session_state[key]
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.header("💾 Salvar / Carregar Projeto")

    # --- NOVIDADE: UPLOAD DE ARQUIVO PKL EXTERNO (GERAL) ---
    arquivo_pkl_geral = st.sidebar.file_uploader("📂 Importar Projeto Externo (.pkl)", type=["pkl"], key="pkl_geral")
    if arquivo_pkl_geral is not None:
        if st.sidebar.button("📥 Carregar Arquivo Importado"):
            try:
                dados = pickle.load(arquivo_pkl_geral)
                st.session_state['df_geral'] = dados['df_geral']
                st.session_state['df_original_geral'] = dados['df_original_geral']
                st.session_state['df_cap_geral'] = dados['df_cap_geral']
                st.sidebar.success("Projeto externo carregado com sucesso!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Erro ao carregar arquivo: {e}")

    if os.path.exists(ARQUIVO_PERSISTENCIA_GERAL):
        if st.sidebar.button("📂 Carregar Projeto Local"):
            with open(ARQUIVO_PERSISTENCIA_GERAL, 'rb') as f:
                dados = pickle.load(f)
                st.session_state['df_geral'] = dados['df_geral']
                st.session_state['df_original_geral'] = dados['df_original_geral']
                st.session_state['df_cap_geral'] = dados['df_cap_geral']
            st.sidebar.success("Projeto Geral local carregado com sucesso!")
            st.rerun()

    if st.sidebar.button("💾 Salvar Nova Versão no Banco"):
    if 'df_geral' in st.session_state:
        autor = st.session_state.get("usuario_logado", "Sistema")
        data_hora = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        novo_id = salvar_cenario_geral_no_banco(st.session_state['df_geral'], nome_cenario=f"Versão Geral {data_hora}", autor=autor)
        
        st.session_state['cenario_geral_id'] = novo_id
        st.sidebar.success(f"Nova versão salva no Banco de Dados! (ID: {novo_id})")
    else:
        st.sidebar.warning("Nenhum dado para salvar.")
            
    st.sidebar.markdown("---")
    st.sidebar.header("📸 Gestão de Baseline")
    st.sidebar.write("Tire uma 'foto' do mês para comparar com o próximo arquivo.")
    
    if os.path.exists(ARQUIVO_BASELINE_GERAL):
        if st.sidebar.button("📂 Carregar Baseline Anterior"):
            with open(ARQUIVO_BASELINE_GERAL, 'rb') as f:
                st.session_state['df_baseline_geral'] = pickle.load(f)
            st.sidebar.success("Baseline carregada com sucesso!")
            st.rerun()
            
    if 'df_geral' in st.session_state:
        if st.sidebar.button("📸 Salvar Atual como Baseline"):
            with open(ARQUIVO_BASELINE_GERAL, 'wb') as f:
                pickle.dump(st.session_state['df_geral'], f)
            st.session_state['df_baseline_geral'] = st.session_state['df_geral'].copy()
            st.sidebar.success(f"Baseline salva em: {BASE_DIR}")
            st.rerun()
            
    tem_arquivos_geral = arquivo_geral is not None
    tem_dados_memoria_geral = 'df_geral' in st.session_state
    tem_baseline = 'df_baseline_geral' in st.session_state

    if tem_arquivos_geral or tem_dados_memoria_geral:
        with st.spinner('Processando dados gerais...'):
            try:
                if tem_arquivos_geral and 'df_original_geral' not in st.session_state:
                    df_alocacao, df_capacidade = load_and_process_geral(arquivo_geral)
                    autor = st.session_state.get("usuario_logado", "Sistema")
                    cenario_id = salvar_cenario_geral_no_banco(df_alocacao, nome_cenario="Carga Inicial Geral Excel", autor=autor)
                    st.session_state['cenario_geral_id'] = cenario_id
                    st.session_state['df_original_geral'] = df_alocacao.copy()
                    st.session_state['df_geral'] = df_alocacao.copy()
                    st.session_state['df_cap_geral'] = df_capacidade.copy()
                
                df_geral = st.session_state['df_geral']
                df_cap_geral = st.session_state['df_cap_geral']
                
                st.sidebar.markdown("---")
                st.sidebar.header("👥 Filtro Global de Equipe")
                
                opcoes_filtro = ["Todas as Equipes"] + list(GRUPOS.keys()) + ["Personalizado"]
                opcao_grupo = st.sidebar.radio("Selecione a visão:", opcoes_filtro, key="radio_grupo_geral")
                
                recursos_disponiveis = sorted(df_geral['Resource Name'].dropna().unique())
                recursos_filtro = recursos_disponiveis
                
                if opcao_grupo in GRUPOS:
                    recursos_filtro = GRUPOS[opcao_grupo]
                elif opcao_grupo == "Personalizado":
                    recursos_filtro = st.sidebar.multiselect("Selecione os recursos:", recursos_disponiveis, default=recursos_disponiveis, key="multi_rec_geral")
                
                df_geral_view = df_geral[df_geral['Resource Name'].isin(recursos_filtro)].copy() if recursos_filtro else df_geral.copy()
                
                abas_titulos = ["📈 Dashboard", "📊 Gantt", "🔥 Capacidade", "✏️ Simulador", "📁 Matriz Editável", "⚠️ Resumo de Alterações"]
                if tem_baseline:
                    abas_titulos.append("⚖️ Comparativo")
                    
                abas = st.tabs(abas_titulos)
                
                with abas[0]: render_dashboard_geral(df_geral_view)
                with abas[1]: render_gantt_geral(df_geral_view)
                with abas[2]: render_heatmap_geral(df_geral_view, df_cap_geral)
                with abas[3]: render_editor_geral()
                with abas[4]: render_editor_matricial_geral()
                with abas[5]: render_changelog_geral(st.session_state['df_original_geral'], df_geral)
                
                if tem_baseline:
                    with abas[6]: 
                        df_base_view = st.session_state['df_baseline_geral']
                        if recursos_filtro:
                            df_base_view = df_base_view[df_base_view['Resource Name'].isin(recursos_filtro)].copy()
                        # render_comparator_geral(df_base_view, df_geral_view)
                    
            except Exception as e:
                st.error(f"Erro ao processar a planilha Geral: {e}")
    else:
        st.info("👈 Faça o upload da planilha de Workload Geral ou carregue um projeto para começar.")