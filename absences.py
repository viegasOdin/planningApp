import streamlit as st
import pandas as pd
from database import SessionLocal, ResourceAbsence
from utils import registrar_log
from datetime import timedelta

def get_absences():
    """Busca todas as ausências cadastradas no banco."""
    db = SessionLocal()
    try:
        absences = db.query(ResourceAbsence).order_by(ResourceAbsence.start_date).all()
        data = [{
            'ID': a.id,
            'Recurso': a.resource_name,
            'Início': a.start_date,
            'Fim': a.end_date,
            'Motivo': a.reason,
            'Cadastrado por': a.registered_by
        } for a in absences]
        return pd.DataFrame(data)
    finally:
        db.close()

def render_absences_manager(df_simulado):
    st.subheader("🌴 Gestão de Férias e Ausências")
    st.write("Cadastre os períodos de ausência da equipe. O sistema descontará automaticamente as horas úteis desses recursos no Heatmap de Capacidade.")
    
    usuario = st.session_state.get("usuario_logado", "Desconhecido")
    
    # Pega todos os recursos únicos do projeto atual para o dropdown
    todos_recursos = sorted(df_simulado['Resource Name'].dropna().unique().tolist())
    
    # --- FORMULÁRIO DE CADASTRO ---
    with st.form("form_nova_ausencia"):
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            recurso = st.selectbox("👤 Recurso:", [""] + todos_recursos)
        with col2:
            data_inicio = st.date_input("📅 Data Início:")
        with col3:
            # NOVIDADE: Campo de Quantidade de Dias em vez de Data Fim
            qtd_dias = st.number_input("⏳ Quantidade de Dias:", min_value=1, value=30)
        with col4:
            motivo = st.selectbox("🏷️ Motivo:", ["Férias", "Licença Médica", "Folga Compensatória", "Treinamento", "Outros"])
            
        submit = st.form_submit_button("➕ Cadastrar Ausência")
        
        if submit:
            if not recurso:
                st.error("Selecione um recurso.")
            else:
                # Calcula a data fim somando a quantidade de dias (menos 1 para incluir o dia de início como o 1º dia)
                data_fim = data_inicio + timedelta(days=qtd_dias - 1)
                
                db = SessionLocal()
                try:
                    nova_ausencia = ResourceAbsence(
                        resource_name=recurso,
                        start_date=data_inicio,
                        end_date=data_fim,
                        reason=motivo,
                        registered_by=usuario
                    )
                    db.add(nova_ausencia)
                    db.commit()
                    
                    # Registra no log de auditoria com a quantidade de dias
                    registrar_log(
                        user_id=usuario, 
                        action="CREATE", 
                        table_affected="resource_absences", 
                        record_id=recurso, 
                        field_changed="Nova Ausência", 
                        old_value="", 
                        new_value=f"{motivo}: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')} ({qtd_dias} dias corridos)"
                    )
                    
                    st.success(f"✅ Ausência cadastrada com sucesso! (Data fim calculada para **{data_fim.strftime('%d/%m/%Y')}**)")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
                finally:
                    db.close()

    st.write("---")
    st.write("### 📋 Ausências Cadastradas")
    
    df_absences = get_absences()
    
    if df_absences.empty:
        st.info("Nenhuma ausência cadastrada no momento.")
    else:
        # Formata as datas para exibição
        df_display = df_absences.copy()
        df_display['Início'] = pd.to_datetime(df_display['Início']).dt.strftime('%d/%m/%Y')
        df_display['Fim'] = pd.to_datetime(df_display['Fim']).dt.strftime('%d/%m/%Y')
        
        df_display.insert(0, 'Excluir', False)
        
        edited_df = st.data_editor(
            df_display, 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Excluir": st.column_config.CheckboxColumn("🗑️ Excluir?", default=False),
                "ID": None # Esconde o ID do banco
            }
        )
        
        if st.button("🗑️ Remover Ausências Selecionadas"):
            mask_excluir = edited_df['Excluir'] == True
            if mask_excluir.any():
                ids_para_excluir = df_absences[mask_excluir]['ID'].tolist()
                
                db = SessionLocal()
                try:
                    for id_exc in ids_para_excluir:
                        ausencia = db.query(ResourceAbsence).filter(ResourceAbsence.id == id_exc).first()
                        if ausencia:
                            registrar_log(usuario, "DELETE", "resource_absences", ausencia.resource_name, "Exclusão de Ausência", f"{ausencia.start_date} a {ausencia.end_date}", "Excluído")
                            db.delete(ausencia)
                    db.commit()
                    st.success("Ausências removidas com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")
                finally:
                    db.close()