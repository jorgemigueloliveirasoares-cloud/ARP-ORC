import streamlit as st
import pandas as pd
import os
import io
from datetime import date

# 1. CONFIGURAÇÃO E CARREGAMENTO
st.set_page_config(page_title="Orçamentador Pro", layout="wide")

def carregar_base():
    caminho = "Cópia de Preços Tabela atual.xlsx"
    if os.path.exists(caminho):
        try:
            df = pd.read_excel(caminho)
            df.columns = [str(c).strip() for c in df.columns]
            col_preco = "VALORES ATUAIS JANEIRO 2025"
            df = df[["CÓDIGO", "DESCRIÇÃO", "UNID", col_preco]].dropna(subset=["CÓDIGO"])
            df.rename(columns={col_preco: "Preço Unitário"}, inplace=True)
            df["CÓDIGO"] = df["CÓDIGO"].astype(str).str.strip()
            df["DESCRIÇÃO"] = df["DESCRIÇÃO"].astype(str).str.strip()
            return df
        except: pass
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário"])

if "itens_orcamento" not in st.session_state:
    st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])

# 2. CABEÇALHO (Logo e Cliente)
col_log, col_cli, col_num = st.columns([1.2, 2.5, 1])
with col_log:
    if os.path.exists("logo.png"): st.image("logo.png", width=180)

with col_cli:
    st.markdown("### **Dados do Cliente**")
    nome_cli = st.text_input("Nome do Cliente")
    morada_cli = st.text_input("Morada")
    c1, c2 = st.columns(2)
    tel_cli = c1.text_input("Telefone")
    email_cli = c2.text_input("Email")

with col_num:
    st.markdown("### **Identificação**")
    n_orc = st.text_input("Nº Orçamento", value=f"ORC-{date.today().year}-{date.today().month:02d}-001")
    st.date_input("Data", date.today())

st.divider()

# 3. ADIÇÃO DE ITENS (Tabela vs Manual)
st.subheader("🔍 1. Adicionar Itens ao Orçamento")
tab_pesquisa, tab_manual = st.tabs(["🔎 Pesquisar no Excel", "➕ Criar Artigo Manual"])

with tab_pesquisa:
    termo = st.text_input("Procurar no Excel (nome ou código):", key="search").strip()
    if termo:
        base = carregar_base()
        mask = (base["DESCRIÇÃO"].str.contains(termo, case=False, na=False)) | (base["CÓDIGO"].str.contains(termo, case=False, na=False))
        resultados = base[mask].head(10)
        for i, row in resultados.iterrows():
            c1, c2, c3, c4, c5 = st.columns([1, 4, 1, 1, 0.5])
            c1.write(row["CÓDIGO"])
            c2.write(row["DESCRIÇÃO"])
            c3.write(f"{row['Preço Unitário']:.2f}€")
            qtd_txt = c4.text_input("Qtd", key=f"q_{row['CÓDIGO']}", label_visibility="collapsed", placeholder="0")
            if c5.button("➕", key=f"b_{row['CÓDIGO']}"):
                if qtd_txt:
                    v = float(qtd_txt.replace(',', '.'))
                    novo = pd.DataFrame([{"CÓDIGO": row["CÓDIGO"], "Artigo": row["DESCRIÇÃO"], "UNID": row["UNID"], "Preço Unitário": row["Preço Unitário"], "Quantidade": v}])
                    st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo], ignore_index=True)
                    st.rerun()

with tab_manual:
    st.info("Utiliza esta opção para itens que não existem na tabela de preços.")
    m1, m2, m3 = st.columns([1, 4, 1])
    m_cod = m1.text_input("Código", value="EXTRA")
    m_desc = m2.text_input("Descrição do Artigo/Serviço")
    m_unid = m3.text_input("Unidade", value="un")
    
    m4, m5, m6 = st.columns([1, 1, 2])
    m_preco = m4.number_input("Preço Unitário (€)", min_value=0.0, step=0.01, format="%.2f")
    m_qtd = m5.number_input("Quantidade", min_value=0.0, step=0.1)
    
    if m6.button("🚀 Adicionar Artigo Personalizado", use_container_width=True):
        if m_desc and m_qtd > 0:
            novo_m = pd.DataFrame([{"CÓDIGO": m_cod, "Artigo": m_desc, "UNID": m_unid, "Preço Unitário": m_preco, "Quantidade": m_qtd}])
            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo_m], ignore_index=True)
            st.rerun()
        else:
            st.warning("Preenche a descrição e a quantidade.")

# 4. ITENS APURADOS E TOTAIS
st.divider()
if not st.session_state.itens_orcamento.empty:
    df_v = st.session_state.itens_orcamento.copy()
    df_v["Subtotal (€)"] = df_v["Quantidade"] * df_v["Preço Unitário"]
    
    df_editado = st.data_editor(df_v, use_container_width=True, hide_index=True,
        column_config={
            "CÓDIGO": st.column_config.TextColumn("Cód", disabled=True),
            "Artigo": st.column_config.TextColumn("Descrição", disabled=True),
            "Subtotal (€)": st.column_config.NumberColumn("Subtotal", format="%.2f", disabled=True)
        }, key="editor")
    
    total_geral = df_editado["Subtotal (€)"].sum()
    st.markdown(f"## **Total Geral: {total_geral:,.2f} €**")
    
    if st.button("💾 Guardar Alterações da Tabela"):
        st.session_state.itens_orcamento = df_editado[["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"]]
        st.rerun()
