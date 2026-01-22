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
    
    if not st.session_state.itens_orcamento.empty:
        df_calc = st.session_state.itens_orcamento
        subtotal = (pd.to_numeric(df_calc["Quantidade"]) * pd.to_numeric(df_calc["Preço Unitário"])).sum()
        total_final = subtotal * (1 + iva/100)
        st.markdown(f"#### **Total: {total_final:,.2f} €**")
    else:
        st.info("Adicione itens.")

# --------------------------------------------------
# 4. PESQUISA (QUANTIDADE MANUAL)
# --------------------------------------------------
st.divider()
tab1, tab2 = st.tabs(["🔍 Pesquisar Artigos", "➕ Item Extra"])

with tab1:
    pesquisa = st.text_input("Pesquisar por nome ou código:")
    if pesquisa:
        mask = (st.session_state.base_dados["DESCRIÇÃO"].str.contains(pesquisa, case=False, na=False)) | \
               (st.session_state.base_dados["CÓDIGO"].str.contains(pesquisa, case=False, na=False))
        resultados = st.session_state.base_dados[mask].head(15)
        
        if not resultados.empty:
            h1, h2, h3, h4, h5 = st.columns([1, 3, 1, 1, 0.5])
            h1.caption("**Cód**")
            h2.caption("**Descrição**")
            h3.caption("**Preço**")
            h4.caption("**Qtd (Manual)**")
            h5.caption("**Add**")
            
            for i, row in resultados.iterrows():
                with st.container():
                    c1, c2, c3, c4, c5 = st.columns([1, 3, 1, 1, 0.5])
                    c1.write(row["CÓDIGO"])
                    c2.write(row["DESCRIÇÃO"])
                    c3.write(f"{row['Preço Unitário']:.2f}€")
                    
                    # Quantidade agora é campo de texto para introdução rápida manual
                    qtd_manual = c4.text_input("qtd", key=f"q_{row['CÓDIGO']}", label_visibility="collapsed")
                    
                    if c5.button("➕", key=f"b_{row['CÓDIGO']}"):
                        try:
                            v_qtd = float(qtd_manual.replace(',', '.'))
                            if v_qtd > 0:
                                novo = pd.DataFrame([{"CÓDIGO": row["CÓDIGO"], "Artigo": row["DESCRIÇÃO"], "UNID": row["UNID"], "Preço Unitário": row["Preço Unitário"], "Quantidade": v_qtd}])
                                st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo], ignore_index=True)
                                st.rerun()
                        except:
                            st.error("Qtd Inválida")

with tab2:
    # Lógica de item extra (manual) permanece para flexibilidade
    e1, e2, e3, e4 = st.columns([2, 1, 1, 1])
    desc_ex = e1.text_input("Descrição do Item Extra")
    preco_ex = e2.number_input("Preço Unit.", min_value=0.0)
    qtd_ex = e3.text_input("Qtd Extra")
    if e4.button("Adicionar Extra", use_container_width=True):
        if desc_ex and qtd_ex:
            novo_ex = pd.DataFrame([{"CÓDIGO": "EXTRA", "Artigo": desc_ex, "UNID": "un", "Preço Unitário": preco_ex, "Quantidade": float(qtd_ex.replace(',','.'))}])
            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo_ex], ignore_index=True)
            st.rerun()

# --------------------------------------------------
# 5. ITENS APURADOS (COR DIFERENTE AO ALTERAR)
# --------------------------------------------------
st.divider()
st.subheader("📝 2. Itens Apurados (Edição de Valores)")

if not st.session_state.itens_orcamento.empty:
    st.info("Dica: Ao alterar o Preço ou Qtd, a célula muda de cor. Clique no botão 'Atualizar' para confirmar.")
    
    # O data_editor destaca visualmente as alterações feitas
    df_editado = st.data_editor(
        st.session_state.itens_orcamento,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="editor_apurados",
        column_config={
            "CÓDIGO": st.column_config.TextColumn("Cód", disabled=True),
            "Artigo": st.column_config.TextColumn("Descrição", width="large", disabled=True),
            "Preço Unitário": st.column_config.NumberColumn("V. Unit (€)", format="%.2f", min_value=0.0),
            "Quantidade": st.column_config.NumberColumn("Qtd", format="%.2f", min_value=0.0)
        }
    )
    
    if st.button("💾 Atualizar Totais e Gravar Alterações"):
        st.session_state.itens_orcamento = df_editado
        st.rerun()
else:
    st.write("Orçamento vazio.")

# --------------------------------------------------
# 6. SIDEBAR
# --------------------------------------------------
with st.sidebar:
    if st.button("🗑️ Limpar Tudo"):
        st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])
        st.rerun()
