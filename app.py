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

# 2. CABEÇALHO E DADOS DO CLIENTE
col_log, col_cli, col_rasc = st.columns([1.2, 2.5, 1.2])

with col_log:
    if os.path.exists("logo.png"): 
        st.image("logo.png", width=180)

with col_cli:
    st.subheader("📋 Dados do Cliente")
    nome_cli = st.text_input("Nome do Cliente", key="nome_cli")
    morada_cli = st.text_input("Morada", key="morada_cli")
    c1, c2 = st.columns(2)
    tel_cli = c1.text_input("Telefone", key="tel_cli")
    email_cli = c2.text_input("Email do Cliente", key="email_cli")
    obs_cli = st.text_area("Notas / Observações", key="obs_cli")

with col_rasc:
    st.subheader("💾 Backup / Rascunho")
    n_orc = st.text_input("Nº Orçamento", value=f"ORC-{date.today().year}-001")
    
    dados_backup = {
        "cliente": {"nome": nome_cli, "morada": morada_cli, "tel": tel_cli, "email": email_cli, "obs": obs_cli, "n_orc": n_orc},
        "itens": st.session_state.itens_orcamento.to_dict(orient="records")
    }
    st.download_button("📥 Guardar Backup", data=json.dumps(dados_backup), file_name=f"backup_{n_orc}.json", use_container_width=True)
    
    u_backup = st.file_uploader("📂 Upload de Backup", type="json", label_visibility="collapsed")
    if u_backup:
        carregados = json.load(u_backup)
        st.session_state.itens_orcamento = pd.DataFrame(carregados["itens"])
        st.success("Dados carregados!")

st.divider()

# 3. ADIÇÃO DE ITENS
st.subheader("🔍 1. Adicionar Itens")
tab1, tab2 = st.tabs(["🔎 Pesquisar Excel (Escolha Pendente)", "➕ Manual"])

with tab1:
    base = carregar_base()
    lista_artigos = base.apply(lambda x: f"{x['CÓDIGO']} - {x['DESCRIÇÃO']}", axis=1).tolist()
    
    escolha = st.selectbox(
        "Pesquise o código ou nome do artigo:",
        options=[""] + lista_artigos,
        index=0,
        help="Escreva para filtrar a lista automaticamente"
    )

    if escolha:
        cod_selecionado = escolha.split(" - ")[0]
        row = base[base["CÓDIGO"] == cod_selecionado].iloc[0]
        
        st.info(f"**Selecionado:** {row['DESCRIÇÃO']} ({row['Preço Unitário']:.2f}€/{row['UNID']})")
        
        # COLOCA QUANTIDADE E BOTÃO NA MESMA LINHA
        c_q, c_b = st.columns([1, 1])
        
        with c_q:
            qtd_txt = st.text_input("Introduza a Quantidade", value="1", key="qtd_sel")
        
        with c_b:
            # Espaçamento manual para alinhar o botão com o campo de texto
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            btn_add = st.button("✅ Adicionar ao Orçamento", use_container_width=True)
        
        if btn_add:
            qtd_limpa = qtd_txt.replace(',', '.').strip()
            try:
                v = float(qtd_limpa)
                if v > 0:
                    novo = pd.DataFrame([{
                        "CÓDIGO": row["CÓDIGO"], 
                        "Artigo": row["DESCRIÇÃO"], 
                        "UNID": row["UNID"], 
                        "Preço Unitário": float(row["Preço Unitário"]), 
                        "Quantidade": v
                    }])
                    st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo], ignore_index=True)
                    st.rerun()
                else:
                    st.error("A quantidade deve ser superior a zero.")
            except ValueError:
                st.error("Quantidade inválida. Use números.")

with tab2:
    m1, m2, m3, m4 = st.columns([3, 1, 1, 1])
    m_desc = m1.text_input("Descrição Manual")
    m_prec = m2.number_input("Preço €", min_value=0.0, step=0.01, format="%.2f")
    m_qtd = m3.number_input("Qtd", min_value=0.0, step=0.01, format="%.2f")
    if m4.button("Adicionar Item"):
        if m_desc and m_qtd > 0:
            nm = pd.DataFrame([{"CÓDIGO": "EXTRA", "Artigo": m_desc, "UNID": "un", "Preço Unitário": m_prec, "Quantidade": m

