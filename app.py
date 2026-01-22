import streamlit as st
import pandas as pd
import os
import io
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

# --------------------------------------------------
# 1. CONFIGURAÇÃO E DADOS
# --------------------------------------------------
st.set_page_config(page_title="Gestor de Orçamentos", layout="wide")

LOGO_PATH = "logo.png"
EXCEL_PATH = "Cópia de Preços Tabela atual.xlsx"

def carregar_base():
    if os.path.exists(EXCEL_PATH):
        try:
            df = pd.read_excel(EXCEL_PATH)
            df.columns = [c.strip() for c in df.columns]
            # Ajuste das colunas conforme o seu ficheiro
            col_preco = "VALORES ATUAIS JANEIRO 2025"
            df = df[["CÓDIGO", "DESCRIÇÃO", "UNID", col_preco]].dropna(subset=["CÓDIGO"])
            df.rename(columns={col_preco: "Preço Unitário"}, inplace=True)
            df["CÓDIGO"] = df["CÓDIGO"].astype(str).str.strip()
            return df
        except Exception as e:
            st.error(f"Erro ao ler Excel: {e}")
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário"])

# --------------------------------------------------
# 2. ESTADO DA SESSÃO
# --------------------------------------------------
if "base_dados" not in st.session_state:
    st.session_state.base_dados = carregar_base()

if "itens_orcamento" not in st.session_state:
    st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])

if "dados_cliente" not in st.session_state:
    st.session_state.dados_cliente = {"nome": "", "tel": "", "morada": "", "iva": 23}

# --------------------------------------------------
# 3. INTERFACE SUPERIOR
# --------------------------------------------------
col_log, col_info, col_exp = st.columns([1, 2, 1.5])

with col_log:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=150)

with col_info:
    st.subheader("📋 Dados do Cliente")
    st.session_state.dados_cliente["nome"] = st.text_input("Cliente", st.session_state.dados_cliente["nome"])
    c1, c2 = st.columns(2)
    st.session_state.dados_cliente["tel"] = c1.text_input("Telefone", st.session_state.dados_cliente["tel"])
    st.session_state.dados_cliente["morada"] = st.text_input("Morada", st.session_state.dados_cliente["morada"])

with col_exp:
    st.subheader("💰 Resumo Financeiro")
    iva = st.selectbox("IVA (%)", [0, 6, 13, 23], index=3)
    
    if not st.session_state.itens_orcamento.empty:
        df_calc = st.session_state.itens_orcamento
        subtotal = (df_calc["Quantidade"] * df_calc["Preço Unitário"]).sum()
        total = subtotal * (1 + iva/100)
        st.markdown(f"#### **Total Orçado: {total:,.2f} €**")
        st.caption(f"Subtotal: {subtotal:,.2f} € | IVA: {iva}%")
    else:
        st.info("Adicione itens para calcular o total.")

# --------------------------------------------------
# 4. PESQUISA E ADIÇÃO (QUANTIDADE VAI A ZERO)
# --------------------------------------------------
st.divider()
st.subheader("🔍 1. Pesquisar e Selecionar Artigos")

pesquisa = st.text_input("Procure por Nome ou Código...")

if pesquisa:
    mask = (st.session_state.base_dados["DESCRIÇÃO"].str.contains(pesquisa, case=False, na=False)) | \
           (st.session_state.base_dados["CÓDIGO"].str.contains(pesquisa, case=False, na=False))
    
    resultados = st.session_state.base_dados[mask].copy()
    
    if not resultados.empty:
        st.dataframe(resultados, use_container_width=True, hide_index=True)
        
        # Menu para escolher o item exato
        escolha = st.selectbox("Selecione o item para adicionar à lista abaixo:", 
                                resultados["CÓDIGO"] + " - " + resultados["DESCRIÇÃO"])
        
        if st.button("➕ Adicionar ao Orçamento"):
            cod_id = escolha.split(" - ")[0]
            item_base = st.session_state.base_dados[st.session_state.base_dados["CÓDIGO"] == cod_id].iloc[0]
            
            # CRIAR NOVO ITEM COM QUANTIDADE 0.00
            novo_item = pd.DataFrame([{
                "CÓDIGO": item_base["CÓDIGO"],
                "Artigo": item_base["DESCRIÇÃO"],
                "UNID": item_base["UNID"],
                "Preço Unitário": item_base["Preço Unitário"],
                "Quantidade": 0.00  # <--- Definido como zero como pretendido
            }])
            
            # Adicionar à lista de apurados
            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo_item], ignore_index=True)
            st.rerun()

# --------------------------------------------------
# 5. ITENS APURADOS (ONDE SE COLOCA A QUANTIDADE)
# --------------------------------------------------
st.divider()
st.subheader("📝 2. Itens Apurados (Insira as Quantidades)")

if not st.session_state.itens_orcamento.empty:
    # O utilizador edita diretamente a quantidade aqui
    df_editado = st.data_editor(
        st.session_state.itens_orcamento,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="editor_final",
        column_config={
            "CÓDIGO": st.column_config.TextColumn("Cód", disabled=True),
            "Artigo": st.column_config.TextColumn("Descrição", width="large", disabled=True),
            "UNID": st.column_config.TextColumn("UM", disabled=True),
            "Preço Unitário": st.column_config.NumberColumn("Preço (€)", format="%.2f"),
            "Quantidade": st.column_config.NumberColumn("Qtd (Coloque aqui)", min_value=0.0, format="%.2f", required=True)
        }
    )
    
    # Atualizar o estado global com os valores inseridos
    if st.button("💾 Validar Quantidades e Totais"):
        st.session_state.itens_orcamento = df_editado
        st.rerun()
else:
    st.warning("Pesquise e adicione itens acima para que apareçam aqui.")
