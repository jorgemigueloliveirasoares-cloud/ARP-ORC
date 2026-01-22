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
# 3. INTERFACE SUPERIOR (DADOS E RESUMO)
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
        # Garantir que os cálculos usam os valores editados
        df_calc = st.session_state.itens_orcamento
        subtotal = (df_calc["Quantidade"] * df_calc["Preço Unitário"]).sum()
        total_iva = subtotal * (iva/100)
        total_final = subtotal + total_iva
        st.markdown(f"#### **Total: {total_final:,.2f} €**")
        st.caption(f"Subtotal: {subtotal:,.2f} € | IVA: {total_iva:,.2f} €")
    else:
        st.info("Adicione itens.")

# --------------------------------------------------
# 4. PESQUISA E ADIÇÃO MANUAL
# --------------------------------------------------
st.divider()
tab1, tab2 = st.tabs(["🔍 Pesquisar na Tabela", "➕ Adicionar Artigo Extra (Manual)"])

with tab1:
    pesquisa = st.text_input("Digite o termo de pesquisa (picar, pintura, código...):")
    if pesquisa:
        mask = (st.session_state.base_dados["DESCRIÇÃO"].str.contains(pesquisa, case=False, na=False)) | \
               (st.session_state.base_dados["CÓDIGO"].str.contains(pesquisa, case=False, na=False))
        resultados = st.session_state.base_dados[mask].head(15)
        
        if not resultados.empty:
            h1, h2, h3, h4, h5 = st.columns([1, 3, 1, 1, 0.5])
            h1.caption("**Cód**")
            h2.caption("**Descrição**")
            h3.caption("**V. Unit**")
            h4.caption("**Quantidade**")
            h5.caption("**Add**")
            
            for i, row in resultados.iterrows():
                with st.container():
                    c1, c2, c3, c4, c5 = st.columns([1, 3, 1, 1, 0.5])
                    c1.write(row["CÓDIGO"])
                    c2.write(row["DESCRIÇÃO"])
                    c3.write(f"{row['Preço Unitário']:.2f} €")
                    qtd = c4.number_input("Qtd", min_value=0.0, step=1.0, key=f"q_{row['CÓDIGO']}", label_visibility="collapsed")
                    if c5.button("➕", key=f"b_{row['CÓDIGO']}"):
                        if qtd > 0:
                            novo = pd.DataFrame([{"CÓDIGO": row["CÓDIGO"], "Artigo": row["DESCRIÇÃO"], "UNID": row["UNID"], "Preço Unitário": row["Preço Unitário"], "Quantidade": qtd}])
                            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo], ignore_index=True)
                            st.rerun()

with tab2:
    st.write("Utilize esta secção para itens que não existem na tabela de preços.")
    m1, m2, m3 = st.columns([1, 3, 1])
    m_cod = m1.text_input("Código Novo", value="EXTRA")
    m_desc = m2.text_input("Descrição do Artigo/Serviço")
    m_unid = m3.text_input("Unidade", value="un")
    
    m4, m5, m6 = st.columns([1, 1, 1])
    m_preco = m4.number_input("Preço Unitário (€)", min_value=0.0, step=0.5)
    m_qtd = m5.number_input("Quantidade", min_value=0.1, step=1.0)
    
    if m6.button("➕ Adicionar Artigo Especial", use_container_width=True):
        if m_desc:
            novo_extra = pd.DataFrame([{"CÓDIGO": m_cod, "Artigo": m_desc, "UNID": m_unid, "Preço Unitário": m_preco, "Quantidade": m_qtd}])
            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo_extra], ignore_index=True)
            st.rerun()
        else:
            st.warning("Preencha a descrição do artigo.")

# --------------------------------------------------
# 5. ITENS APURADOS (EDIÇÃO TOTAL HABILITADA)
# --------------------------------------------------
st.divider()
st.subheader("📝 2. Itens Apurados (Pode alterar preços e quantidades aqui)")

if not st.session_state.itens_orcamento.empty:
    # AQUI ESTÁ A CHAVE: Coluna 'Preço Unitário' e 'Quantidade' estão editáveis
    df_editado = st.data_editor(
        st.session_state.itens_orcamento,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="editor_final",
        column_config={
            "CÓDIGO": st.column_config.TextColumn("Cód", disabled=True),
            "Artigo": st.column_config.TextColumn("Descrição", width="large"), # Editável se quiser mudar o nome
            "Preço Unitário": st.column_config.NumberColumn("V. Unit (€)", format="%.2f", min_value=0.0),
            "Quantidade": st.column_config.NumberColumn("Qtd", format="%.2f", min_value=0.0)
        }
    )
    
    # Atualiza os dados na sessão sempre que houver alterações
    if st.button("💾 Validar/Atualizar Cálculos"):
        st.session_state.itens_orcamento = df_editado
        st.rerun()
else:
    st.info("O orçamento está vazio.")

# --------------------------------------------------
# 6. EXPORTAÇÃO (PDF E EXCEL)
# --------------------------------------------------
if not st.session_state.itens_orcamento.empty:
    st.divider()
    c_pdf, c_xls, c_clear = st.columns(3)
    
    with c_pdf:
        # Lógica simplificada de PDF (pode expandir com a sua anterior)
        if st.button("📥 Baixar PDF"):
            st.write("Gerando PDF...") # Integra aqui a função reportlab anterior
            
    with c_xls:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            st.session_state.itens_orcamento.to_excel(writer, index=False)
        st.download_button("📥 Baixar Excel", output.getvalue(), "orcamento.xlsx")

    with c_clear:
        if st.button("🗑️ Limpar Tudo"):
            st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])
            st.rerun()
