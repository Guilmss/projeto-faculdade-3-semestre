import streamlit as st
from streamlit_option_menu import option_menu
from frontend import pagina_login, exibir_dashboard_completo
import os

st.set_page_config(layout="wide", page_title="Dashboard de Análise de Vendas")

st.markdown("""
<style>
    .stMetric {
        border: 1px solid #E0E0E0;        
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 2px 2px 10px #E0E0E0;
    }
    .stPlotlyChart {
        border-radius: 10px;
        box-shadow: 2px 2px 10px #E0E0E0;
    }
</style>
""", unsafe_allow_html=True)


def main():
    if "view" not in st.session_state:
        st.session_state.view = "Login"
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["user_role"] = None
        st.session_state["username"] = None
        st.session_state["user_permissions"] = {}
    
    if st.session_state["logged_in"]:
        exibir_dashboard_completo()
    else:
        with st.sidebar: # Menu para não logados
            # Adicionar a logo na tela de login
            script_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(script_dir, "SLA.png")

            try:
                if os.path.exists(logo_path):
                    st.image(logo_path, use_container_width=True) # Usar st.image para a sidebar
                else:
                    st.warning(f"Logo não encontrada: {logo_path}")
            except Exception as e:
                st.error(f"Erro ao carregar logo: {e}")

            st.session_state.view = option_menu(
                menu_title="Menu Principal",
                options=["Login"],
                icons=["box-arrow-in-right"],
                menu_icon="cast",
                default_index=0,
            )
        if st.session_state.view == "Login":
            pagina_login()

if __name__ == "__main__":
    main()
