--

### 🏗️ 1. Arquitetura e Resumo dos Módulos

O aplicativo foi dividido em **12 arquivos** para garantir organização, facilidade de manutenção e escalabilidade. Ele opera em dois grandes modos: **OdyC (SCADA)** e **Workload Geral**.

1. **`app.py` (O Coração do Sistema)**
   * **Função:** Gerencia o roteamento das páginas, o sistema de Login (proteção de acesso), o menu lateral, os filtros globais de equipe e a persistência de dados (salvar/carregar `.pkl`).
2. **`editor.py` e `editor_geral.py` (Simuladores de Cenários)**
   * **Função:** Permitem criar, editar e excluir tarefas. Incluem a inteligência de cálculo automático de dias úteis (9,18h/dia) e a aba de "Divisão Manual por Mês" para fatiar tarefas longas.
3. **`editor_matricial.py` e `editor_matricial_geral.py` (Visão Tabela Dinâmica)**
   * **Função:** Criam uma visão matricial (Projeto -> Atividade -> Recurso -> Meses). Permitem digitar horas diretamente nos meses. O código faz engenharia reversa para salvar os dados e recalcula automaticamente as datas de Início e Fim da tarefa com base nos meses preenchidos.
4. **`comparator_geral.py` (Gestão de Baseline)**
   * **Função:** Compara uma "foto" do mês anterior com os dados atuais, gerando KPIs de variação (Delta) e listando quais tarefas entraram ou saíram do planejamento.
5. **`data_processing.py` e `data_processing_geral.py` (ETL - Extração e Limpeza)**
   * **Função:** Lêem os arquivos Excel (`.xlsx`, `.xlsm`), limpam os dados, cruzam as informações de Schedule com Workload e preparam os DataFrames para o Streamlit.
6. **`visualizations.py` e `visualizations_geral.py` (Gráficos e Dashboards)**
   * **Função:** Geram os gráficos interativos usando Plotly (Gantt, Heatmap de Capacidade com regras de cores 80-119% verde, Dashboard de KPIs e Resumo de Alterações).
7. **`run_app.py` e `requirements.txt` (Motores de Compilação)**
   * **Função:** O `run_app.py` "engana" o Streamlit para rodar dentro de um executável fechado, e o `requirements.txt` lista as bibliotecas necessárias.

---

### ⚙️ 2. Ambiente de Desenvolvimento e Compilação

**Desenvolvimento (Mac M3):**
* Feito no macOS usando VSCode.
* Ambiente virtual (`venv`) isolado para evitar conflitos de versão.
* Testes locais rápidos rodando `streamlit run app.py`.

**Compilação para Produção (Windows 11 via Parallels):**
* **O Pulo do Gato:** Como o Mac M3 é arquitetura ARM, a compilação precisou ser feita em uma VM Windows 11. Foi instalado o **Python x64 (Intel/AMD)** nativo do Windows para garantir que o `.exe` rode nos computadores corporativos dos colegas.
* **Segurança:** O código-fonte e as senhas de login foram embutidos e criptografados dentro de um único arquivo `.exe` usando a biblioteca **PyInstaller**.

**Comando Oficial de Compilação:**
```cmd
pyinstaller --onefile --windowed --add-data "app.py;." --add-data "data_processing.py;." --add-data "visualizations.py;." --add-data "editor.py;." --add-data "data_processing_geral.py;." --add-data "visualizations_geral.py;." --add-data "editor_geral.py;." --add-data "comparator_geral.py;." --add-data "editor_matricial.py;." --add-data "editor_matricial_geral.py;." --collect-all streamlit --collect-all plotly --collect-all pandas run_app.py
```

---

### 💻 3. Código Completo dos Módulos Estruturais

*(Nota: Os arquivos de processamento de dados e visualizações (`data_processing` e `visualizations`) mantêm a estrutura de ETL e Plotly que homologamos nas primeiras etapas. Abaixo estão os códigos completos dos motores de interface, edição e compilação que construímos recentemente).*

#### Arquivo 1: `requirements.txt`
```text
streamlit
pandas
plotly
openpyxl
numpy
xlrd
pyinstaller
```

#### Arquivo 2: `run_app.py`
```python
import os
import sys
import streamlit.web.cli as stcli

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        diretorio = sys._MEIPASS
    else:
        diretorio = os.path.dirname(os.path.abspath(__file__))
        
    app_path = os.path.join(diretorio, 'app.py')
    sys.argv = ["streamlit", "run", app_path, "--global.developmentMode=false"]
    sys.exit(stcli.main())
```

#### Arquivo 3: `app.py`
```python
import streamlit as st
import os
import sys
import pickle

# Importações Módulo OdyC (SCADA)
from data_processing import load_and_process_data
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

    if st.sidebar.button("💾 Salvar Projeto Atual"):
        if 'df_geral' in st.session_state:
            with open(ARQUIVO_PERSISTENCIA_GERAL, 'wb') as f:
                pickle.dump({
                    'df_geral': st.session_state['df_geral'],
                    'df_original_geral': st.session_state['df_original_geral'],
                    'df_cap_geral': st.session_state['df_cap_geral']
                }, f)
            st.sidebar.success(f"Projeto Geral salvo localmente em: {BASE_DIR}")
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
```

#### Arquivo 4: `editor_matricial.py` (Exemplo da Lógica de Matriz e Datas)
```python
import streamlit as st
import pandas as pd
import numpy as np

def render_editor_matricial():
    st.subheader("📁 Visão e Edição Matricial por Projeto")
    st.write("Edite as horas diretamente. A tabela exibe a partir do mês inicial até **4 meses depois** da última entrega. Use os filtros de data para focar em um período específico.")
    
    df_simulado = st.session_state['df_simulado']
    
    col1, col2 = st.columns(2)
    projetos = ["Todos"] + sorted(df_simulado['Task Code'].dropna().unique().tolist())
    proj_selecionado = col1.selectbox("🔍 Filtrar por Task Code:", projetos, key="mat_proj_odyc")
    
    recursos = ["Todos"] + sorted(df_simulado['Resource Name'].dropna().unique().tolist())
    rec_selecionado = col2.selectbox("👤 Filtrar por Recurso:", recursos, key="mat_rec_odyc")
    
    # --- NOVIDADE: Filtros de Data ---
    col3, col4 = st.columns(2)
    data_inicio_filtro = col3.date_input("📅 Filtrar a partir de (Início):", value=None, key="mat_dt_ini_odyc")
    data_fim_filtro = col4.date_input("📅 Filtrar até (Fim):", value=None, key="mat_dt_fim_odyc")
    
    df_filtrado = df_simulado.copy()
    if proj_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Task Code'] == proj_selecionado]
    if rec_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Resource Name'] == rec_selecionado]
        
    # Aplicar filtro de datas nas tarefas
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

    df_grouped = df_filtrado.groupby(['Task Code', 'Activity Name', 'Resource Name', 'Mes'])['Horas_Alocadas'].sum().reset_index()
    df_pivot = df_grouped.pivot_table(
        index=['Task Code', 'Activity Name', 'Resource Name'],
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
    
    # Puxar o total geral da tarefa (mesmo que alguns meses fiquem fora do filtro)
    total_por_tarefa = df_grouped.groupby(['Task Code', 'Activity Name', 'Resource Name'])['Horas_Alocadas'].sum().reset_index()
    total_por_tarefa.rename(columns={'Horas_Alocadas': 'Total (Horas)'}, inplace=True)
    
    df_pivot = pd.merge(df_pivot, total_por_tarefa, on=['Task Code', 'Activity Name', 'Resource Name'], how='left')
    
    cols_exibicao = ['Task Code', 'Activity Name', 'Resource Name', 'Total (Horas)'] + meses_cols
    for col in cols_exibicao:
        if col not in df_pivot.columns:
            df_pivot[col] = 0.0
            
    df_pivot = df_pivot[cols_exibicao]
    
    config_colunas = {
        "Task Code": st.column_config.TextColumn(disabled=True),
        "Activity Name": st.column_config.TextColumn(disabled=True),
        "Resource Name": st.column_config.TextColumn(disabled=True),
        "Total (Horas)": st.column_config.NumberColumn("Total (Geral)", disabled=True, format="%.1f")
    }
    for mes in meses_cols:
        config_colunas[mes] = st.column_config.NumberColumn(mes, min_value=0.0, format="%.1f")
        
    with st.form("form_matricial_odyc"):
        df_editado = st.data_editor(
            df_pivot,
            column_config=config_colunas,
            use_container_width=True,
            hide_index=True,
            key="editor_mat_odyc_ui"
        )
        
        if st.form_submit_button("💾 Salvar Alterações Matriciais"):
            df_novo = st.session_state['df_simulado'].copy()
            
            df_melted_original = df_pivot.melt(id_vars=['Task Code', 'Activity Name', 'Resource Name'], value_vars=meses_cols, var_name='Mes', value_name='Horas_Alocadas_orig')
            df_melted_editado = df_editado.melt(id_vars=['Task Code', 'Activity Name', 'Resource Name'], value_vars=meses_cols, var_name='Mes', value_name='Horas_Alocadas_novo')
            
            df_diff = pd.merge(df_melted_original, df_melted_editado, on=['Task Code', 'Activity Name', 'Resource Name', 'Mes'])
            df_changed = df_diff[df_diff['Horas_Alocadas_orig'] != df_diff['Horas_Alocadas_novo']]
            
            if df_changed.empty:
                st.warning("Nenhuma alteração detectada.")
            else:
                for _, row in df_changed.iterrows():
                    t_code = row['Task Code']
                    a_name = row['Activity Name']
                    rec = row['Resource Name']
                    mes = row['Mes']
                    nova_hora = row['Horas_Alocadas_novo']
                    
                    mask = (df_novo['Task Code'] == t_code) & (df_novo['Activity Name'] == a_name) & (df_novo['Resource Name'] == rec) & (df_novo['Mes'] == mes)
                    
                    if mask.any():
                        indices = df_novo[mask].index
                        df_novo.loc[indices[0], 'Horas_Alocadas'] = nova_hora
                        if len(indices) > 1:
                            df_novo.loc[indices[1:], 'Horas_Alocadas'] = 0
                    else:
                        if nova_hora > 0:
                            mask_base = (df_novo['Task Code'] == t_code) & (df_novo['Activity Name'] == a_name) & (df_novo['Resource Name'] == rec)
                            if mask_base.any():
                                info_base = df_novo[mask_base].iloc[0].copy()
                                info_base['Mes'] = mes
                                info_base['Horas_Alocadas'] = nova_hora
                                if 'Line identifier' in info_base:
                                    info_base['Line identifier'] = f"MAT-{np.random.randint(1000,9999)}"
                                df_novo = pd.concat([df_novo, pd.DataFrame([info_base])], ignore_index=True)
                
                # 4. RECALCULAR DATAS DE INÍCIO E FIM
                tarefas_alteradas = df_changed[['Task Code', 'Activity Name', 'Resource Name']].drop_duplicates()
                
                for _, row in tarefas_alteradas.iterrows():
                    t_code = row['Task Code']
                    a_name = row['Activity Name']
                    rec = row['Resource Name']
                    
                    mask_tarefa = (df_novo['Task Code'] == t_code) & (df_novo['Activity Name'] == a_name) & (df_novo['Resource Name'] == rec) & (df_novo['Horas_Alocadas'] > 0)
                    
                    if mask_tarefa.any():
                        meses_ativos = df_novo[mask_tarefa]['Mes'].tolist()
                        meses_dt = [pd.to_datetime(m, format='%m/%Y') for m in meses_ativos]
                        
                        novo_inicio = min(meses_dt).date()
                        novo_fim = (max(meses_dt) + pd.offsets.MonthEnd(0)).date()
                        
                        mask_update = (df_novo['Task Code'] == t_code) & (df_novo['Activity Name'] == a_name) & (df_novo['Resource Name'] == rec)
                        df_novo.loc[mask_update, 'Planned start'] = novo_inicio
                        df_novo.loc[mask_update, 'Planned finish'] = novo_fim
                
                st.session_state['df_simulado'] = df_novo
                
                # Limpa cache de UI focado apenas nos editores
                prefixos = ['mat_', 'editor_', 'visao_', 'busca_', 'sel_', 'task_', 'proj_']
                for key in list(st.session_state.keys()):
                    if any(key.startswith(p) for p in prefixos):
                        del st.session_state[key]
                
                keys_to_keep = ['df_simulado', 'df_original', 'df_capacidade', 'ignored_conflicts', 'df_geral', 'df_original_geral', 'df_cap_geral', 'df_baseline_geral', 'logado', 'seletor_modo_global']
                for key in list(st.session_state.keys()):
                    if key not in keys_to_keep and not key.startswith('FormSubmitter'):
                        del st.session_state[key]
                        
                st.success("✅ Alterações salvas e datas recalculadas com sucesso!")
                st.rerun()
```

#### Arquivo 5: `comparator_geral.py` (Lógica de Baseline)
```python
iimport streamlit as st
import pandas as pd
import plotly.express as px

def render_comparator_geral(df_base, df_atual):
    st.subheader("⚖️ Comparativo: Baseline vs. Mês Atual")
    st.write("Analise a evolução do Workload em relação ao mês anterior. Valores positivos indicam aumento de horas, valores negativos indicam redução.")

    # 1. KPIs Principais
    total_base = df_base['Horas_Alocadas'].sum()
    total_atual = df_atual['Horas_Alocadas'].sum()
    delta_total = total_atual - total_base

    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Horas (Baseline)", f"{total_base:,.1f}h")
    col2.metric("Total de Horas (Atual)", f"{total_atual:,.1f}h")
    col3.metric("Variação Global (Delta)", f"{delta_total:+,.1f}h", delta=round(delta_total, 1))

    st.write("---")

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

    st.write("---")
    st.write("### 🔍 Entradas e Saídas (Alocações)")

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
```

#### Arquivo 6: `editor.py` (Simulador de Cenários - OdyC)

*   **Função:** É o motor de edição do modo OdyC. Ele constrói a interface com as 4 abas de simulação: "Editar Existente", "Criar Nova Tarefa", "Visão por Recurso/Mês" e "Dividir Horas por Mês".
*   **Destaque Técnico:** Contém a inteligência matemática para calcular automaticamente a Data Fim de uma tarefa baseada em dias úteis (considerando a constante de **9,18h por dia útil**), além de gerenciar o fatiamento manual de horas ao longo dos meses.

```python
import streamlit as st
import pandas as pd
import numpy as np
import math

def clear_ui_state():
    # Limpa apenas os estados dos filtros internos e editores
    prefixos = ['mat_', 'editor_', 'visao_', 'busca_', 'sel_', 'task_', 'proj_']
    for key in list(st.session_state.keys()):
        if any(key.startswith(p) for p in prefixos):
            del st.session_state[key]

def render_editor_geral():
    st.subheader("✏️ Simulador de Cenários (Geral)")
    df_geral = st.session_state['df_geral']
    
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
                df_visao_show = df_visao_show.sort_values('Horas_Alocadas', ascending=False)
                
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
                        
                        for idx, row in df_editado_visao.iterrows():
                            p_name = row['Project Name']
                            a_name = row['Activity Name']
                            novo_rec = row['Resource Name']
                            novo_inicio = row['Planned start']
                            novo_fim = row['Planned finish']
                            novas_horas = row['Horas_Alocadas']
                            novo_rtc = row['RTC_ID']
                            
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
                        st.success("✅ Alterações salvas com sucesso!")
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
                        st.success("✅ Distribuição salva com sucesso!")
                        clear_ui_state()
                        st.rerun()
```
#### Arquivo 7: `editor_geral.py` (Simulador de Cenários - Workload Geral)
*   **Função:** É o equivalente exato do `editor.py`, porém totalmente adaptado para a estrutura de colunas do Workload Geral.
*   **Destaque Técnico:** Ao invés de cruzar dados por `Task Code` e `Line identifier` (como no OdyC), ele utiliza a chave combinada de `Project Name`, `Activity Name` e `CostCenter Name` para garantir que as edições e cálculos de dias úteis sejam aplicados na linha correta.
```python
import streamlit as st
import pandas as pd
import numpy as np
import math

def clear_ui_state():
    # Limpa apenas os estados dos filtros internos e editores
    prefixos = ['mat_', 'editor_', 'visao_', 'busca_', 'sel_', 'task_', 'proj_']
    for key in list(st.session_state.keys()):
        if any(key.startswith(p) for p in prefixos):
            del st.session_state[key]

def render_editor_geral():
    st.subheader("✏️ Simulador de Cenários (Geral)")
    df_geral = st.session_state['df_geral']
    
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
                df_visao_show = df_visao_show.sort_values('Horas_Alocadas', ascending=False)
                
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
                        
                        for idx, row in df_editado_visao.iterrows():
                            p_name = row['Project Name']
                            a_name = row['Activity Name']
                            novo_rec = row['Resource Name']
                            novo_inicio = row['Planned start']
                            novo_fim = row['Planned finish']
                            novas_horas = row['Horas_Alocadas']
                            novo_rtc = row['RTC_ID']
                            
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
                        st.success("✅ Alterações salvas com sucesso!")
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
                        st.success("✅ Distribuição salva com sucesso!")
                        clear_ui_state()
                        st.rerun()
```

### Arquivo 8: `editor_matricial_geral.py` (Matriz Editável - Workload Geral)
*   **Função:** É o arquivo "irmão" do `editor_matricial.py` (que mostrei no resumo anterior), feito para o modo Geral.
*   **Destaque Técnico:** Gera a tabela dinâmica (Pivot Table) interativa. Ele filtra a partir da data de início da tarefa mais antiga e projeta colunas até **4 meses após** a data mais distante. Possui a lógica de engenharia reversa que detecta o que foi digitado na tabela, atualiza o banco de dados e recalcula automaticamente o `Planned start` e `Planned finish`.
```python
import streamlit as st
import pandas as pd
import numpy as np

def render_editor_matricial_geral():
    st.subheader("📁 Visão e Edição Matricial por Projeto")
    st.write("Edite as horas diretamente. A tabela exibe a partir do mês inicial até **4 meses depois** da última entrega. Use os filtros de data para focar em um período específico.")
    
    df_geral = st.session_state['df_geral']
    
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
                for _, row in df_changed.iterrows():
                    p_name = row['Project Name']
                    a_name = row['Activity Name']
                    rec = row['Resource Name']
                    mes = row['Mes']
                    nova_hora = row['Horas_Alocadas_novo']
                    
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
                
                keys_to_keep = ['df_simulado', 'df_original', 'df_capacidade', 'ignored_conflicts', 'df_geral', 'df_original_geral', 'df_cap_geral', 'df_baseline_geral', 'logado', 'seletor_modo_global']
                for key in list(st.session_state.keys()):
                    if key not in keys_to_keep and not key.startswith('FormSubmitter'):
                        del st.session_state[key]
                        
                st.success("✅ Alterações salvas e datas recalculadas com sucesso!")
                st.rerun()
```

### Arquivo 9: `data_processing.py` (ETL e Tratamento de Dados - OdyC)
*   **Função:** É o motor de extração e limpeza (ETL) do OdyC. Responsável por ler os dois arquivos Excel pesados (`.xlsx` ou `.xlsm`).
*   **Destaque Técnico:** Faz o "merge" (cruzamento) entre a aba de Workload e a aba de Schedule, limpa dados nulos, formata as datas de Início/Fim e gera a tabela de Capacidade dos recursos. É ele que cria o `df_original` (intocável) e o `df_simulado` (que vai para a memória).
```python
import pandas as pd
import numpy as np

def load_and_process_data(arquivo_wkl, arquivo_schedule):
    df_wkl = pd.read_excel(arquivo_wkl, sheet_name="DB_WKL")
    df_capacity_raw = pd.read_excel(arquivo_wkl, sheet_name="ByResource", header=None, nrows=2)
    df_planning = pd.read_excel(arquivo_wkl, sheet_name="Planning")
    df_schedule = pd.read_excel(arquivo_schedule, sheet_name="View 01")
    
    meses = df_capacity_raw.iloc[0, 4:].values
    horas = df_capacity_raw.iloc[1, 4:].values
    df_capacidade = pd.DataFrame({'Mes': meses, 'Horas_Uteis': horas}).dropna()
    df_capacidade['Mes'] = pd.to_datetime(df_capacidade['Mes']).dt.strftime('%m/%Y')
    
    df_wkl.columns = df_wkl.columns.astype(str)
    
    colunas_fixas = ['Task Code', 'Activity Name', 'Resource Name', 'Resource Category']
    if 'Start' in df_wkl.columns: colunas_fixas.append('Start')
    if 'Finish' in df_wkl.columns: colunas_fixas.append('Finish')
        
    colunas_meses = [col for col in df_wkl.columns if '202' in col or '203' in col]
    
    df_alocacao = pd.melt(df_wkl, id_vars=colunas_fixas, value_vars=colunas_meses, var_name='Mes', value_name='Horas_Alocadas')
    
    df_alocacao['Horas_Alocadas'] = df_alocacao['Horas_Alocadas'].astype(str).str.replace(',', '.')
    df_alocacao['Horas_Alocadas'] = pd.to_numeric(df_alocacao['Horas_Alocadas'], errors='coerce').fillna(0)
    df_alocacao = df_alocacao[df_alocacao['Horas_Alocadas'] > 0]
    df_alocacao['Mes'] = pd.to_datetime(df_alocacao['Mes']).dt.strftime('%m/%Y')
    
    df_alocacao['Task Code'] = df_alocacao['Task Code'].astype(str).str.strip().str.upper()
    df_alocacao['Activity Name'] = df_alocacao['Activity Name'].astype(str).str.strip().str.upper()
    df_planning['OdyC Task Code Name Task'] = df_planning['OdyC Task Code Name Task'].astype(str).str.strip().str.upper()
    df_planning['Description Activity'] = df_planning['Description Activity'].astype(str).str.strip().str.upper()
    df_planning['Line identifier Task'] = df_planning['Line identifier Task'].astype(str).str.replace('.0', '', regex=False).str.strip()
    df_schedule['Line identifier'] = df_schedule['Line identifier'].astype(str).str.replace('.0', '', regex=False).str.strip()
    
    df_ponte = df_planning[['OdyC Task Code Name Task', 'Description Activity', 'Line identifier Task']].drop_duplicates()
    df_master_step1 = pd.merge(df_alocacao, df_ponte, left_on=['Task Code', 'Activity Name'], right_on=['OdyC Task Code Name Task', 'Description Activity'], how='left')
    
    colunas_do_schedule = ['Line identifier', 'Planned start', 'Planned finish', 'Predecessor', 'Successor']
    df_master = pd.merge(df_master_step1, df_schedule[colunas_do_schedule], left_on='Line identifier Task', right_on='Line identifier', how='left')
    
    colunas_para_remover = ['OdyC Task Code Name Task', 'Description Activity', 'Line identifier Task']
    df_master = df_master.drop(columns=[col for col in colunas_para_remover if col in df_master.columns])
    
    if 'Start' in df_master.columns and 'Finish' in df_master.columns:
        df_master['Planned start'] = df_master['Planned start'].fillna(df_master['Start'])
        df_master['Planned finish'] = df_master['Planned finish'].fillna(df_master['Finish'])
        df_master = df_master.drop(columns=['Start', 'Finish'])
        
    df_master['Planned start'] = pd.to_datetime(df_master['Planned start'], errors='coerce').dt.date
    df_master['Planned finish'] = pd.to_datetime(df_master['Planned finish'], errors='coerce').dt.date
    
    df_master['Line identifier'] = df_master['Line identifier'].fillna('N/A')
    
    # NOVIDADE: Coluna para rastreio no RTC
    df_master['RTC_ID'] = ""
    
    return df_master, df_capacidade
```

### Arquivo 10: `data_processing_geral.py` (ETL e Tratamento de Dados - Workload Geral)
*   **Função:** O motor de extração focado apenas na planilha única do Workload Geral.
*   **Destaque Técnico:** Lê a aba `DB_WKL` (ignorando as tabelas dinâmicas do Excel para evitar erros), formata a coluna de meses (MM/YYYY) e agrupa as horas alocadas por recurso e projeto, preparando a base `df_geral`.
```python
import pandas as pd
import numpy as np
from datetime import datetime

def load_and_process_geral(arquivo_geral):
    df_capacity_raw = pd.read_excel(arquivo_geral, sheet_name="Hours by Month", skiprows=3)
    
    col_class = df_capacity_raw.columns[0]
    df_capacity_raw = df_capacity_raw.rename(columns={col_class: 'ClassBR'})
    
    colunas_data_cap = [col for col in df_capacity_raw.columns if col != 'ClassBR' and not str(col).startswith('Unnamed')]
    
    df_capacidade = pd.melt(df_capacity_raw, id_vars=['ClassBR'], value_vars=colunas_data_cap, var_name='Mes_Raw', value_name='Horas_Uteis')
    
    def format_month(val):
        try:
            if isinstance(val, datetime):
                return val.strftime('%m/%Y')
            return pd.to_datetime(val).strftime('%m/%Y')
        except:
            return str(val)
            
    df_capacidade['Mes'] = df_capacidade['Mes_Raw'].apply(format_month)
    df_capacidade['Horas_Uteis'] = pd.to_numeric(df_capacidade['Horas_Uteis'], errors='coerce').fillna(180)
    df_capacidade = df_capacidade.drop(columns=['Mes_Raw'])

    df_db = pd.read_excel(arquivo_geral, sheet_name="DataBase-Hours")
    
    colunas_fixas = [
        'ClassBR', 'OBS code & desc', 'CT |BO ID |PG |OH', 'Project Name', 'Local ID', 
        'Schedule Name', 'Task Code', 'Activity Name', 'Start', 'Finish', 'Resource ID', 
        'Resource Name', 'SoA', 'Filters', 'CostCenter', 'CostCenter Name', 'DH', 
        'Resource Category', 'Free text1', 'Free text2'
    ]
    
    colunas_fixas_existentes = [col for col in colunas_fixas if col in df_db.columns]
    colunas_meses = [col for col in df_db.columns if col not in colunas_fixas_existentes and not str(col).startswith('Unnamed')]
    
    df_alocacao = pd.melt(df_db, id_vars=colunas_fixas_existentes, value_vars=colunas_meses, var_name='Mes_Raw', value_name='Horas_Alocadas')
    
    df_alocacao['Horas_Alocadas'] = df_alocacao['Horas_Alocadas'].astype(str).str.replace(',', '.')
    df_alocacao['Horas_Alocadas'] = pd.to_numeric(df_alocacao['Horas_Alocadas'], errors='coerce').fillna(0)
    df_alocacao = df_alocacao[df_alocacao['Horas_Alocadas'] > 0]
    
    df_alocacao['Planned start'] = pd.to_datetime(df_alocacao['Start'], errors='coerce').dt.date
    df_alocacao['Planned finish'] = pd.to_datetime(df_alocacao['Finish'], errors='coerce').dt.date
    df_alocacao['Mes'] = df_alocacao['Mes_Raw'].apply(format_month)
    
    df_alocacao['Project Name'] = df_alocacao['Project Name'].fillna('Sem Projeto').astype(str)
    df_alocacao['Activity Name'] = df_alocacao['Activity Name'].fillna('N/A').astype(str)
    df_alocacao['Resource Name'] = df_alocacao['Resource Name'].fillna('Não Atribuído').astype(str)
    df_alocacao['CostCenter Name'] = df_alocacao['CostCenter Name'].fillna('N/A').astype(str)
    
    df_alocacao['RTC_ID'] = ""
    
    return df_alocacao, df_capacidade
```

### Arquivo 11: `visualizations.py` (Gráficos e Dashboards - OdyC)
*   **Função:** Concentra toda a parte visual e de UI (User Interface) dos gráficos do modo OdyC, utilizando a biblioteca Plotly.
*   **Destaque Técnico:** Contém a lógica complexa do **Heatmap de Capacidade** (incluindo a regra de cores de negócio: <80% Amarelo, 80-119% Verde, >120% Vermelho), o Gráfico de Gantt interativo, os KPIs do Dashboard e a tabela de Changelog que compara o `df_original` com o `df_simulado`.
```python
import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import re

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
    st.subheader("⚠️ Resumo de Alterações e Alertas")
    st.write("Audite as mudanças, reverta cenários, ignore falsos positivos e exporte o relatório.")
    
    if 'ignored_conflicts' not in st.session_state:
        st.session_state['ignored_conflicts'] = []
        
    st.write("### 📝 O que mudou?")
    
    df_orig_grp = df_original.groupby(['Line identifier', 'Task Code', 'Activity Name']).agg({
        'Planned start': 'min', 
        'Planned finish': 'max', 
        'Horas_Alocadas': 'sum',
        'Resource Name': lambda x: ', '.join(sorted(set(x.dropna().astype(str))))
    }).reset_index()
    
    df_sim_grp = df_simulado.groupby(['Line identifier', 'Task Code', 'Activity Name']).agg({
        'Planned start': 'min', 
        'Planned finish': 'max', 
        'Horas_Alocadas': 'sum',
        'Resource Name': lambda x: ', '.join(sorted(set(x.dropna().astype(str))))
    }).reset_index()
    
    df_compare = pd.merge(df_orig_grp, df_sim_grp, on=['Line identifier', 'Task Code', 'Activity Name'], 
                          how='outer', suffixes=('_Orig', '_Sim'))
    
    df_compare['Planned start_Orig'] = pd.to_datetime(df_compare['Planned start_Orig']).dt.date
    df_compare['Planned finish_Orig'] = pd.to_datetime(df_compare['Planned finish_Orig']).dt.date
    df_compare['Planned start_Sim'] = pd.to_datetime(df_compare['Planned start_Sim']).dt.date
    df_compare['Planned finish_Sim'] = pd.to_datetime(df_compare['Planned finish_Sim']).dt.date
    
    df_compare['Resource Name_Orig'] = df_compare['Resource Name_Orig'].fillna('N/A')
    df_compare['Resource Name_Sim'] = df_compare['Resource Name_Sim'].fillna('N/A')
    df_compare['Horas_Alocadas_Orig'] = df_compare['Horas_Alocadas_Orig'].fillna(0)
    df_compare['Horas_Alocadas_Sim'] = df_compare['Horas_Alocadas_Sim'].fillna(0)

    mudancas = df_compare[
        (df_compare['Planned start_Orig'] != df_compare['Planned start_Sim']) |
        (df_compare['Planned finish_Orig'] != df_compare['Planned finish_Sim']) |
        (round(df_compare['Horas_Alocadas_Orig'], 1) != round(df_compare['Horas_Alocadas_Sim'], 1)) |
        (df_compare['Resource Name_Orig'] != df_compare['Resource Name_Sim'])
    ].copy()
    
    if mudancas.empty:
        st.success("Nenhuma alteração detectada em relação ao original.")
    else:
        mudancas['Início (De -> Para)'] = mudancas['Planned start_Orig'].fillna('N/A').astype(str) + " ➡️ " + mudancas['Planned start_Sim'].fillna('N/A').astype(str)
        mudancas['Fim (De -> Para)'] = mudancas['Planned finish_Orig'].fillna('N/A').astype(str) + " ➡️ " + mudancas['Planned finish_Sim'].fillna('N/A').astype(str)
        mudancas['Horas (De -> Para)'] = mudancas['Horas_Alocadas_Orig'].round(1).astype(str) + "h ➡️ " + mudancas['Horas_Alocadas_Sim'].round(1).astype(str) + "h"
        mudancas['Recursos (De -> Para)'] = mudancas['Resource Name_Orig'].astype(str) + " ➡️ " + mudancas['Resource Name_Sim'].astype(str)
        
        df_display = mudancas[['Line identifier', 'Task Code', 'Activity Name', 'Recursos (De -> Para)', 'Início (De -> Para)', 'Fim (De -> Para)', 'Horas (De -> Para)']].copy()
        
        df_display.insert(0, 'Reverter', False)
        
        st.write("Selecione as tarefas que deseja desfazer e clique no botão abaixo.")
        
        edited_mudancas = st.data_editor(
            df_display, hide_index=True, use_container_width=True,
            column_config={"Reverter": st.column_config.CheckboxColumn("Desfazer?", default=False)}
        )
        
        col_btn1, col_btn2 = st.columns([2, 2])
        with col_btn1:
            if st.button("🔄 Reverter Tarefas Selecionadas"):
                revert_mask = edited_mudancas['Reverter'] == True
                if revert_mask.any():
                    tasks_to_revert = edited_mudancas[revert_mask]
                    df_novo = st.session_state['df_simulado'].copy()
                    
                    for _, row in tasks_to_revert.iterrows():
                        l_id = row['Line identifier']
                        t_code = row['Task Code']
                        a_name = row['Activity Name']
                        
                        mask_sim = (df_novo['Line identifier'] == l_id) & (df_novo['Task Code'] == t_code) & (df_novo['Activity Name'] == a_name)
                        df_novo = df_novo[~mask_sim]
                        
                        mask_orig = (df_original['Line identifier'] == l_id) & (df_original['Task Code'] == t_code) & (df_original['Activity Name'] == a_name)
                        df_to_restore = df_original[mask_orig]
                        
                        if not df_to_restore.empty:
                            df_novo = pd.concat([df_novo, df_to_restore], ignore_index=True)
                            
                    st.session_state['df_simulado'] = df_novo
                    st.success("Alterações revertidas com sucesso!")
                    st.rerun()
                    
        with col_btn2:
            csv = df_display.drop(columns=['Reverter']).to_csv(index=False, sep=';', encoding='utf-8-sig')
            st.download_button(label="📥 Exportar Relatório (CSV)", data=csv, file_name="relatorio_alteracoes.csv", mime="text/csv")
            
    st.write("---")
    st.write("### 🚨 Alertas de Conflito (Predecessoras)")
    
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
```

### Arquivo 12: `visualizations_geral.py` (Gráficos e Dashboards - Workload Geral)
*   **Função:** Réplica do módulo de visualizações, mas consumindo os dados do `df_geral`.
*   **Destaque Técnico:** Adapta os eixos dos gráficos (como o Gantt e os agrupamentos do Dashboard) para focar em `Project Name` ao invés das nomenclaturas específicas do OdyC, mantendo a mesma identidade visual e regras de cores de capacidade.
```python
import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

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
        # CORREÇÃO: Adicionado key="dash_proj_filter"
        projetos_selecionados = st.multiselect("📁 Filtrar por Projeto(s):", options=projetos_disponiveis, default=[], key="dash_proj_filter")
    with col_f2:
        cc_disponiveis = sorted(df_valid['CostCenter Name'].unique())
        # CORREÇÃO: Adicionado key="dash_cc_filter"
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
            # CORREÇÃO: Adicionado key="heat_rec_filter_geral"
            recursos_selecionados = st.multiselect("👥 Selecione os Recursos:", options=recursos_disponiveis, default=[], key="heat_rec_filter_geral")
        with col2:
            # CORREÇÃO: Adicionado key="heat_date_filter_geral"
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
    st.subheader("⚠️ Resumo de Alterações (Workload Geral)")
    st.write("Audite as mudanças, reverta cenários e exporte o relatório.")
    
    projetos_disp = sorted(df_simulado['Project Name'].dropna().unique())
    projetos_filtro = st.multiselect("📁 Filtrar por Projeto(s):", options=projetos_disp, default=[], key="change_proj_filter_geral")
    
    df_orig_view = df_original.copy()
    df_sim_view = df_simulado.copy()
    
    if projetos_filtro:
        df_orig_view = df_orig_view[df_orig_view['Project Name'].isin(projetos_filtro)]
        df_sim_view = df_sim_view[df_sim_view['Project Name'].isin(projetos_filtro)]
        
    df_orig_view['Planned start'] = pd.to_datetime(df_orig_view['Planned start'], errors='coerce')
    df_orig_view['Planned finish'] = pd.to_datetime(df_orig_view['Planned finish'], errors='coerce')
    df_sim_view['Planned start'] = pd.to_datetime(df_sim_view['Planned start'], errors='coerce')
    df_sim_view['Planned finish'] = pd.to_datetime(df_sim_view['Planned finish'], errors='coerce')
        
    # NOVIDADE: Agrupando também por 'Mes' para ter a visão granular
    df_orig_grp = df_orig_view.groupby(['Project Name', 'Activity Name', 'Mes']).agg({
        'Planned start': 'min', 
        'Planned finish': 'max', 
        'Horas_Alocadas': 'sum',
        'Resource Name': lambda x: ', '.join(sorted(set(x.dropna().astype(str))))
    }).reset_index()
    
    df_sim_grp = df_sim_view.groupby(['Project Name', 'Activity Name', 'Mes']).agg({
        'Planned start': 'min', 
        'Planned finish': 'max', 
        'Horas_Alocadas': 'sum',
        'Resource Name': lambda x: ', '.join(sorted(set(x.dropna().astype(str))))
    }).reset_index()
    
    # O merge agora cruza Projeto, Atividade E Mês
    df_compare = pd.merge(df_orig_grp, df_sim_grp, on=['Project Name', 'Activity Name', 'Mes'], 
                          how='outer', suffixes=('_Orig', '_Sim'))
    
    df_compare['Planned start_Orig_str'] = pd.to_datetime(df_compare['Planned start_Orig']).dt.date.fillna('N/A').astype(str)
    df_compare['Planned finish_Orig_str'] = pd.to_datetime(df_compare['Planned finish_Orig']).dt.date.fillna('N/A').astype(str)
    df_compare['Planned start_Sim_str'] = pd.to_datetime(df_compare['Planned start_Sim']).dt.date.fillna('N/A').astype(str)
    df_compare['Planned finish_Sim_str'] = pd.to_datetime(df_compare['Planned finish_Sim']).dt.date.fillna('N/A').astype(str)
    
    df_compare['Resource Name_Orig'] = df_compare['Resource Name_Orig'].fillna('N/A')
    df_compare['Resource Name_Sim'] = df_compare['Resource Name_Sim'].fillna('N/A')
    df_compare['Horas_Alocadas_Orig'] = df_compare['Horas_Alocadas_Orig'].fillna(0)
    df_compare['Horas_Alocadas_Sim'] = df_compare['Horas_Alocadas_Sim'].fillna(0)

    mudancas = df_compare[
        (df_compare['Planned start_Orig_str'] != df_compare['Planned start_Sim_str']) |
        (df_compare['Planned finish_Orig_str'] != df_compare['Planned finish_Sim_str']) |
        (round(df_compare['Horas_Alocadas_Orig'], 1) != round(df_compare['Horas_Alocadas_Sim'], 1)) |
        (df_compare['Resource Name_Orig'] != df_compare['Resource Name_Sim'])
    ].copy()
    
    if mudancas.empty:
        st.success("Nenhuma alteração detectada em relação ao original.")
    else:
        mudancas['Início (De -> Para)'] = mudancas['Planned start_Orig_str'] + " ➡️ " + mudancas['Planned start_Sim_str']
        mudancas['Fim (De -> Para)'] = mudancas['Planned finish_Orig_str'] + " ➡️ " + mudancas['Planned finish_Sim_str']
        mudancas['Horas (De -> Para)'] = mudancas['Horas_Alocadas_Orig'].round(1).astype(str) + "h ➡️ " + mudancas['Horas_Alocadas_Sim'].round(1).astype(str) + "h"
        mudancas['Recursos (De -> Para)'] = mudancas['Resource Name_Orig'].astype(str) + " ➡️ " + mudancas['Resource Name_Sim'].astype(str)
        
        # Adicionamos a coluna 'Mes' na exibição final
        df_display = mudancas[['Project Name', 'Activity Name', 'Mes', 'Recursos (De -> Para)', 'Início (De -> Para)', 'Fim (De -> Para)', 'Horas (De -> Para)']].copy()
        
        df_display.insert(0, 'Reverter', False)
        
        st.write("Selecione as tarefas que deseja desfazer e clique no botão abaixo.")
        
        edited_mudancas = st.data_editor(
            df_display, hide_index=True, use_container_width=True,
            column_config={"Reverter": st.column_config.CheckboxColumn("Desfazer?", default=False)},
            key="editor_changelog_geral"
        )
        
        col_btn1, col_btn2 = st.columns([2, 2])
        with col_btn1:
            if st.button("🔄 Reverter Tarefas Selecionadas", key="btn_revert_geral"):
                revert_mask = edited_mudancas['Reverter'] == True
                if revert_mask.any():
                    tasks_to_revert = edited_mudancas[revert_mask]
                    df_novo = st.session_state['df_geral'].copy()
                    
                    for _, row in tasks_to_revert.iterrows():
                        p_name = row['Project Name']
                        a_name = row['Activity Name']
                        mes_reverter = row['Mes'] # Pega o mês específico
                        
                        # Remove apenas o mês específico do simulado
                        mask_sim = (df_novo['Project Name'] == p_name) & (df_novo['Activity Name'] == a_name) & (df_novo['Mes'] == mes_reverter)
                        df_novo = df_novo[~mask_sim]
                        
                        # Restaura apenas o mês específico do original
                        mask_orig = (df_original['Project Name'] == p_name) & (df_original['Activity Name'] == a_name) & (df_original['Mes'] == mes_reverter)
                        df_to_restore = df_original[mask_orig]
                        
                        if not df_to_restore.empty:
                            df_novo = pd.concat([df_novo, df_to_restore], ignore_index=True)
                            
                    st.session_state['df_geral'] = df_novo
                    st.success("Alterações revertidas com sucesso!")
                    st.rerun()
                    
        with col_btn2:
            csv = df_display.drop(columns=['Reverter']).to_csv(index=False, sep=';', encoding='utf-8-sig')
            st.download_button(label="📥 Exportar Relatório (CSV)", data=csv, file_name="relatorio_alteracoes_geral.csv", mime="text/csv", key="btn_export_geral")
```
