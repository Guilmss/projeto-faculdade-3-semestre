import streamlit as st 
import pandas as pd
import sqlite3
import os

# --- CONSTANTES PARA NOMES DE COLUNAS ---
CSV_CATEGORY = 'category'
CSV_DISCOUNTED_PRICE = 'discounted_price'
CSV_PRODUCT_NAME = 'product_name'
CSV_RATING = 'rating'
CSV_RATING_COUNT = 'rating_count'
CSV_ACTUAL_PRICE = 'actual_price'
CSV_DISCOUNT_PERCENTAGE = 'discount_percentage'

COL_CATEGORIA = 'Categoria'
COL_NOME_PRODUTO = 'Nome do Produto'
COL_VALOR = 'Valor'
COL_AVALIACAO = 'Avaliação'
COL_CONTAGEM_AVALIACOES = 'Contagem de Avaliações'
COL_PERCENTUAL_DESCONTO = 'Percentual de Desconto'
COL_SENTIMENTO = 'Sentimento'
COL_PRECO = 'Preço Original'

# --- CONSTANTES PARA SQLITE ---
NOME_BANCO_SQLITE = "vendas_db.sqlite"
NOME_TABELA_VENDAS = "vendas"


# --- DADOS DE USUÁRIOS ---
# claro, como exemplo esse são os logins e senhas de exemplo, em funcionamento real deve-se usar um sistema de banco de dados seguro.
USUARIOS_FUNCIONARIOS = {
    "func1": {"password": "senha123", "can_see_details": True, "active": True},
    "ana.vendas": {"password": "vendas234", "can_see_details": False, "active": True}
}
# esse são os logins de gerentes com acesso para editar funções dos funcionarios.
USUARIOS_GERENTES = {
    "admin": "admin",
    "boss": "boss1337"
}

# --- FUNÇÕES DE SENTIMENTO ---
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

# --- PROCESSAMENTO DE DADOS DO CSV ---
def _limpar_e_transformar_df_vendas_csv(df_csv):

    messages = []
    if df_csv.empty:
        messages.append({'type': 'error', 'text': "O arquivo CSV fornecido para limpeza está vazio."})
        return None, messages

    colunas_csv_originais_necessarias = [
        CSV_CATEGORY, CSV_DISCOUNTED_PRICE, CSV_PRODUCT_NAME
    ]
    colunas_faltantes_csv = [col for col in colunas_csv_originais_necessarias if col not in df_csv.columns]

    if colunas_faltantes_csv:
        messages.append({'type': 'error', 'text': f"CSV: As seguintes colunas essenciais não foram encontradas: {', '.join(colunas_faltantes_csv)}."})
        messages.append({'type': 'info', 'text': f"Colunas encontradas no arquivo CSV: {df_csv.columns.tolist()}"})
        return None, messages

    df_limpo = df_csv.rename(columns={
        CSV_CATEGORY: COL_CATEGORIA,
        CSV_PRODUCT_NAME: COL_NOME_PRODUTO,
        CSV_DISCOUNTED_PRICE: COL_VALOR,
        CSV_RATING: COL_AVALIACAO,
        CSV_RATING_COUNT: COL_CONTAGEM_AVALIACOES,
        CSV_DISCOUNT_PERCENTAGE: COL_PERCENTUAL_DESCONTO,
        CSV_ACTUAL_PRICE: COL_PRECO
    })

    if COL_VALOR in df_limpo.columns:
        df_limpo[COL_VALOR] = df_limpo[COL_VALOR].astype(str).str.replace('₹', '', regex=False).str.replace(',', '', regex=False)
        df_limpo[COL_VALOR] = pd.to_numeric(df_limpo[COL_VALOR], errors='coerce')
        df_limpo.dropna(subset=[COL_VALOR], inplace=True)
    else:
        messages.append({'type': 'error', 'text': f"Coluna '{COL_VALOR}' (mapeada de '{CSV_DISCOUNTED_PRICE}') não encontrada após renomear."})
        return None, messages

    if COL_PRECO in df_limpo.columns:
        df_limpo[COL_PRECO] = df_limpo[COL_PRECO].astype(str).str.replace('₹', '', regex=False).str.replace(',', '', regex=False)
        df_limpo[COL_PRECO] = pd.to_numeric(df_limpo[COL_PRECO], errors='coerce')

    if COL_AVALIACAO in df_limpo.columns:
        extracted_ratings = df_limpo[COL_AVALIACAO].astype(str).str.extract(r'(\d+\.?\d*)')
        if not extracted_ratings.empty and extracted_ratings.shape[1] > 0 and extracted_ratings.iloc[:, 0].notna().any():
            df_limpo[COL_AVALIACAO] = pd.to_numeric(extracted_ratings.iloc[:, 0], errors='coerce')
        else:
            df_limpo[COL_AVALIACAO] = pd.NA 
    else:
        df_limpo[COL_AVALIACAO] = pd.NA 

    df_limpo[COL_SENTIMENTO] = df_limpo[COL_AVALIACAO].apply(classificar_sentimento)

    if COL_CONTAGEM_AVALIACOES in df_limpo.columns:
        # Tratar possíveis valores não numéricos antes de remover vírgulas
        df_limpo[COL_CONTAGEM_AVALIACOES] = df_limpo[COL_CONTAGEM_AVALIACOES].apply(
            lambda x: str(x).replace(',', '') if pd.notnull(x) else x
        )
        df_limpo[COL_CONTAGEM_AVALIACOES] = pd.to_numeric(df_limpo[COL_CONTAGEM_AVALIACOES], errors='coerce')

    if COL_PERCENTUAL_DESCONTO in df_limpo.columns:
        df_limpo[COL_PERCENTUAL_DESCONTO] = df_limpo[COL_PERCENTUAL_DESCONTO].astype(str).str.replace('%', '', regex=False)
        df_limpo[COL_PERCENTUAL_DESCONTO] = pd.to_numeric(df_limpo[COL_PERCENTUAL_DESCONTO], errors='coerce')

    if COL_CATEGORIA in df_limpo.columns:
        df_limpo[COL_CATEGORIA] = df_limpo[COL_CATEGORIA].astype(str).str.split('|').str[0]
    else:
        messages.append({'type': 'error', 'text': f"Coluna '{COL_CATEGORIA}' (mapeada de '{CSV_CATEGORY}') não encontrada após renomear."})
        return None, messages
    
    if COL_NOME_PRODUTO not in df_limpo.columns:
        messages.append({'type': 'error', 'text': f"Coluna '{COL_NOME_PRODUTO}' (mapeada de '{CSV_PRODUCT_NAME}') não encontrada após renomear."})
        return None, messages
            
    return df_limpo, messages

# --- OPERAÇÕES SQLITE: SALVAR DATAFRAME ---
def _salvar_df_no_sqlite(df_para_salvar, conn_sqlite, nome_tabela):
    """Salva o DataFrame fornecido na tabela SQLite, substituindo-a."""
    messages = []
    try:
        if df_para_salvar is not None and not df_para_salvar.empty:
            df_para_salvar.to_sql(nome_tabela, conn_sqlite, if_exists='replace', index=False)
            messages.append({'type': 'toast', 'text': f"Dados salvos com sucesso na tabela '{nome_tabela}' do banco de dados!", 'icon': "✅"})
            return True, messages
        else:
            messages.append({'type': 'error', 'text': "DataFrame para salvar está vazio ou nulo. Banco de dados não atualizado."})
            return False, messages
    except Exception as e:
        messages.append({'type': 'error', 'text': f"Erro ao salvar DataFrame no SQLite: {e}"})
        return False, messages

# --- SINCRONIZAÇÃO: CSV PARA SQLITE ---
def processar_e_sincronizar_csv(caminho_arquivo_csv, nome_banco_sqlite=NOME_BANCO_SQLITE, nome_tabela=NOME_TABELA_VENDAS):
    """Lê um CSV de um caminho de arquivo, limpa e sincroniza com SQLite."""
    messages = []
    conn = None
    sucesso_geral = False
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        caminho_completo_csv = os.path.join(script_dir, caminho_arquivo_csv)
        df_csv_raw = pd.read_csv(caminho_completo_csv)
        messages.append({'type': 'info', 'text': f"Lendo CSV de: {caminho_completo_csv}"})

        df_limpo, transform_messages = _limpar_e_transformar_df_vendas_csv(df_csv_raw)
        messages.extend(transform_messages)

        if df_limpo is not None:
            conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), nome_banco_sqlite))
            sucesso_salvar, salvar_messages = _salvar_df_no_sqlite(df_limpo, conn, nome_tabela)
            messages.extend(salvar_messages)
            sucesso_geral = sucesso_salvar
        else:
            messages.append({'type': 'error', 'text': "Processamento do CSV falhou. Banco de dados não atualizado."})
            
    except FileNotFoundError:
        messages.append({'type': 'error', 'text': f"ARQUIVO CSV NÃO ENCONTRADO: '{caminho_completo_csv}'."})
    except pd.errors.ParserError:
        messages.append({'type': 'error', 'text': f"Erro ao analisar o arquivo CSV: '{caminho_completo_csv}'. Verifique o formato."})
    except Exception as e:
        messages.append({'type': 'error', 'text': f"Ocorreu um erro inesperado ao processar/sincronizar CSV: {e}"})
    finally:
        if conn:
            conn.close()
    return sucesso_geral, messages

# --- SINCRONIZAÇÃO: DATAFRAME EDITADO PARA SQLITE ---
def sincronizar_dataframe_editado(df_editado, nome_banco_sqlite=NOME_BANCO_SQLITE, nome_tabela=NOME_TABELA_VENDAS):
    messages = []
    conn = None
    sucesso_geral = False
    try:
        conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), nome_banco_sqlite))
        sucesso_salvar, salvar_messages = _salvar_df_no_sqlite(df_editado, conn, nome_tabela)
        messages.extend(salvar_messages)
        sucesso_geral = sucesso_salvar
    except Exception as e:
        messages.append({'type': 'error', 'text': f"Erro ao sincronizar DataFrame editado: {e}"})
    finally:
        if conn:
            conn.close()
    return sucesso_geral, messages

# --- CARREGAMENTO DE DADOS DO SQLITE ---
@st.cache_data
def carregar_dados():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    caminho_banco_sqlite = os.path.join(script_dir, NOME_BANCO_SQLITE)
    conn = None
    df_resultado = None
    messages_for_frontend = []

    try:
        conn = sqlite3.connect(caminho_banco_sqlite)
        cursor = conn.cursor()

        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{NOME_TABELA_VENDAS}'")
        table_exists = cursor.fetchone()

        if not table_exists:
            messages_for_frontend.append({'type': 'info', 'text': f"Tabela '{NOME_TABELA_VENDAS}' não encontrada. Tentando sincronização inicial com 'vendas.csv' padrão..."})
            if conn: conn.close(); conn = None
            sucesso_sinc_inicial, sync_messages = processar_e_sincronizar_csv("vendas.csv", caminho_banco_sqlite, NOME_TABELA_VENDAS)
            messages_for_frontend.extend(sync_messages)
            if not sucesso_sinc_inicial:
                return None, messages_for_frontend
            conn = sqlite3.connect(caminho_banco_sqlite)

        df_resultado = pd.read_sql_query(f"SELECT * FROM {NOME_TABELA_VENDAS}", conn)

        if df_resultado.empty:
            if not any(msg['type'] == 'error' for msg in messages_for_frontend):
                 messages_for_frontend.append({'type': 'warning', 'text': f"A tabela '{NOME_TABELA_VENDAS}' no banco de dados está vazia. Verifique o arquivo CSV e tente sincronizar novamente."})
            if table_exists and not any(msg['type'] == 'error' for msg in messages_for_frontend):
                 messages_for_frontend.append({'type': 'info', 'text': f"A tabela '{NOME_TABELA_VENDAS}' foi carregada, mas está vazia."})

        return df_resultado, messages_for_frontend

    except sqlite3.Error as e:
        messages_for_frontend.append({'type': 'error', 'text': f"Erro de SQLite ao acessar '{caminho_banco_sqlite}': {e}"})
        return None, messages_for_frontend
    except Exception as e:
        messages_for_frontend.append({'type': 'error', 'text': f"Ocorreu um erro inesperado ao carregar dados do banco SQLite: {e}"})
        return None, messages_for_frontend
    finally:
        if conn:
            conn.close()

# --- FUNÇÕES DE LOGIN ---
def verificar_login(username, password):
    
    if username in USUARIOS_FUNCIONARIOS:
        user_data = USUARIOS_FUNCIONARIOS[username]
        if user_data["password"] == password and user_data.get("active", False):
            return "funcionario"
    if username in USUARIOS_GERENTES and USUARIOS_GERENTES[username] == password:
        return "gerente"
    return None
