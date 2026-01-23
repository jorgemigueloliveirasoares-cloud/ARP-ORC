import streamlit as st
import pandas as pd
import os
import io
from datetime import date

# Bibliotecas para PDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# 1. CONFIGURAÇÃO E CARREGAMENTO
st.set_page_config(page_title="Orçamentador Pro", layout="wide")

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
        except: pass
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário"])

if "itens_orcamento" not in st.session_state:
    st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])

# 2. DADOS DO CLIENTE
st.subheader("📋 Dados do Orçamento")
c1, c2, c3 = st.columns([2, 2, 1])
nome_cli = c1.text_input("Cliente")
morada_cli = c2.text_input("Morada")
n_orc = c3.text_input("Nº Orçamento", value=f"ORC-{date.today().year}-001")

st.divider()

# 3. OPÇÃO A: SELEÇÃO DA TABELA (ESTA SECÇÃO ATUALIZA OS VALORES)
st.markdown("### **Opção A: Selecionar da Tabela de Preços**")
base = carregar_base()
lista_artigos = base.apply(lambda x: f"{x['CÓDIGO']} - {x['DESCRIÇÃO']}", axis=1).tolist()

col_pesq, col_unid_t, col_prec_t, col_qtd_t = st.columns([2, 0.5, 0.7, 0.6])

with col_pesq:
    escolha = st.selectbox("Pesquise o artigo:", options=[""] + lista_artigos, key="sel_tab")

# Lógica de preenchimento imediato
u_auto, p_auto = "", 0.0
if escolha:
    cod_atual = escolha.split(" - ")[0]
    dados = base[base["CÓDIGO"] == cod_atual].iloc[0]
    u_auto = str(dados["UNID"])
    p_auto = float(dados["Preço Unitário"])

with col_unid_t:
    st.text_input("Unid", value=u_auto, disabled=True, key="u_ver")
with col_prec_t:
    st.number_input("Preço Unit. €", value=p_auto, disabled=True, format="%.2f", key="p_ver")
with col_qtd_t:
    qtd_a = st.number_input("Qtd", min_value=0.01, value=1.0, key="q_ver")

if st.button("✅ Adicionar Item da Tabela", use_container_width=True):
    if escolha:
        novo = pd.DataFrame([{"CÓDIGO": cod_atual, "Artigo": escolha.split(" - ", 1)[1], "UNID": u_auto, "Preço Unitário": p_auto, "Quantidade": qtd_a}])
        st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo], ignore_index=True)
        st.rerun()

st.divider()

# 4. OPÇÃO B: MANUAL
st.markdown("### **Opção B: Adicionar Item Manual**")
with st.form("f_manual", clear_on_submit=True):
    cm1, cm2, cm3, cm4 = st.columns([2, 0.5, 0.7, 0.6])
    item_m = cm1.text_input("Descrição do Item Novo")
    unid_m = cm2.text_input("Unid", value="un")
    prec_m = cm3.number_input("Preço €", min_value=0.0, step=0.01, format="%.2f")
    qtd_m = cm4.number_input("Qtd", min_value=0.01, value=1.0)
    if st.form_submit_button("➕ Adicionar Manual"):
        if item_m:
            novo_m = pd.DataFrame([{"CÓDIGO": "MANUAL", "Artigo": item_m, "UNID": unid_m, "Preço Unitário": prec_m, "Quantidade": qtd_m}])
            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo_m], ignore_index=True)
            st.rerun()

# 5. TABELA FINAL E PDF
if not st.session_state.itens_orcamento.empty:
    st.divider()
    st.subheader("📋 Resumo")
    df_calc = st.session_state.itens_orcamento.copy()
    df_calc["Subtotal"] = df_calc["Quantidade"] * df_calc["Preço Unitário"]
    
    df_editado = st.data_editor(df_calc, use_container_width=True, hide_index=True)
    st.session_state.itens_orcamento = df_editado[["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"]]
    
    v_total = df_editado["Subtotal"].sum()
    st.metric("TOTAL", f"{v_total:,.2f}€")

    def exportar_pdf(df, tot):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        estilos = getSampleStyleSheet()
        elementos = [Paragraph(f"ORÇAMENTO: {n_orc}", estilos['Title']), Spacer(1, 20)]
        elementos.append(Paragraph(f"Cliente: {nome_cli}", estilos['Normal']))
        elementos.append(Spacer(1, 15))
        
        dados_tabela = [["Descrição", "Qtd", "Unid", "Preço", "Total"]]
        for _, r in df.iterrows():
            dados_tabela.append([Paragraph(str(r['Artigo']), estilos['Normal']), f"{r['Quantidade']}", r['UNID'], f"{r['Preço Unitário']}€", f"{r['Subtotal']:.2f}€"])
        
        dados_tabela.append(["", "", "", "TOTAL:", f"{tot:.2f}€"])
        t = Table(dados_tabela, colWidths=[250, 40, 40, 70, 70])
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.cadetblue), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('GRID', (0,0), (-1,-2), 0.5, colors.grey)]))
        elementos.append(t)
        doc.build(elementos)
        return buffer.getvalue()

    st.download_button("📥 Baixar PDF", data=exportar_pdf(df_editado, v_total), file_name=f"{n_orc}.pdf", use_container_width=True)
