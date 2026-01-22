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
# 3. INTERFACE SUPERIOR (DADOS CLIENTE E TOTAL)
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
    st.subheader("💰 Resumo")
    iva = st.selectbox("IVA (%)", [0, 6, 13, 23], index=3)
    
    if not st.session_state.itens_orcamento.empty:
        df_calc = st.session_state.itens_orcamento
        subtotal = (df_calc["Quantidade"] * df_calc["Preço Unitário"]).sum()
        total = subtotal * (1 + iva/100)
        st.markdown(f"#### **Total: {total:,.2f} €**")
    else:
        st.info("Adicione itens.")

# --------------------------------------------------
# 4. PESQUISA "USER FRIENDLY" (BOTÃO POR LINHA)
# --------------------------------------------------
st.divider()
st.subheader("🔍 1. Pesquisar e Adicionar Artigos")

pesquisa = st.text_input("Digite o termo de pesquisa (ex: picar, arp, etc):")

if pesquisa:
    mask = (st.session_state.base_dados["DESCRIÇÃO"].str.contains(pesquisa, case=False, na=False)) | \
           (st.session_state.base_dados["CÓDIGO"].str.contains(pesquisa, case=False, na=False))
    
    resultados = st.session_state.base_dados[mask].head(20) # Limite para performance
    
    if not resultados.empty:
        # Cabeçalho da lista de pesquisa
        h1, h2, h3, h4, h5 = st.columns([1, 3, 1, 1, 0.5])
        h1.caption("**Cód**")
        h2.caption("**Descrição**")
        h3.caption("**Preço Unit.**")
        h4.caption("**Quantidade**")
        h5.caption("**Add**")
        
        for i, row in resultados.iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([1, 3, 1, 1, 0.5])
                
                c1.write(row["CÓDIGO"])
                c2.write(row["DESCRIÇÃO"])
                c3.write(f"{row['Preço Unitário']:.2f} €")
                
                # Input de quantidade único para cada linha
                qtd = c4.number_input("Qtd", min_value=0.0, value=0.0, step=1.0, key=f"qtd_{row['CÓDIGO']}", label_visibility="collapsed")
                
                # Botão Mais (+) para adicionar
                if c5.button("➕", key=f"btn_{row['CÓDIGO']}"):
                    if qtd > 0:
                        novo_item = pd.DataFrame([{
                            "CÓDIGO": row["CÓDIGO"],
                            "Artigo": row["DESCRIÇÃO"],
                            "UNID": row["UNID"],
                            "Preço Unitário": row["Preço Unitário"],
                            "Quantidade": qtd
                        }])
                        st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo_item], ignore_index=True)
                        st.success(f"Adicionado: {row['CÓDIGO']}")
                        st.rerun()
                    else:
                        st.error("Insira Qtd > 0")
    else:
        st.warning("Nenhum item encontrado.")

# --------------------------------------------------
# 5. ITENS APURADOS (TABELA FINAL)
# --------------------------------------------------
st.divider()
st.subheader("📝 2. Itens Apurados (No Orçamento)")

if not st.session_state.itens_orcamento.empty:
    df_editado = st.data_editor(
        st.session_state.itens_orcamento,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="editor_final",
        column_config={
            "CÓDIGO": st.column_config.TextColumn("Cód", disabled=True),
            "Artigo": st.column_config.TextColumn("Descrição", width="large", disabled=True),
            "Preço Unitário": st.column_config.NumberColumn("V. Unit (€)", format="%.2f"),
            "Quantidade": st.column_config.NumberColumn("Qtd", format="%.2f")
        }
    )
    
    if st.button("💾 Guardar Alterações da Tabela"):
        st.session_state.itens_orcamento = df_editado
        st.rerun()
else:
    st.write("Pesquise e clique no ➕ para adicionar itens.")

# --------------------------------------------------
# 6. SIDEBAR (LIMPAR TUDO)
# --------------------------------------------------
with st.sidebar:
    if st.button("🗑️ Limpar Todo o Orçamento"):
        st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])
        st.rerun()
