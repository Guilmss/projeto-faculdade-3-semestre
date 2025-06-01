import streamlit as st
import pandas as pd 
import plotly.express as px
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import os

from backend import (
    carregar_dados, verificar_login,
    USUARIOS_FUNCIONARIOS, USUARIOS_GERENTES, 
    COL_CATEGORIA, COL_NOME_PRODUTO, COL_VALOR,
    COL_AVALIACAO, COL_CONTAGEM_AVALIACOES, COL_PERCENTUAL_DESCONTO, 
    COL_SENTIMENTO, COL_PRECO,
    CSV_CATEGORY, CSV_DISCOUNTED_PRICE, CSV_PRODUCT_NAME 
)


def pagina_login():
   
    with st.container():
        st.title("Bem-vindo ao Dashboard de Vendas")
        st.subheader("Login")

        with st.form("login_form"):
            username = st.text_input("Usuário", key="login_username_input")
            password = st.text_input("Senha", type="password", key="login_password_input")
            submitted = st.form_submit_button("Entrar")

            if submitted:
                role = verificar_login(username, password) 
                if role:
                    st.session_state["logged_in"] = True
                    st.session_state["user_role"] = role
                    st.session_state["username"] = username
                    if role == "funcionario":
                        st.session_state["user_permissions"] = USUARIOS_FUNCIONARIOS[username]
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos, ou conta inativa.")


def exibir_dashboard_completo():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(script_dir, "SLA.png")

    try:
        if os.path.exists(logo_path):
            st.sidebar.image(logo_path, use_container_width=True)
        else:
            st.sidebar.warning(f"Logo não encontrada: {logo_path}")
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar logo: {e}")
        
    if st.sidebar.button("Logout", key="logout_button"):
        keys_to_clear = ["logged_in", "user_role", "username", "user_permissions", "view"]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    st.sidebar.markdown(f"Usuário: **{st.session_state.get('username', '')}**")
    st.sidebar.markdown(f"Perfil: **{st.session_state.get('user_role', '').capitalize()}**")
    st.sidebar.markdown("---")

    df_vendas = carregar_dados("vendas.csv") 

    if df_vendas is not None:
        st.title("📊 Dashboard de Análise de Vendas")
        st.markdown("---")

        st.sidebar.header("Filtros do Dashboard")
        df_filtrado = df_vendas.copy()

        if COL_CATEGORIA in df_filtrado.columns:
            categorias_unicas = df_filtrado[COL_CATEGORIA].dropna().unique()
            categorias_disponiveis = ["Todas"] + sorted(list(categorias_unicas))
            categoria_selecionada = st.sidebar.selectbox(f"Selecione a {COL_CATEGORIA}", categorias_disponiveis, key="filtro_categoria")
            if categoria_selecionada != "Todas":
                df_filtrado = df_filtrado[df_filtrado[COL_CATEGORIA] == categoria_selecionada]
        else:
            st.sidebar.warning(f"Coluna '{COL_CATEGORIA}' não encontrada para filtro.")

        st.subheader("Principais Indicadores")
        if not df_filtrado.empty:
            total_vendas = df_filtrado[COL_VALOR].sum()
            media_vendas = df_filtrado[COL_VALOR].mean() if pd.api.types.is_numeric_dtype(df_filtrado[COL_VALOR]) and df_filtrado[COL_VALOR].notna().any() else 0
            if media_vendas == 0 and (not pd.api.types.is_numeric_dtype(df_filtrado[COL_VALOR]) or not df_filtrado[COL_VALOR].notna().any()):
                 st.warning(f"Não foi possível calcular o Ticket Médio pois a coluna '{COL_VALOR}' não é numérica ou não contém dados válidos.")
            num_transacoes = df_filtrado.shape[0]
            col1, col2, col3 = st.columns(3)
            col1.metric("Total de Vendas", f"$ {total_vendas:,.2f}")
            col2.metric("Ticket Médio", f"$ {media_vendas:,.2f}")
            col3.metric("Número de Transações", f"{num_transacoes}")
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados.")

        tabs_titulos = [
            "Visão Geral 📈", "Análise de Produtos 🛍️", "Preços 💲",
            "Exploração Avançada  📊", "Visualizações 3D 🌌",
            "Análise de Feedbacks 📨", "Dados Detalhados 📄"
        ]
        tab_geral, tab_produtos, tab_precos_avaliacoes, tab_matplotlib_avancado, tab_3d, tab_sentimento, tab_dados_detalhados = st.tabs(tabs_titulos)

        with tab_geral:
            st.subheader("Performance Geral de Vendas")
            if not df_filtrado.empty:
                if COL_CATEGORIA in df_filtrado.columns and COL_VALOR in df_filtrado.columns:
                    vendas_por_categoria = df_filtrado.groupby(COL_CATEGORIA)[COL_VALOR].sum().reset_index()
                    if not vendas_por_categoria.empty:
                        fig = px.pie(vendas_por_categoria, values=COL_VALOR, names=COL_CATEGORIA, title=f"Distribuição de Vendas por {COL_CATEGORIA}", color_discrete_sequence=px.colors.qualitative.Pastel)
                        st.plotly_chart(fig, use_container_width=True)
                    else: st.info("Nenhuma venda para categorias nos filtros.")
                else: st.info(f"Gráfico de Vendas por {COL_CATEGORIA} desabilitado.")
            else: st.info("Selecione filtros para gráficos.")

        with tab_produtos:
            st.subheader("Análise Detalhada de Produtos")
            if not df_filtrado.empty:
                if COL_NOME_PRODUTO in df_filtrado.columns and COL_VALOR in df_filtrado.columns:
                    top_n = st.slider("Top Produtos:", 5, 20, 10, key="top_n_slider")
                    top_produtos = df_filtrado.groupby(COL_NOME_PRODUTO)[COL_VALOR].sum().nlargest(top_n).reset_index()
                    fig = px.bar(top_produtos, x=COL_NOME_PRODUTO, y=COL_VALOR, title=f"Top {top_n} Produtos por {COL_VALOR}", labels={COL_NOME_PRODUTO: 'Produto', COL_VALOR: 'Vendas ($)'}, color=COL_VALOR, color_continuous_scale=px.colors.sequential.Viridis)
                    fig.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)
                if COL_CATEGORIA in df_filtrado.columns:
                    contagem_categoria = df_filtrado[COL_CATEGORIA].value_counts().reset_index()
                    contagem_categoria.columns = [COL_CATEGORIA, 'Contagem']
                    fig = px.bar(contagem_categoria, x=COL_CATEGORIA, y='Contagem', title=f"Produtos por {COL_CATEGORIA}", labels={COL_CATEGORIA: COL_CATEGORIA, 'Contagem': 'Nº Produtos'}, color=COL_CATEGORIA, color_discrete_sequence=px.colors.qualitative.Set3)
                    st.plotly_chart(fig, use_container_width=True)
            else: st.info("Selecione filtros para gráficos.")

        with tab_precos_avaliacoes:
            st.subheader(f"Análise de Preços ({COL_VALOR}), Descontos e Avaliações")
            if not df_filtrado.empty:
                if COL_VALOR in df_filtrado.columns:
                    fig = px.histogram(df_filtrado, x=COL_VALOR, nbins=30, title=f"Distribuição de Preços ({COL_VALOR} com Desconto)", labels={COL_VALOR: 'Preço ($)'}, color_discrete_sequence=['skyblue'])
                    st.plotly_chart(fig, use_container_width=True)
                if COL_VALOR in df_filtrado.columns and df_filtrado[COL_VALOR].notna().any():
                    st.markdown("---")
                    st.subheader("Distribuição de Preços (Seaborn/Matplotlib)")
                    fig_s, ax_s = plt.subplots()
                    sns.histplot(df_filtrado[COL_VALOR], kde=True, ax=ax_s, color="steelblue")
                    ax_s.set_title('Distribuição de Preços com Densidade')
                    ax_s.set_xlabel('Preço ($)'); ax_s.set_ylabel('Frequência / Densidade')
                    st.pyplot(fig_s); plt.close(fig_s)
                if COL_VALOR in df_filtrado.columns and COL_AVALIACAO in df_filtrado.columns and df_filtrado[COL_AVALIACAO].notna().any():
                    fig = px.scatter(df_filtrado.dropna(subset=[COL_AVALIACAO, COL_VALOR]), x=COL_AVALIACAO, y=COL_VALOR, title=f"Preço ({COL_VALOR}) vs. {COL_AVALIACAO}", labels={COL_AVALIACAO: 'Avaliação', COL_VALOR: 'Preço ($)'}, hover_data=[COL_NOME_PRODUTO], color=COL_AVALIACAO, color_continuous_scale=px.colors.sequential.Plasma)
                    st.plotly_chart(fig, use_container_width=True)
                if COL_NOME_PRODUTO in df_filtrado.columns and COL_PERCENTUAL_DESCONTO in df_filtrado.columns and df_filtrado[COL_PERCENTUAL_DESCONTO].notna().any():
                    top_n_desconto = st.slider("Produtos com Maior Desconto:", 5, 20, 10, key="top_n_desconto_slider")
                    produtos_maior_desconto = df_filtrado.nlargest(top_n_desconto, COL_PERCENTUAL_DESCONTO)
                    fig = px.bar(produtos_maior_desconto, x=COL_NOME_PRODUTO, y=COL_PERCENTUAL_DESCONTO, title=f"Top {top_n_desconto} Produtos por {COL_PERCENTUAL_DESCONTO}", labels={COL_NOME_PRODUTO: 'Produto', COL_PERCENTUAL_DESCONTO: 'Desconto (%)'}, color=COL_PERCENTUAL_DESCONTO, color_continuous_scale=px.colors.sequential.OrRd)
                    fig.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)
            else: st.info("Selecione filtros para gráficos.")

        with tab_matplotlib_avancado:
            st.subheader("Exploração Avançada com Matplotlib & Seaborn")
            if not df_filtrado.empty:
                st.markdown("---"); st.write(f"#### Box Plot: {COL_VALOR} por {COL_CATEGORIA}")
                if COL_CATEGORIA in df_filtrado.columns and COL_VALOR in df_filtrado.columns:
                    fig, ax = plt.subplots(figsize=(12, 7))
                    sns.boxplot(x=COL_CATEGORIA, y=COL_VALOR, data=df_filtrado, ax=ax, palette="Set3")
                    ax.set_title(f'Distribuição de {COL_VALOR} por {COL_CATEGORIA}'); ax.set_xlabel(COL_CATEGORIA); ax.set_ylabel(f'{COL_VALOR} ($)')
                    plt.xticks(rotation=45, ha='right'); plt.tight_layout(); st.pyplot(fig); plt.close(fig)
                else: st.info(f"Colunas '{COL_CATEGORIA}' ou '{COL_VALOR}' não disponíveis.")

                st.markdown("---"); st.write(f"#### Violin Plot: {COL_AVALIACAO} por {COL_CATEGORIA}")
                if COL_CATEGORIA in df_filtrado.columns and COL_AVALIACAO in df_filtrado.columns and df_filtrado[COL_AVALIACAO].notna().any():
                    fig, ax = plt.subplots(figsize=(12, 7))
                    sns.violinplot(x=COL_CATEGORIA, y=COL_AVALIACAO, data=df_filtrado.dropna(subset=[COL_AVALIACAO]), ax=ax, palette="Pastel1")
                    ax.set_title(f'Distribuição de {COL_AVALIACAO} por {COL_CATEGORIA}'); ax.set_xlabel(COL_CATEGORIA); ax.set_ylabel(COL_AVALIACAO)
                    plt.xticks(rotation=45, ha='right'); plt.tight_layout(); st.pyplot(fig); plt.close(fig)
                else: st.info(f"Colunas '{COL_CATEGORIA}' ou '{COL_AVALIACAO}' não disponíveis.")

                st.markdown("---"); st.write(f"#### Scatter Plot: {COL_VALOR} vs. {COL_PERCENTUAL_DESCONTO}")
                if COL_VALOR in df_filtrado.columns and COL_PERCENTUAL_DESCONTO in df_filtrado.columns and df_filtrado[COL_PERCENTUAL_DESCONTO].notna().any():
                    fig, ax = plt.subplots(figsize=(10, 6))
                    sns.scatterplot(x=COL_PERCENTUAL_DESCONTO, y=COL_VALOR, data=df_filtrado.dropna(subset=[COL_PERCENTUAL_DESCONTO, COL_VALOR]), ax=ax, hue=COL_CATEGORIA, palette="viridis", alpha=0.7)
                    ax.set_title(f'Relação {COL_VALOR} vs. {COL_PERCENTUAL_DESCONTO}'); ax.set_xlabel(f'{COL_PERCENTUAL_DESCONTO} (%)'); ax.set_ylabel(f'{COL_VALOR} ($)')
                    plt.tight_layout(); st.pyplot(fig); plt.close(fig)
                else: st.info(f"Colunas '{COL_VALOR}' ou '{COL_PERCENTUAL_DESCONTO}' não disponíveis.")

                st.markdown("---"); st.write("#### Heatmap de Correlação")
                numeric_cols = df_filtrado.select_dtypes(include=np.number).columns.tolist()
                if len(numeric_cols) > 1:
                    corr_matrix = df_filtrado[numeric_cols].corr()
                    fig, ax = plt.subplots(figsize=(10, 8))
                    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f", linewidths=.5, ax=ax)
                    ax.set_title('Heatmap de Correlação'); plt.tight_layout(); st.pyplot(fig); plt.close(fig)
                else: st.info("Não há variáveis numéricas suficientes.")

                st.markdown("---"); st.write(f"#### Count Plot: Produtos por {COL_CATEGORIA}")
                if COL_CATEGORIA in df_filtrado.columns:
                    fig, ax = plt.subplots(figsize=(12, 7))
                    sns.countplot(y=COL_CATEGORIA, data=df_filtrado, ax=ax, palette="Spectral", order = df_filtrado[COL_CATEGORIA].value_counts().index)
                    ax.set_title(f'Produtos por {COL_CATEGORIA}'); ax.set_xlabel('Contagem'); ax.set_ylabel(COL_CATEGORIA)
                    plt.tight_layout(); st.pyplot(fig); plt.close(fig)
                else: st.info(f"Coluna '{COL_CATEGORIA}' não disponível.")

                st.markdown("---"); st.write(f"#### Joint Plot: {COL_AVALIACAO} vs. {COL_CONTAGEM_AVALIACOES}")
                if COL_AVALIACAO in df_filtrado.columns and COL_CONTAGEM_AVALIACOES in df_filtrado.columns and df_filtrado[COL_AVALIACAO].notna().any() and df_filtrado[COL_CONTAGEM_AVALIACOES].notna().any():
                    joint_fig = sns.jointplot(x=COL_AVALIACAO, y=COL_CONTAGEM_AVALIACOES, 
                                              data=df_filtrado.dropna(subset=[COL_AVALIACAO, COL_CONTAGEM_AVALIACOES]), 
                                              kind='scatter', color='skyblue', marginal_kws=dict(bins=15, fill=True))
                    joint_fig.fig.suptitle(f'{COL_AVALIACAO} vs. {COL_CONTAGEM_AVALIACOES} (Marginais)', y=1.02)
                    st.pyplot(joint_fig.fig); plt.close(joint_fig.fig)
                else: st.info(f"Colunas '{COL_AVALIACAO}' ou '{COL_CONTAGEM_AVALIACOES}' não disponíveis.")
            else: st.info("Selecione filtros para gráficos.")

        with tab_3d:
            st.subheader("Visualizações 3D Interativas")
            if not df_filtrado.empty:
                st.markdown("---"); st.write(f"#### Dispersão 3D: {COL_VALOR}, {COL_AVALIACAO}, {COL_CONTAGEM_AVALIACOES}")
                cols_3d = [COL_VALOR, COL_AVALIACAO, COL_CONTAGEM_AVALIACOES]
                if all(col in df_filtrado.columns for col in cols_3d) and all(df_filtrado[col].notna().any() for col in cols_3d):
                    df_3d = df_filtrado.dropna(subset=cols_3d)
                    fig = px.scatter_3d(df_3d, x=COL_AVALIACAO, y=COL_CONTAGEM_AVALIACOES, z=COL_VALOR, color=COL_CATEGORIA, 
                                        title=f"3D: {COL_AVALIACAO}, {COL_CONTAGEM_AVALIACOES}, {COL_VALOR}", 
                                        labels={COL_AVALIACAO: 'Avaliação', COL_CONTAGEM_AVALIACOES: 'Nº Avaliações', COL_VALOR: 'Preço ($)'})
                    st.plotly_chart(fig, use_container_width=True)
                else: st.info(f"Colunas '{COL_VALOR}', '{COL_AVALIACAO}' ou '{COL_CONTAGEM_AVALIACOES}' não disponíveis para 3D.")
            else: st.info("Selecione filtros para gráficos.")
        
        with tab_sentimento:
            st.subheader("Análise de Sentimento Baseada em Avaliações")
            if not df_filtrado.empty and COL_SENTIMENTO in df_filtrado.columns:
                sent_counts = df_filtrado[COL_SENTIMENTO].value_counts().reset_index()
                sent_counts.columns = [COL_SENTIMENTO, 'Contagem']
                fig = px.bar(sent_counts, x=COL_SENTIMENTO, y='Contagem', title="Distribuição de Sentimento", 
                             labels={COL_SENTIMENTO: 'Sentimento', 'Contagem': 'Nº Produtos'}, color=COL_SENTIMENTO, 
                             color_discrete_map={'Positivo': '#2ca02c', 'Neutro': '#1f77b4', 'Negativo': '#d62728', 'Não Avaliado': '#7f7f7f'}, 
                             category_orders={COL_SENTIMENTO: ["Positivo", "Neutro", "Negativo", "Não Avaliado"]})
                st.plotly_chart(fig, use_container_width=True)
                if COL_CATEGORIA in df_filtrado.columns:
                    st.markdown("---"); st.write(f"#### {COL_SENTIMENTO} por {COL_CATEGORIA}")
                    sent_cat = df_filtrado.groupby([COL_CATEGORIA, COL_SENTIMENTO]).size().reset_index(name='Contagem')
                    if not sent_cat.empty:
                        fig = px.bar(sent_cat, x=COL_CATEGORIA, y='Contagem', color=COL_SENTIMENTO, title=f"{COL_SENTIMENTO} por {COL_CATEGORIA}", barmode='group',
                                      color_discrete_map={'Positivo': '#2ca02c', 'Neutro': '#1f77b4', 'Negativo': '#d62728', 'Não Avaliado': '#7f7f7f'},
                                        category_orders={COL_SENTIMENTO: ["Positivo", "Neutro", "Negativo", "Não Avaliado"]})
                        st.plotly_chart(fig, use_container_width=True)
                    else: st.info("Sem dados de sentimento por categoria.")
            elif COL_SENTIMENTO not in df_filtrado.columns:
                st.warning(f"Coluna '{COL_SENTIMENTO}' não gerada. Verifique '{COL_AVALIACAO}'.")
            else: st.info("Sem dados para análise de sentimento.")

        with tab_dados_detalhados:
            st.subheader("Dados Detalhados Filtrados 📄")
            user_can_see = st.session_state.get("user_permissions", {}).get("can_see_details", False)
            if st.session_state.get("user_role") == "gerente": user_can_see = True
            if user_can_see:
                cols_mostrar = [COL_NOME_PRODUTO, COL_CATEGORIA, COL_VALOR, COL_AVALIACAO, COL_SENTIMENTO, COL_CONTAGEM_AVALIACOES, COL_PERCENTUAL_DESCONTO, COL_PRECO]
                cols_existentes = [col for col in cols_mostrar if col in df_filtrado.columns]
                st.dataframe(df_filtrado[cols_existentes] if cols_existentes else df_filtrado, height=400, use_container_width=True)
            else: st.info("Sem permissão para ver dados detalhados.")
    else:
        st.error("⚠️ Não foi possível carregar os dados. Verifique 'vendas.csv'.")
        st.info(f"Verifique se 'vendas.csv' está na pasta e contém as colunas '{CSV_CATEGORY}', '{CSV_DISCOUNTED_PRICE}', '{CSV_PRODUCT_NAME}'.")

    # --- SEÇÃO ESPECÍFICA PARA GERENTES (no frontend, mas usa dados do backend) ---
    if st.session_state.get("user_role") == "gerente":
        st.sidebar.markdown("---")
        st.sidebar.subheader("Painel do Gerente")
        with st.sidebar.expander("Criar Nova Conta de Funcionário", expanded=False):
            with st.form("create_employee_form", clear_on_submit=True):
                st.subheader("Novo Funcionário")
                new_username = st.text_input("Nome de Usuário")
                new_password = st.text_input("Senha", type="password")
                new_password_confirm = st.text_input("Confirmar Senha", type="password")
                can_see_details_new = st.checkbox("Permitir ver dados detalhados", value=False)
                is_active_new = st.checkbox("Conta Ativa", value=True)
                create_submitted = st.form_submit_button("Criar Conta")
                if create_submitted:
                    if not new_username or not new_password: st.error("Usuário e senha obrigatórios.")
                    elif new_password != new_password_confirm: st.error("Senhas não coincidem.")
                    elif new_username in USUARIOS_FUNCIONARIOS or new_username in USUARIOS_GERENTES: st.error("Usuário já existe.")
                    else:
                        USUARIOS_FUNCIONARIOS[new_username] = {"password": new_password, "can_see_details": can_see_details_new, "active": is_active_new}
                        st.success(f"Conta para '{new_username}' criada!"); st.rerun()
        with st.sidebar.expander("Gerenciar Funcionários Ativos", expanded=False):
            if not USUARIOS_FUNCIONARIOS: st.write("Nenhum funcionário ativo.")
            else:
                for user, data in USUARIOS_FUNCIONARIOS.items():
                    st.markdown(f"**Usuário:** {user}")
                    is_active = data.get("active", False)
                    new_active_status = st.checkbox("Ativo", value=is_active, key=f"active_{user}")
                    if new_active_status != is_active: USUARIOS_FUNCIONARIOS[user]["active"] = new_active_status; st.rerun()
                    can_see_details_perm = data.get("can_see_details", False)
                    new_detail_perm = st.checkbox("Permitir ver dados detalhados", value=can_see_details_perm, key=f"details_{user}")
                    if new_detail_perm != can_see_details_perm: USUARIOS_FUNCIONARIOS[user]["can_see_details"] = new_detail_perm; st.rerun()
                    st.markdown("---")
