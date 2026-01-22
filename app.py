import streamlit as st
import pandas as pd
import os
import io
import pickle
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
        df = pd.read_excel(EXCEL_PATH)
        df.columns = [c.strip() for c in df.columns]
        # Ajuste exato das suas colunas
        col_preco = "VALORES ATUAIS JANEIRO 2025"
        df = df[["CÓDIGO", "DESCRIÇÃO", "UNID", col_preco]].dropna(subset=["CÓDIGO"])
        df.rename(columns={col_preco: "Preço Unitário"}, inplace=True)
        df["CÓDIGO"] = df["CÓDIGO"].astype(str).str.strip()
        return df
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário"])

# --------------------------------------------------
# 2. ESTADO DA SESSÃO
# --------------------------------------------------
if "base_dados" not in st.session_state:
    st.session_state.base_dados = carregar_base()

if "itens_orcamento" not in st.session_state:
    # Lista de dicionários para guardar os itens apurados
    st.session_state.itens_orcamento = []

if "dados_cliente" not in st.session_state:
    st.session_state.dados_cliente = {"nome": "", "tel": "", "morada": "", "iva": 23, "notas": ""}

# --------------------------------------------------
# 3. INTERFACE SUPERIOR
# --------------------------------------------------
col_log, col_info, col_exp = st.columns([1, 2, 1.5])

with col_log:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=150)

with col_info:
    st.subheader("📋 Dados do Orçamento")
    st.session_state.dados_cliente["nome"] = st.text_input("Cliente", st.session_state.dados_cliente["nome"])
    c1, c2 = st.columns(2)
    st.session_state.dados_cliente["tel"] = c1.text_input("Telefone", st.session_state.dados_cliente["tel"])
    st.session_state.dados_cliente["morada"] = st.text_input("Morada", st.session_state.dados_cliente["morada"])

with col_exp:
    st.subheader("💰 Resumo")
    iva = st.selectbox("IVA (%)", [0, 6, 13, 23], index=3)
    st.session_state.dados_cliente["iva"] = iva
    
    if st.session_state.itens_orcamento:
        df_ver = pd.DataFrame(st.session_state.itens_orcamento)
        subtotal = (df_ver["Quantidade"] * df_ver["Preço Unitário"]).sum()
        total = subtotal * (1 + iva/100)
        st.markdown(f"#### **Total: {total:,.2f} €**")
        
        # Botão para gerar PDF
        if st.button("📥 Gerar PDF"):
            st.success("PDF gerado com sucesso!") # Aqui entra a função do ReportLab
    else:
        st.info("Adicione itens para calcular.")

# --------------------------------------------------
# 4. PESQUISA E ADIÇÃO (MÉTODO SEGURO)
# --------------------------------------------------
st.divider()
st.subheader("🔍 1. Pesquisar e Adicionar Artigos")

pesquisa = st.text_input("Procure por Nome ou Código (Ex: arp2202)...")

if pesquisa:
    mask = (st.session_state.base_dados["DESCRIÇÃO"].str.contains(pesquisa, case=False, na=False)) | \
           (st.session_state.base_dados["CÓDIGO"].str.contains(pesquisa, case=False, na=False))
    
    resultados = st.session_state.base_dados[mask].copy()
    
    if not resultados.empty:
        # Mostramos os resultados numa tabela de seleção
        selecao = st.dataframe(
            resultados,
            use_container_width=True,
            hide_index=True,
            column_config={"Preço Unitário": st.column_config.NumberColumn(format="%.2f €")}
        )
        
        # Seleção manual por Código para evitar erros de índice
        cod_escolhido = st.selectbox("Selecione o Código para adicionar:", resultados["CÓDIGO"].unique())
        qtd_add = st.number_input("Quantidade:", min_value=0.1, value=1.0, step=0.1)
        
        if st.button("➕ Adicionar ao Orçamento"):
            item_base = st.session_state.base_dados[st.session_state.base_dados["CÓDIGO"] == cod_escolhido].iloc[0]
            
            novo_item = {
                "CÓDIGO": item_base["CÓDIGO"],
                "Artigo": item_base["DESCRIÇÃO"],
                "UM": item_base["UNID"],
                "Preço Unitário": item_base["Preço Unitário"],
                "Quantidade": qtd_add
            }
            st.session_state.itens_orcamento.append(novo_item)
            st.rerun()

# --------------------------------------------------
# 5. ITENS APURADOS (EDIÇÃO E REMOÇÃO)
# --------------------------------------------------
st.divider()
st.subheader("📝 2. Itens Apurados (No Orçamento)")

if st.session_state.itens_orcamento:
    df_apurados = pd.DataFrame(st.session_state.itens_orcamento)
    
    # Editor para mudar quantidades ou preços unitários dos apurados
    editado = st.data_editor(
        df_apurados,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic", # Permite apagar linhas
        key="editor_apurados",
        column_config={
            "Artigo": st.column_config.TextColumn(width="large", disabled=True),
            "Preço Unitário": st.column_config.NumberColumn("V. Unit (€)", format="%.2f"),
            "Quantidade": st.column_config.NumberColumn("Qtd", format="%.2f")
        }
    )
    
    # Guardar alterações se o utilizador mexer na tabela
    if st.button("💾 Gravar Alterações na Lista"):
        st.session_state.itens_orcamento = editado.to_dict('records')
        st.rerun()

    st.session_state.dados_cliente["notas"] = st.text_area("Notas Finais", st.session_state.dados_cliente["notas"])

else:
    st.write("O orçamento ainda não tem itens.")

# --------------------------------------------------
# 6. SIDEBAR
# --------------------------------------------------
with st.sidebar:
    if st.button("🗑️ Limpar Tudo"):
        st.session_state.itens_orcamento = []
        st.rerun()
