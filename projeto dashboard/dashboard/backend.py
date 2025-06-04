import streamlit as st 
import pandas as pd
import os

# --- CONSTANTES PARA NOMES DE COLUNAS ---
# Nomes das colunas como estão no arquivo CSV original
CSV_CATEGORY = 'category'
CSV_DISCOUNTED_PRICE = 'discounted_price'
CSV_PRODUCT_NAME = 'product_name'
CSV_RATING = 'rating'
CSV_RATING_COUNT = 'rating_count'
CSV_ACTUAL_PRICE = 'actual_price'
CSV_DISCOUNT_PERCENTAGE = 'discount_percentage'

# Nomes das colunas como serão usadas no DataFrame do dashboard
COL_CATEGORIA = 'Categoria'
COL_NOME_PRODUTO = 'Nome do Produto'
COL_VALOR = 'Valor'
COL_AVALIACAO = 'Avaliação'
COL_CONTAGEM_AVALIACOES = 'Contagem de Avaliações'
COL_PERCENTUAL_DESCONTO = 'Percentual de Desconto'
COL_SENTIMENTO = 'Sentimento'
COL_PRECO = 'Preço Original'

# --- DADOS DE USUÁRIOS (exemplo)
USUARIOS_FUNCIONARIOS = {
    "func1": {"password": "senha123", "can_see_details": True, "active": True},
    "ana.vendas": {"password": "vendas234", "can_see_details": False, "active": True}
}

USUARIOS_GERENTES = {
    "admin": "admin",
    "boss": "boss1337"
}

# --- ANÁLISE Feedbacks ---
def classificar_sentimento(rating):

    if pd.isna(rating):
        return "Não Avaliado"
    elif rating >= 4.0:
        return "Positivo"
    elif rating >= 3.0:
        return "Neutro"
    elif rating < 3.0:
        return "Negativo"
    return "Não Avaliado"

# --- CARREGAMENTO E PREPARAÇÃO DOS DADOS ---
@st.cache_data
def carregar_dados(nome_arquivo_csv):
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        caminho_arquivo = os.path.join(script_dir, nome_arquivo_csv)
        df = pd.read_csv(caminho_arquivo)

        if df.empty:
            st.error(f"O arquivo '{caminho_arquivo}' está vazio.")
            return None

        colunas_csv_originais_necessarias = [
            CSV_CATEGORY,
            CSV_DISCOUNTED_PRICE,
            CSV_PRODUCT_NAME
        ]
        colunas_faltantes_csv = [col for col in colunas_csv_originais_necessarias if col not in df.columns]

        if colunas_faltantes_csv:
            st.error(f"As seguintes colunas essenciais do CSV não foram encontradas: {', '.join(colunas_faltantes_csv)}.")
            st.info(f"Colunas encontradas no arquivo CSV: {df.columns.tolist()}")
            return None

        df = df.rename(columns={
            CSV_CATEGORY: COL_CATEGORIA,
            CSV_PRODUCT_NAME: COL_NOME_PRODUTO,
            CSV_DISCOUNTED_PRICE: COL_VALOR,
            CSV_RATING: COL_AVALIACAO,
            CSV_RATING_COUNT: COL_CONTAGEM_AVALIACOES,
            CSV_DISCOUNT_PERCENTAGE: COL_PERCENTUAL_DESCONTO,
            CSV_ACTUAL_PRICE: COL_PRECO
        })

        if COL_VALOR in df.columns:
            df[COL_VALOR] = df[COL_VALOR].astype(str).str.replace('₹', '', regex=False).str.replace(',', '', regex=False)
            df[COL_VALOR] = pd.to_numeric(df[COL_VALOR], errors='coerce')
            df.dropna(subset=[COL_VALOR], inplace=True)
        else:
            st.error(f"Coluna '{COL_VALOR}' (mapeada de '{CSV_DISCOUNTED_PRICE}') não encontrada.")
            return None

        if COL_PRECO in df.columns:
            df[COL_PRECO] = df[COL_PRECO].astype(str).str.replace('₹', '', regex=False).str.replace(',', '', regex=False)
            df[COL_PRECO] = pd.to_numeric(df[COL_PRECO], errors='coerce')

        if COL_AVALIACAO in df.columns:
            df[COL_AVALIACAO] = df[COL_AVALIACAO].astype(str).str.extract(r'(\d+\.?\d*)').astype(float)
            df[COL_SENTIMENTO] = df[COL_AVALIACAO].apply(classificar_sentimento)

        if COL_CONTAGEM_AVALIACOES in df.columns:
            df[COL_CONTAGEM_AVALIACOES] = df[COL_CONTAGEM_AVALIACOES].astype(str).str.replace(',', '', regex=False)
            df[COL_CONTAGEM_AVALIACOES] = pd.to_numeric(df[COL_CONTAGEM_AVALIACOES], errors='coerce')

        if COL_PERCENTUAL_DESCONTO in df.columns:
            df[COL_PERCENTUAL_DESCONTO] = df[COL_PERCENTUAL_DESCONTO].astype(str).str.replace('%', '', regex=False)
            df[COL_PERCENTUAL_DESCONTO] = pd.to_numeric(df[COL_PERCENTUAL_DESCONTO], errors='coerce')

        if COL_CATEGORIA in df.columns:
            df[COL_CATEGORIA] = df[COL_CATEGORIA].astype(str).str.split('|').str[0]
        else:
            st.error(f"Coluna '{COL_CATEGORIA}' (mapeada de '{CSV_CATEGORY}') não encontrada.")
            return None
        
        if COL_NOME_PRODUTO not in df.columns:
            st.error(f"Coluna '{COL_NOME_PRODUTO}' (mapeada de '{CSV_PRODUCT_NAME}') não encontrada.")
            return None
            
        return df
        
    except FileNotFoundError:
        st.error(f"ARQUIVO NÃO ENCONTRADO: '{caminho_arquivo}'.")
        return None
    except pd.errors.ParserError:
        st.error(f"Erro ao analisar o arquivo CSV '{caminho_arquivo}'.")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao carregar os dados de '{caminho_arquivo}': {e}")
        return None

# --- FUNÇÕES DE LOGIN ---
def verificar_login(username, password):
    
    if username in USUARIOS_FUNCIONARIOS:
        user_data = USUARIOS_FUNCIONARIOS[username]
        if user_data["password"] == password and user_data.get("active", False):
            return "funcionario"
    if username in USUARIOS_GERENTES and USUARIOS_GERENTES[username] == password:
        return "gerente"
    return None
