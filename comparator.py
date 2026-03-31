import streamlit as st
import pandas as pd
from database import SessionLocal, Scenario, TaskOdyc, TaskGeral


# ---------------------------------------------------------------------------
# Funções de acesso ao banco de dados
# ---------------------------------------------------------------------------

def get_scenarios(modo):
    """Busca todos os cenários salvos no banco de dados para o modo atual."""
    db = SessionLocal()
    try:
        scenarios = (
            db.query(Scenario)
            .filter(Scenario.mode == modo)
            .order_by(Scenario.created_at.desc())
            .all()
        )
        return {
            f"ID {s.id} | {s.name} ({s.created_at.strftime('%d/%m/%Y %H:%M')}) — por {s.author}": s.id
            for s in scenarios
        }
    finally:
        db.close()


def get_tasks_df(scenario_id, modo):
    """Busca as tarefas de um cenário e retorna como DataFrame."""
    db = SessionLocal()
    try:
        if modo == "OdyC":
            tasks = db.query(TaskOdyc).filter(TaskOdyc.scenario_id == scenario_id).all()
            data = [
                {
                    "Line identifier": t.line_identifier,
                    "Task Code": t.task_code,
                    "Resource Name": t.resource_name,
                    "Planned start": t.planned_start,
                    "Planned finish": t.planned_finish,
                    "Horas_Alocadas": t.workload_hours,
                }
                for t in tasks
            ]
        else:
            tasks = db.query(TaskGeral).filter(TaskGeral.scenario_id == scenario_id).all()
            data = [
                {
                    "Project Name": t.project_name,
                    "Activity Name": t.activity_name,
                    "Resource Name": t.resource_name,
                    "Planned start": t.planned_start,
                    "Planned finish": t.planned_finish,
                    "Horas_Alocadas": t.workload_hours,
                }
                for t in tasks
            ]
        return pd.DataFrame(data)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Funções puras de filtragem (testáveis sem Streamlit)
# ---------------------------------------------------------------------------

def get_filter_options(df_a: pd.DataFrame, df_b: pd.DataFrame, modo: str):
    """
    Retorna as opções de filtro como a união dos valores únicos de A e B.

    Returns:
        recursos_opts: lista ordenada de recursos únicos (A ∪ B)
        proj_opts: lista ordenada de identificadores de projeto/tarefa únicos (A ∪ B)
    """
    recursos_a = set(df_a["Resource Name"].dropna().astype(str))
    recursos_b = set(df_b["Resource Name"].dropna().astype(str))
    recursos_opts = sorted(recursos_a | recursos_b)

    proj_col = "Task Code" if modo == "OdyC" else "Project Name"
    proj_a = set(df_a[proj_col].dropna().astype(str)) if proj_col in df_a.columns else set()
    proj_b = set(df_b[proj_col].dropna().astype(str)) if proj_col in df_b.columns else set()
    proj_opts = sorted(proj_a | proj_b)

    return recursos_opts, proj_opts


def apply_comparator_filters(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    modo: str,
    filtro_recursos: list,
    filtro_proj: list,
):
    """
    Aplica filtros de recurso e identificador de projeto nos DataFrames.
    Lista vazia significa sem filtro (retorna todos os dados).

    Returns:
        (df_a_filtrado, df_b_filtrado)
    """
    df_a_f = df_a.copy()
    df_b_f = df_b.copy()

    if filtro_recursos:
        df_a_f = df_a_f[df_a_f["Resource Name"].isin(filtro_recursos)]
        df_b_f = df_b_f[df_b_f["Resource Name"].isin(filtro_recursos)]

    if filtro_proj:
        proj_col = "Task Code" if modo == "OdyC" else "Project Name"
        if proj_col in df_a_f.columns:
            df_a_f = df_a_f[df_a_f[proj_col].isin(filtro_proj)]
        if proj_col in df_b_f.columns:
            df_b_f = df_b_f[df_b_f[proj_col].isin(filtro_proj)]

    return df_a_f, df_b_f


# ---------------------------------------------------------------------------
# Renderização principal
# ---------------------------------------------------------------------------

def render_comparator(modo):
    st.subheader(f"⚖️ Comparador de Versões — {modo}")
    st.caption(
        "Selecione duas versões salvas no banco para comparar diferenças de alocação, "
        "datas e recursos. Use os filtros para focar em um subconjunto."
    )

    scenarios_dict = get_scenarios(modo)

    if len(scenarios_dict) < 2:
        st.warning("⚠️ Você precisa ter pelo menos **2 versões salvas** para usar o comparador.")
        st.info(
            "💡 **Dica:** No menu lateral, clique em **💾 Salvar Nova Versão no Banco** "
            "para criar um ponto de comparação."
        )
        return

    ss_key = f"comp_data_{modo}"

    col1, col2 = st.columns(2)
    with col1:
        cenario_a_nome = st.selectbox(
            "📌 Versão Base (Antiga):",
            list(scenarios_dict.keys()),
            index=len(scenarios_dict) - 1,
            help="Versão de referência. As diferenças são calculadas em relação a ela.",
        )
    with col2:
        cenario_b_nome = st.selectbox(
            "🎯 Versão Comparada (Nova):",
            list(scenarios_dict.keys()),
            index=0,
            help="Versão que você quer comparar contra a base.",
        )

    if st.button("🚀 Comparar Versões", use_container_width=True, type="primary"):
        id_a = scenarios_dict[cenario_a_nome]
        id_b = scenarios_dict[cenario_b_nome]

        if id_a == id_b:
            st.warning("Selecione versões **diferentes** para comparar.")
            st.session_state.pop(ss_key, None)
            return

        with st.spinner("Buscando dados e calculando diferenças..."):
            df_a = get_tasks_df(id_a, modo)
            df_b = get_tasks_df(id_b, modo)

            if df_a.empty or df_b.empty:
                st.error("Uma das versões não possui dados válidos para comparação.")
                st.session_state.pop(ss_key, None)
                return

            st.session_state[ss_key] = {"df_a": df_a, "df_b": df_b}

    if ss_key not in st.session_state:
        return

    df_a = st.session_state[ss_key]["df_a"]
    df_b = st.session_state[ss_key]["df_b"]

    # --- FILTROS ---
    st.divider()
    recursos_opts, proj_opts = get_filter_options(df_a, df_b, modo)
    proj_label = "Task Code" if modo == "OdyC" else "Projeto"

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_recursos = st.multiselect(
            "👤 Filtrar por Recurso:",
            options=recursos_opts,
            default=[],
            help="Restringe a comparação aos recursos selecionados. Vazio = todos.",
        )
    with col_f2:
        filtro_proj = st.multiselect(
            f"📁 Filtrar por {proj_label}:",
            options=proj_opts,
            default=[],
            help=f"Restringe a comparação aos {proj_label.lower()}s selecionados. Vazio = todos.",
        )

    df_a_f, df_b_f = apply_comparator_filters(df_a, df_b, modo, filtro_recursos, filtro_proj)

    # --- MÉTRICAS DE RESUMO ---
    st.divider()
    variacao_total = df_b_f["Horas_Alocadas"].sum() - df_a_f["Horas_Alocadas"].sum()
    col_r1, col_r2, col_r3 = st.columns(3)
    col_r1.metric("Horas — Versão Base", f"{df_a_f['Horas_Alocadas'].sum():,.1f}h")
    col_r2.metric("Horas — Versão Nova", f"{df_b_f['Horas_Alocadas'].sum():,.1f}h")
    col_r3.metric(
        "Variação Total",
        f"{variacao_total:+,.1f}h",
        delta=float(variacao_total),
        delta_color="inverse",
    )

    # --- CÁLCULO DAS DIFERENÇAS ---
    st.divider()

    if modo == "OdyC":
        merge_cols = ["Line identifier", "Task Code"]
        agg_keys = merge_cols
    else:
        merge_cols = ["Project Name", "Activity Name"]
        agg_keys = merge_cols

    def _agrupar(df):
        return (
            df.groupby(agg_keys)
            .agg(
                {
                    "Planned start": "min",
                    "Planned finish": "max",
                    "Horas_Alocadas": "sum",
                    "Resource Name": lambda x: ", ".join(sorted(set(x.dropna().astype(str)))),
                }
            )
            .reset_index()
        )

    df_a_grp = _agrupar(df_a_f)
    df_b_grp = _agrupar(df_b_f)

    df_compare = pd.merge(df_a_grp, df_b_grp, on=merge_cols, how="outer", suffixes=("_Base", "_Nova"))

    df_compare["Planned start_Base_str"] = pd.to_datetime(df_compare["Planned start_Base"]).dt.date.astype(str).replace("NaT", "N/A")
    df_compare["Planned finish_Base_str"] = pd.to_datetime(df_compare["Planned finish_Base"]).dt.date.astype(str).replace("NaT", "N/A")
    df_compare["Planned start_Nova_str"] = pd.to_datetime(df_compare["Planned start_Nova"]).dt.date.astype(str).replace("NaT", "N/A")
    df_compare["Planned finish_Nova_str"] = pd.to_datetime(df_compare["Planned finish_Nova"]).dt.date.astype(str).replace("NaT", "N/A")

    df_compare["Resource Name_Base"] = df_compare["Resource Name_Base"].fillna("N/A")
    df_compare["Resource Name_Nova"] = df_compare["Resource Name_Nova"].fillna("N/A")
    df_compare["Horas_Alocadas_Base"] = df_compare["Horas_Alocadas_Base"].fillna(0)
    df_compare["Horas_Alocadas_Nova"] = df_compare["Horas_Alocadas_Nova"].fillna(0)

    mudancas = df_compare[
        (df_compare["Planned start_Base_str"] != df_compare["Planned start_Nova_str"])
        | (df_compare["Planned finish_Base_str"] != df_compare["Planned finish_Nova_str"])
        | (round(df_compare["Horas_Alocadas_Base"], 1) != round(df_compare["Horas_Alocadas_Nova"], 1))
        | (df_compare["Resource Name_Base"] != df_compare["Resource Name_Nova"])
    ].copy()

    if mudancas.empty:
        st.success("✅ As duas versões são idênticas para os filtros aplicados. Nenhuma alteração encontrada.")
        return

    st.warning(f"⚠️ **{len(mudancas)}** tarefa(s)/atividade(s) com diferenças encontradas.")

    mudancas["Início (Base → Nova)"] = mudancas["Planned start_Base_str"] + " → " + mudancas["Planned start_Nova_str"]
    mudancas["Fim (Base → Nova)"] = mudancas["Planned finish_Base_str"] + " → " + mudancas["Planned finish_Nova_str"]
    mudancas["Horas (Base → Nova)"] = (
        mudancas["Horas_Alocadas_Base"].round(1).astype(str) + "h → " + mudancas["Horas_Alocadas_Nova"].round(1).astype(str) + "h"
    )
    mudancas["Recursos (Base → Nova)"] = mudancas["Resource Name_Base"].astype(str) + " → " + mudancas["Resource Name_Nova"].astype(str)
    mudancas["Δ Horas"] = mudancas["Horas_Alocadas_Nova"] - mudancas["Horas_Alocadas_Base"]

    cols_display = merge_cols + ["Recursos (Base → Nova)", "Início (Base → Nova)", "Fim (Base → Nova)", "Horas (Base → Nova)", "Δ Horas"]
    df_display = mudancas[cols_display].copy()

    def _color_variation(val):
        if val > 0:
            return "color: #e74c3c; font-weight: bold"
        elif val < 0:
            return "color: #2ecc71; font-weight: bold"
        return ""

    st.dataframe(
        df_display.style.map(_color_variation, subset=["Δ Horas"]).format({"Δ Horas": "{:+.1f}h"}),
        use_container_width=True,
        hide_index=True,
    )

    csv = df_display.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button(
        label="📥 Exportar Comparativo (CSV)",
        data=csv,
        file_name=f"comparativo_versoes_{modo}.csv",
        mime="text/csv",
    )
