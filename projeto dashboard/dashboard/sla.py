import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_option_menu import option_menu 
import matplotlib.pyplot as plt 
import numpy as np 
import seaborn as sns
import os

# Configuração da página
st.set_page_config(layout="wide", page_title="Dashboard de Análise de Vendas")

# --- ESTILIZAÇÃO COM CSS ---
st.markdown("""
<style>
    /* Adicione seu CSS customizado aqui */
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


USUARIOS_FUNCIONARIOS = {
    "func1": {"password": "senha123", "can_see_details": True, "active": True},
    "ana.vendas": {"password": "vendas2024", "can_see_details": False, "active": True}
}

USUARIOS_GERENTES = {
    "gerente01": "admin456",
    "boss": "chefe10"
}

# Para armazenar solicitações de registro pendentes (em memória para este exemplo)
# Estrutura: {username: "password_solicitada"}
if "pending_registrations" not in st.session_state:
    st.session_state.pending_registrations = {}


# --- CARREGAMENTO E PREPARAÇÃO DOS DADOS ---
@st.cache_data # Cache para otimizar o carregamento de dados
def carregar_dados(nome_arquivo_csv):
    try:
        # Constrói o caminho absoluto para o arquivo CSV
        # __file__ é o caminho para o script atual (sla.py)
        # os.path.dirname(os.path.abspath(__file__)) é o diretório onde sla.py está
        # os.path.join une o diretório com o nome do arquivo
        script_dir = os.path.dirname(os.path.abspath(__file__))


        caminho_arquivo = os.path.join(script_dir, nome_arquivo_csv)
        df = pd.read_csv(caminho_arquivo)

        if df.empty:
            st.error(f"O arquivo '{caminho_arquivo}' está vazio.")
            return None

        # Verificar colunas essenciais do CSV original
        colunas_csv_originais_necessarias = ['category', 'discounted_price', 'product_name']
        colunas_faltantes_csv = [col for col in colunas_csv_originais_necessarias if col not in df.columns]

        if colunas_faltantes_csv:
            st.error(f"As seguintes colunas essenciais do CSV não foram encontradas: {', '.join(colunas_faltantes_csv)}.")
            st.info(f"Colunas encontradas no CSV: {df.columns.tolist()}")
            return None

        # Renomear colunas para o padrão do dashboard
        df = df.rename(columns={
            'category': 'Categoria',
            'product_name': 'Nome do Produto', # Mantendo para exibição
            'discounted_price': 'Valor',
            'rating': 'Avaliação',
            'rating_count': 'Contagem de Avaliações',
            'discount_percentage': 'Percentual de Desconto'
        })

        # Limpeza e conversão da coluna 'Valor'
        if 'Valor' in df.columns:
            df['Valor'] = df['Valor'].astype(str).str.replace('₹', '', regex=False).str.replace(',', '', regex=False)
            df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
            df.dropna(subset=['Valor'], inplace=True) # Remover linhas onde a conversão para número falhou
        else:
            # Se 'discounted_price' não for uma das colunas essenciais, isso pode ser um aviso em vez de erro
            st.warning("Coluna 'Valor' (mapeada de 'discounted_price') não encontrada ou não pôde ser processada.")
            # Não retornaremos None aqui, pois o dashboard pode funcionar parcialmente sem 'Valor'

        # Limpeza e conversão da coluna 'actual_price' (se existir)
        if 'actual_price' in df.columns:
            df['actual_price'] = df['actual_price'].astype(str).str.replace('₹', '', regex=False).str.replace(',', '', regex=False)
            df['actual_price'] = pd.to_numeric(df['actual_price'], errors='coerce')

        # Limpeza da coluna 'Avaliação' (rating) - ex: "4.2 out of 5 stars" -> 4.2
        if 'Avaliação' in df.columns:
            df['Avaliação'] = df['Avaliação'].astype(str).str.extract(r'(\d+\.?\d*)').astype(float)

        # Limpeza da coluna 'Contagem de Avaliações' (rating_count) - ex: "24,269" -> 24269
        if 'Contagem de Avaliações' in df.columns:
            df['Contagem de Avaliações'] = df['Contagem de Avaliações'].astype(str).str.replace(',', '', regex=False)
            df['Contagem de Avaliações'] = pd.to_numeric(df['Contagem de Avaliações'], errors='coerce')

        # Limpeza da coluna 'Percentual de Desconto' (discount_percentage) - ex: "70%" -> 70
        if 'Percentual de Desconto' in df.columns:
            df['Percentual de Desconto'] = df['Percentual de Desconto'].astype(str).str.replace('%', '', regex=False)
            df['Percentual de Desconto'] = pd.to_numeric(df['Percentual de Desconto'], errors='coerce')

        # Extrair a categoria principal da coluna 'Categoria'
        if 'Categoria' in df.columns:
            df['Categoria'] = df['Categoria'].astype(str).str.split('|').str[0]
        else:
            st.error("Coluna 'Categoria' (mapeada de 'category') não encontrada após renomeação.")
            return None
        
        # Verificar se 'Nome do Produto' existe após o rename, pois é usado em gráficos
        if 'Nome do Produto' not in df.columns:
            st.error("Coluna 'Nome do Produto' (mapeada de 'product_name') não encontrada após renomeação.")
            return None
            
        return df
        
    except FileNotFoundError:
        st.error(f"ARQUIVO NÃO ENCONTRADO: '{caminho_arquivo}'.")
        st.info(f"Verifique se o arquivo está na mesma pasta que o script (sla.py) ou se o caminho está correto.")
        return None
    except pd.errors.ParserError:
        st.error(f"Erro ao analisar (parse) o arquivo CSV '{caminho_arquivo}'. Verifique se o arquivo é um CSV válido e se o separador está correto (geralmente vírgula).")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao carregar os dados de '{caminho_arquivo}': {e}")
        return None

# --- FUNÇÕES DE LOGIN ---
def verificar_login(username, password):
    """Verifica as credenciais e retorna o papel do usuário ou None."""
    if username in USUARIOS_FUNCIONARIOS:
        user_data = USUARIOS_FUNCIONARIOS[username]
        if user_data["password"] == password and user_data.get("active", False): # Verifica se está ativo
            return "funcionario"
    if username in USUARIOS_GERENTES and USUARIOS_GERENTES[username] == password:
        return "gerente"
    return None

def pagina_login():
    """Exibe o formulário de login."""
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
        
        st.markdown("---")
        if st.button("Criar Conta de Funcionário", key="show_register_page"):
            st.session_state.view = "register"
            st.rerun()

def pagina_registro():
    """Exibe o formulário de registro para funcionários."""
    with st.container():
        st.title("Criar Conta de Funcionário")
        st.write("Após o registro, sua conta precisará ser aprovada por um gerente.")

        with st.form("register_form"):
            reg_username = st.text_input("Nome de Usuário Desejado", key="reg_username")
            reg_password = st.text_input("Senha", type="password", key="reg_password")
            reg_password_confirm = st.text_input("Confirme a Senha", type="password", key="reg_password_confirm")
            register_submitted = st.form_submit_button("Registrar")

            if register_submitted:
                if not reg_username or not reg_password:
                    st.error("Nome de usuário e senha são obrigatórios.")
                elif reg_password != reg_password_confirm:
                    st.error("As senhas não coincidem.")
                elif reg_username in USUARIOS_FUNCIONARIOS or reg_username in USUARIOS_GERENTES or reg_username in st.session_state.pending_registrations:
                    st.error("Este nome de usuário já existe ou está pendente de aprovação.")
                else:
                    # Adiciona à lista de pendentes (em memória)
                    st.session_state.pending_registrations[reg_username] = reg_password
                    st.success("Solicitação de registro enviada! Aguarde a aprovação do gerente.")
                    st.info("Você será redirecionado para a páginwwwwwa de login em alguns segundos...")
                    # Idealmente, um st.experimental_rerun() com delay ou um botão para voltar
                    st.session_state.view = "login" # Volta para a tela de login
                    # Para forçar a atualização da UI após o sucesso:
                    # import time
                    # time.sleep(3)
                    # st.rerun() 
        
        if st.button("Voltar para Login", key="back_to_login_from_register"):
            st.session_state.view = "login"
            st.rerun()

def exibir_dashboard_completo():
    """Exibe o dashboard principal após o login."""

    # Botão de Logout na sidebar
    if st.sidebar.button("Logout", key="logout_button"):
        # Limpa todas as chaves do session_state relacionadas ao login
        keys_to_clear = ["logged_in", "user_role", "username", "user_permissions", "view"]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun() # Re-executa para voltar à tela de login

    st.sidebar.markdown(f"Usuário: **{st.session_state.get('username', '')}**")
    st.sidebar.markdown(f"Perfil: **{st.session_state.get('user_role', '').capitalize()}**")
    st.sidebar.markdown("---")

    # Carregar os dados do arquivo vendas.csv
    df_vendas = carregar_dados("vendas.csv")

    if df_vendas is not None:
        st.title("📊 Dashboard de Análise de Vendas")
        st.markdown("---")

        # --- SIDEBAR PARA FILTROS ---
        st.sidebar.header("Filtros do Dashboard")

        df_filtrado = df_vendas.copy() # Começa com todos os dados

        # Filtro de Categoria
        if 'Categoria' in df_filtrado.columns:
            categorias_unicas = df_filtrado['Categoria'].dropna().unique()
            categorias_disponiveis = ["Todas"] + sorted(list(categorias_unicas))
            categoria_selecionada = st.sidebar.selectbox("Selecione a Categoria", categorias_disponiveis, key="filtro_categoria")

            if categoria_selecionada != "Todas":
                df_filtrado = df_filtrado[df_filtrado['Categoria'] == categoria_selecionada]
        else:
            st.sidebar.warning("Coluna 'Categoria' não encontrada para filtro.")

        # --- KPIs PRINCIPAIS ---
        st.subheader("Principais Indicadores")
        
        if not df_filtrado.empty:
            total_vendas = df_filtrado['Valor'].sum()
            
            if pd.api.types.is_numeric_dtype(df_filtrado['Valor']) and df_filtrado['Valor'].notna().any():
                media_vendas = df_filtrado['Valor'].mean()
            else:
                media_vendas = 0 
                st.warning("Não foi possível calcular o Ticket Médio pois a coluna 'Valor' não é numérica ou não contém dados válidos.")
                
            num_transacoes = df_filtrado.shape[0]

            col1, col2, col3 = st.columns(3)
            col1.metric("Total de Vendas", f"$ {total_vendas:,.2f}") 
            col2.metric("Ticket Médio", f"$ {media_vendas:,.2f}")
            col3.metric("Número de Transações", f"{num_transacoes}")
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados.")

        # --- ABAS PARA ORGANIZAR O CONTEÚDO ---
        tab_geral, tab_produtos, tab_precos_avaliacoes, tab_matplotlib_avancado, tab_3d, tab_dados_detalhados = st.tabs([
            "Visão Geral 📈", 
            "Análise de Produtos 🛍️", 
            "Preços e Avaliações 💲⭐",
            "Exploração Avançada (Matplotlib) 📊",
            "Visualizações 3D 🌌",
            "Dados Detalhados 📄"
        ])

        with tab_geral:
            st.subheader("Performance Geral de Vendas")
            if not df_filtrado.empty:
                # Gráfico de Vendas por Categoria (Pizza)
                if 'Categoria' in df_filtrado.columns and 'Valor' in df_filtrado.columns:
                    vendas_por_categoria = df_filtrado.groupby('Categoria')['Valor'].sum().reset_index()
                    if not vendas_por_categoria.empty:
                        fig_vendas_categoria_pizza = px.pie(vendas_por_categoria, values='Valor', names='Categoria', 
                                                            title="Distribuição de Vendas por Categoria",
                                                            color_discrete_sequence=px.colors.qualitative.Pastel)
                        st.plotly_chart(fig_vendas_categoria_pizza, use_container_width=True)
                    else:
                        st.info("Nenhuma venda encontrada para as categorias nos filtros selecionados.")
                else:
                    st.info("Gráfico de Vendas por Categoria desabilitado (colunas 'Categoria' ou 'Valor' não disponíveis).")
            else:
                st.info("Selecione filtros para visualizar os gráficos.")

        with tab_produtos:
            st.subheader("Análise Detalhada de Produtos")
            if not df_filtrado.empty:
                # Top N Produtos por Valor de Venda
                if 'Nome do Produto' in df_filtrado.columns and 'Valor' in df_filtrado.columns:
                    top_n = st.slider("Número de Top Produtos para exibir:", 5, 20, 10, key="top_n_slider")
                    top_produtos = df_filtrado.groupby('Nome do Produto')['Valor'].sum().nlargest(top_n).reset_index()
                    fig_top_produtos = px.bar(top_produtos, x='Nome do Produto', y='Valor', 
                                              title=f"Top {top_n} Produtos por Valor de Venda",
                                              labels={'Nome do Produto': 'Produto', 'Valor': 'Total de Vendas ($)'},
                                              color='Valor', color_continuous_scale=px.colors.sequential.Viridis)
                    fig_top_produtos.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig_top_produtos, use_container_width=True)

                # Contagem de Produtos por Categoria (Gráfico de Barras)
                if 'Categoria' in df_filtrado.columns:
                    contagem_categoria = df_filtrado['Categoria'].value_counts().reset_index()
                    contagem_categoria.columns = ['Categoria', 'Contagem']
                    fig_contagem_categoria = px.bar(contagem_categoria, x='Categoria', y='Contagem',
                                                    title="Contagem de Produtos por Categoria",
                                                    labels={'Categoria': 'Categoria', 'Contagem': 'Número de Produtos'},
                                                    color='Categoria', color_discrete_sequence=px.colors.qualitative.Set3)
                    st.plotly_chart(fig_contagem_categoria, use_container_width=True)
            else:
                st.info("Selecione filtros para visualizar os gráficos.")

        with tab_precos_avaliacoes:
            st.subheader("Análise de Preços, Descontos e Avaliações")
            if not df_filtrado.empty:
                # Histograma da Distribuição de Preços (Valor)
                if 'Valor' in df_filtrado.columns:
                    fig_hist_preco = px.histogram(df_filtrado, x='Valor', nbins=30, title="Distribuição de Preços dos Produtos (Valor com Desconto)",
                                                  labels={'Valor': 'Preço ($)'}, color_discrete_sequence=['skyblue'])
                    st.plotly_chart(fig_hist_preco, use_container_width=True)
                
                # Histograma com KDE usando Seaborn/Matplotlib
                if 'Valor' in df_filtrado.columns and df_filtrado['Valor'].notna().any():
                    st.markdown("---") # Separador visual
                    st.subheader("Distribuição de Preços (Seaborn/Matplotlib)")
                    fig_seaborn, ax_seaborn = plt.subplots() # Criar figura e eixos Matplotlib
                    sns.histplot(df_filtrado['Valor'], kde=True, ax=ax_seaborn, color="steelblue")
                    ax_seaborn.set_title('Distribuição de Preços com Curva de Densidade')
                    ax_seaborn.set_xlabel('Preço ($)')
                    ax_seaborn.set_ylabel('Frequência / Densidade')
                    st.pyplot(fig_seaborn) # Exibir o gráfico Matplotlib no Streamlit
                    plt.close(fig_seaborn) # Fechar a figura para liberar memória

                # Relação entre Preço (Valor) e Avaliação
                if 'Valor' in df_filtrado.columns and 'Avaliação' in df_filtrado.columns and df_filtrado['Avaliação'].notna().any():
                    fig_scatter_preco_avaliacao = px.scatter(df_filtrado.dropna(subset=['Avaliação', 'Valor']), 
                                                             x='Avaliação', y='Valor', title="Relação Preço vs. Avaliação",
                                                             labels={'Avaliação': 'Avaliação Média', 'Valor': 'Preço ($)'},
                                                             hover_data=['Nome do Produto'], color='Avaliação',
                                                             color_continuous_scale=px.colors.sequential.Plasma)
                    st.plotly_chart(fig_scatter_preco_avaliacao, use_container_width=True)
                
                # Produtos com Maior Percentual de Desconto
                if 'Nome do Produto' in df_filtrado.columns and 'Percentual de Desconto' in df_filtrado.columns and df_filtrado['Percentual de Desconto'].notna().any():
                    top_n_desconto = st.slider("Número de Produtos com Maior Desconto:", 5, 20, 10, key="top_n_desconto_slider")
                    produtos_maior_desconto = df_filtrado.nlargest(top_n_desconto, 'Percentual de Desconto')
                    fig_maior_desconto = px.bar(produtos_maior_desconto, x='Nome do Produto', y='Percentual de Desconto',
                                                title=f"Top {top_n_desconto} Produtos por Percentual de Desconto",
                                                labels={'Nome do Produto': 'Produto', 'Percentual de Desconto': 'Desconto (%)'},
                                                color='Percentual de Desconto', color_continuous_scale=px.colors.sequential.OrRd)
                    fig_maior_desconto.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig_maior_desconto, use_container_width=True)
            else:
                st.info("Selecione filtros para visualizar os gráficos.")

        with tab_matplotlib_avancado:
            st.subheader("Exploração Avançada com Matplotlib & Seaborn")

            if not df_filtrado.empty:
                st.markdown("---")
                st.write("#### Box Plot: Distribuição de Valor por Categoria")
                if 'Categoria' in df_filtrado.columns and 'Valor' in df_filtrado.columns:
                    fig_box, ax_box = plt.subplots(figsize=(12, 7))
                    sns.boxplot(x='Categoria', y='Valor', data=df_filtrado, ax=ax_box, palette="Set3")
                    ax_box.set_title('Distribuição de Valor por Categoria')
                    ax_box.set_xlabel('Categoria')
                    ax_box.set_ylabel('Valor ($)')
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()
                    st.pyplot(fig_box)
                    plt.close(fig_box)
                else:
                    st.info("Colunas 'Categoria' ou 'Valor' não disponíveis para Box Plot.")

                st.markdown("---")
                st.write("#### Violin Plot: Distribuição de Avaliação por Categoria")
                if 'Categoria' in df_filtrado.columns and 'Avaliação' in df_filtrado.columns and df_filtrado['Avaliação'].notna().any():
                    fig_violin, ax_violin = plt.subplots(figsize=(12, 7))
                    sns.violinplot(x='Categoria', y='Avaliação', data=df_filtrado.dropna(subset=['Avaliação']), ax=ax_violin, palette="Pastel1")
                    ax_violin.set_title('Distribuição de Avaliação por Categoria')
                    ax_violin.set_xlabel('Categoria')
                    ax_violin.set_ylabel('Avaliação')
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()
                    st.pyplot(fig_violin)
                    plt.close(fig_violin)
                else:
                    st.info("Colunas 'Categoria' ou 'Avaliação' não disponíveis ou sem dados para Violin Plot.")

                st.markdown("---")
                st.write("#### Scatter Plot: Valor vs. Percentual de Desconto")
                if 'Valor' in df_filtrado.columns and 'Percentual de Desconto' in df_filtrado.columns and df_filtrado['Percentual de Desconto'].notna().any():
                    fig_scatter_mpl, ax_scatter_mpl = plt.subplots(figsize=(10, 6))
                    sns.scatterplot(x='Percentual de Desconto', y='Valor', data=df_filtrado.dropna(subset=['Percentual de Desconto', 'Valor']), ax=ax_scatter_mpl, hue='Categoria', palette="viridis", alpha=0.7)
                    ax_scatter_mpl.set_title('Relação entre Valor e Percentual de Desconto')
                    ax_scatter_mpl.set_xlabel('Percentual de Desconto (%)')
                    ax_scatter_mpl.set_ylabel('Valor ($)')
                    plt.tight_layout()
                    st.pyplot(fig_scatter_mpl)
                    plt.close(fig_scatter_mpl)
                else:
                    st.info("Colunas 'Valor' ou 'Percentual de Desconto' não disponíveis ou sem dados para Scatter Plot.")

                st.markdown("---")
                st.write("#### Heatmap de Correlação entre Variáveis Numéricas")
                numeric_cols = df_filtrado.select_dtypes(include=np.number).columns.tolist()
                if len(numeric_cols) > 1:
                    correlation_matrix = df_filtrado[numeric_cols].corr()
                    fig_heatmap, ax_heatmap = plt.subplots(figsize=(10, 8))
                    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', fmt=".2f", linewidths=.5, ax=ax_heatmap)
                    ax_heatmap.set_title('Heatmap de Correlação')
                    plt.tight_layout()
                    st.pyplot(fig_heatmap)
                    plt.close(fig_heatmap)
                else:
                    st.info("Não há variáveis numéricas suficientes para um heatmap de correlação.")

                st.markdown("---")
                st.write("#### Count Plot: Contagem de Produtos por Categoria")
                if 'Categoria' in df_filtrado.columns:
                    fig_countplot, ax_countplot = plt.subplots(figsize=(12, 7))
                    sns.countplot(y='Categoria', data=df_filtrado, ax=ax_countplot, palette="Spectral", order = df_filtrado['Categoria'].value_counts().index)
                    ax_countplot.set_title('Contagem de Produtos por Categoria')
                    ax_countplot.set_xlabel('Contagem')
                    ax_countplot.set_ylabel('Categoria')
                    plt.tight_layout()
                    st.pyplot(fig_countplot)
                    plt.close(fig_countplot)
                else:
                    st.info("Coluna 'Categoria' não disponível para Count Plot.")

                st.markdown("---")
                st.write("#### Joint Plot: Avaliação vs. Contagem de Avaliações")
                if 'Avaliação' in df_filtrado.columns and 'Contagem de Avaliações' in df_filtrado.columns and df_filtrado['Avaliação'].notna().any() and df_filtrado['Contagem de Avaliações'].notna().any():
                    # Jointplot é um pouco diferente, ele cria sua própria figura
                    joint_fig = sns.jointplot(x='Avaliação', y='Contagem de Avaliações', data=df_filtrado.dropna(subset=['Avaliação', 'Contagem de Avaliações']), kind='scatter', color='skyblue', marginal_kws=dict(bins=15, fill=True))
                    joint_fig.fig.suptitle('Relação entre Avaliação e Contagem de Avaliações (com Distribuições Marginais)', y=1.02) # Ajustar título
                    st.pyplot(joint_fig.fig) # Passar a figura do jointplot
                    plt.close(joint_fig.fig)
                else:
                    st.info("Colunas 'Avaliação' ou 'Contagem de Avaliações' não disponíveis ou sem dados para Joint Plot.")
            else:
                st.info("Selecione filtros para visualizar os gráficos.")

        with tab_3d:
            st.subheader("Visualizações 3D Interativas")
            if not df_filtrado.empty:
                st.markdown("---")
                st.write("#### Gráfico de Dispersão 3D: Valor, Avaliação e Contagem de Avaliações")

                # Certificar que as colunas existem e têm dados válidos
                cols_3d = ['Valor', 'Avaliação', 'Contagem de Avaliações']
                if all(col in df_filtrado.columns for col in cols_3d) and \
                   all(df_filtrado[col].notna().any() for col in cols_3d):
                    
                    df_3d_scatter = df_filtrado.dropna(subset=cols_3d)
                    
                    fig_3d_scatter = px.scatter_3d(df_3d_scatter, 
                                                   x='Avaliação', y='Contagem de Avaliações', z='Valor',
                                                   color='Categoria', # Opcional: colorir por categoria
                                                   title="Relação 3D: Avaliação, Contagem e Valor",
                                                   labels={'Avaliação': 'Avaliação Média', 'Contagem de Avaliações': 'Nº de Avaliações', 'Valor': 'Preço ($)'})
                    st.plotly_chart(fig_3d_scatter, use_container_width=True)
                else:
                    st.info("Colunas 'Valor', 'Avaliação' ou 'Contagem de Avaliações' não disponíveis ou sem dados suficientes para o gráfico 3D.")
            else:
                st.info("Selecione filtros para visualizar os gráficos.")

        with tab_dados_detalhados:
            st.subheader("Dados Detalhados Filtrados 📄")
            user_can_see_details = st.session_state.get("user_permissions", {}).get("can_see_details", False)
            if st.session_state.get("user_role") == "gerente": # Gerente sempre pode ver
                user_can_see_details = True

            if user_can_see_details:
                colunas_para_mostrar_tabela = ['Nome do Produto', 'Categoria', 'Valor', 'Avaliação', 'Contagem de Avaliações', 'Percentual de Desconto']
                outras_colunas_csv = ['actual_price'] # Adicionar outras se desejar
                for col_csv in outras_colunas_csv:
                    if col_csv in df_filtrado.columns: # Verifica se a coluna original existe antes de tentar adicionar
                        colunas_para_mostrar_tabela.append(col_csv)
                
                colunas_existentes_na_tabela = [col for col in colunas_para_mostrar_tabela if col in df_filtrado.columns]
                if colunas_existentes_na_tabela:
                    st.dataframe(df_filtrado[colunas_existentes_na_tabela], height=400, use_container_width=True)
                else:
                    st.dataframe(df_filtrado, height=400, use_container_width=True)
            else:
                st.info("Você não tem permissão para visualizar os dados detalhados.")

    else:
        st.error("⚠️ Não foi possível carregar os dados. Verifique o arquivo 'vendas.csv' e tente novamente.")
        st.info("Certifique-se de que o arquivo 'vendas.csv' está na mesma pasta que o script 'sla.py' e que contém as colunas 'category', 'discounted_price' e 'product_name'.")

    # --- SEÇÃO ESPECÍFICA PARA GERENTES ---
    if st.session_state.get("user_role") == "gerente":
        # numpy as np já está importado globalmente
        st.sidebar.markdown("---")
        st.sidebar.subheader("Painel do Gerente")

        with st.sidebar.expander("Aprovar Registros Pendentes", expanded=False):
            if not st.session_state.pending_registrations:
                st.write("Nenhuma solicitação de registro pendente.")
            else:
                for user, pwd in list(st.session_state.pending_registrations.items()): # Usar list() para poder modificar o dict
                    col1, col2 = st.columns([3,1])
                    col1.text(f"Usuário: {user}")
                    if col2.button("Aprovar", key=f"approve_{user}"):
                        USUARIOS_FUNCIONARIOS[user] = {"password": pwd, "can_see_details": False, "active": True} # Padrão: não vê detalhes, ativo
                        del st.session_state.pending_registrations[user]
                        st.success(f"Usuário {user} aprovado!")
                        st.rerun()

        with st.sidebar.expander("Gerenciar Funcionários Ativos", expanded=False):
            if not USUARIOS_FUNCIONARIOS:
                st.write("Nenhum funcionário ativo.")
            else:
                for user, data in USUARIOS_FUNCIONARIOS.items():
                    st.markdown(f"**Usuário:** {user}")
                    
                    # Ativar/Desativar conta
                    is_active = data.get("active", False)
                    new_active_status = st.checkbox("Ativo", value=is_active, key=f"active_{user}")
                    if new_active_status != is_active:
                        USUARIOS_FUNCIONARIOS[user]["active"] = new_active_status
                        st.rerun()

                    # Permitir/Negar acesso a dados detalhados
                    can_see_details_perm = data.get("can_see_details", False)
                    new_detail_perm = st.checkbox("Permitir ver dados detalhados", value=can_see_details_perm, key=f"details_{user}")
                    if new_detail_perm != can_see_details_perm:
                        USUARIOS_FUNCIONARIOS[user]["can_see_details"] = new_detail_perm
                        st.rerun()
                    st.markdown("---")


# --- LÓGICA PRINCIPAL DO APLICATIVO ---
# Gerenciamento de qual página mostrar (login, registro, dashboard)
if "view" not in st.session_state:
    st.session_state.view = "Login" # Ajustar para corresponder às opções do menu

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_role"] = None
    st.session_state["username"] = None
    st.session_state["user_permissions"] = {}
    
if st.session_state["logged_in"]:
    exibir_dashboard_completo()
else:
    # Usar option_menu para navegação entre login e registro
    with st.sidebar: # Ou no corpo principal, como preferir
        st.session_state.view = option_menu(
            menu_title="Menu Principal",
            options=["Login", "Criar Conta"],
            icons=["box-arrow-in-right", "person-plus-fill"], # Ícones do Bootstrap
            menu_icon="cast",
            default_index=0,
        )
    if st.session_state.view == "Login":
        pagina_login()
    elif st.session_state.view == "Criar Conta":
        pagina_registro()
