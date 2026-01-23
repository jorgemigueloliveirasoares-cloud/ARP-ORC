import streamlit as st
import pandas as pd
import os
import io
import json
from datetime import date

# Bibliotecas para PDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

# 1. CONFIGURAÇÃO INICIAL
st.set_page_config(page_title="Orçamentador Pro", layout="wide")
AZUL_LOGO = colors.Color(0/255, 115/255, 180/255) 

@st.cache_data(ttl=600)
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
            df["Preço Unitário"] = pd.to_numeric(df["Preço Unitário"], errors='coerce').fillna(0.0)
            return df
        except Exception as e:
            st.error(f"Erro ao ler Excel: {e}")
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário"])

if "itens_orcamento" not in st.session_state:
    st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])

# 2. CABEÇALHO
col_log, col_cli, col_rasc = st.columns([1.2, 2.5, 1.2])
with col_log:
    if os.path.exists("logo.png"): st.image("logo.png", width=180)
with col_cli:
    st.subheader("📋 Dados do Cliente")
    nome_cli = st.text_input("Nome do Cliente")
    morada_cli = st.text_input("Morada")
    tel_cli = st.text_input("Telefone/Email")
with col_rasc:
    n_orc = st.text_input("Nº Orçamento", value=f"ORC-{date.today().year}-001")

st.divider()

# 3. ADIÇÃO DE ITENS (LÓGICA CORRIGIDA)
st.subheader("🔍 1. Adicionar Itens")
base = carregar_base()
lista_artigos = base.apply(lambda x: f"{x['CÓDIGO']} - {x['DESCRIÇÃO']}", axis=1).tolist()

# --- OPÇÃO A: FORA DO FORMULÁRIO PARA ATUALIZAÇÃO IMEDIATA ---
st.markdown("### **Opção A: Selecionar da Tabela de Preços**")
col_pesq, col_unid_t, col_prec_t, col_qtd_t = st.columns([2, 0.5, 0.7, 0.6])

with col_pesq:
    escolha = st.selectbox("Pesquise o código ou nome do artigo:", options=[""] + lista_artigos, index=0, key="sel_tabela")

# Procurar dados assim que a escolha muda
u_val, p_val = "", 0.0
if escolha:
    c_cod = escolha.split(" - ")[0]
    match = base[base["CÓDIGO"] == c_cod].iloc[0]
    u_val = str(match["UNID"])
    p_val = float(match["Preço Unitário"])

with col_unid_t:
    st.text_input("Unid", value=u_val, disabled=True, key="u_disp")
with col_prec_t:
    st.number_input("Preço Unit. €", value=p_val, disabled=True, format="%.2f", key="p_disp")
with col_qtd_t:
    qtd_a = st.number_input("Qtd", min_value=0.01, value=1.0, key="q_a")

if st.button("✅ Adicionar Item Selecionado", use_container_width=True):
    if escolha:
        novo = pd.DataFrame([{"CÓDIGO": c_cod, "Artigo": escolha.split(" - ", 1)[1], "UNID": u_val, "Preço Unitário": p_val, "Quantidade": qtd_a}])
        st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo], ignore_index=True)
        st.rerun()

st.markdown("---")

# --- OPÇÃO B: MANUAL (DENTRO DE FORMULÁRIO PARA O ENTER FUNCIONAR) ---
st.markdown("### **Opção B: Adicionar Item Manual**")
with st.form("form_manual", clear_on_submit=True):
    col_desc_m, col_unid_m, col_prec_m, col_qtd_m = st.columns([2, 0.5, 0.7, 0.6])
    with col_desc_m:
        item_m = st.text_input("Descrição do Item Novo:", placeholder="Escreva aqui...")
    with col_unid_m:
        unid_m = st.text_input("Unid", value="un")
    with col_prec_m:
        prec_m = st.number_input("Preço €", min_value=0.0, step=0.01, format="%.2f")
    with col_qtd_m:
        qtd_m = st.number_input("Qtd", min_value=0.01, value=1.0)
    
    if st.form_submit_button("➕ Adicionar Manual (ou Enter)", use_container_width=True):
        if item_m:
            novo_m = pd.DataFrame([{"CÓDIGO": "MANUAL", "Artigo": item_m, "UNID": unid_m, "Preço Unitário": prec_m, "Quantidade": qtd_m}])
            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo_m], ignore_index=True)
            st.rerun()

# 4. RESUMO E PDF
st.divider()
if not st.session_state.itens_orcamento.empty:
    st.markdown("### 📋 Resumo")
    df_calc = st.session_state.itens_orcamento.copy()
    df_calc["Subtotal"] = df_calc["Quantidade"] * df_calc["Preço Unitário"]
    
    df_editado = st.data_editor(df_calc, use_container_width=True, hide_index=True)
    st.session_state.itens_orcamento = df_editado[["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"]]
    
    total = df_editado["Subtotal"].sum()
    st.metric("TOTAL ORÇAMENTO", f"{total:,.2f}€")

    # Botão PDF Simples
    def gerar_pdf(df, tot):
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4)
        elems = [Paragraph(f"ORÇAMENTO: {n_orc}", getSampleStyleSheet()['Title']), Spacer(1, 12)]
        data = [["Artigo", "Qtd", "Unid", "Preço", "Total"]]
        for _, r in df.iterrows():
            data.append([r['Artigo'][:50], r['Quantidade'], r['UNID'], f"{r['Preço Unitário']}€", f"{(r['Quantidade']*r['Preço Unitário']):.2f}€"])
        data.append(["", "", "", "TOTAL:", f"{tot:.2f}€"])
        t = Table(data, colWidths=[250, 40, 40, 70, 70])
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
        elems.append(t)
        doc.build(elems)
        return buf.getvalue()

    st.download_button("📥 Baixar PDF", data=gerar_pdf(df_editado, total), file_name=f"{n_orc}.pdf", use_container_width=True)
