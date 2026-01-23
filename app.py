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

# Inicialização do Estado
if "itens_orcamento" not in st.session_state:
    st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])
if "unid_preview" not in st.session_state:
    st.session_state.unid_preview = ""
if "preco_preview" not in st.session_state:
    st.session_state.preco_preview = ""

# Função para atualizar os campos instantaneamente
def atualizar_campos():
    escolha = st.session_state.sel_artigo
    if escolha:
        base = carregar_base()
        cod = escolha.split(" - ")[0]
        item = base[base["CÓDIGO"] == cod].iloc[0]
        st.session_state.unid_preview = str(item["UNID"])
        st.session_state.preco_preview = f"{float(item['Preço Unitário']):.2f} €"
    else:
        st.session_state.unid_preview = ""
        st.session_state.preco_preview = ""

# 2. CABEÇALHO E DADOS DO CLIENTE (Mantido igual)
col_log, col_cli, col_rasc = st.columns([1.2, 2.5, 1.2])
with col_log:
    if os.path.exists("logo.png"): st.image("logo.png", width=180)
with col_cli:
    st.subheader("📋 Dados do Cliente")
    nome_cli = st.text_input("Nome do Cliente")
    morada_cli = st.text_input("Morada")
    c1, c2 = st.columns(2)
    tel_cli = c1.text_input("Telefone")
    email_cli = c2.text_input("Email")
    obs_cli = st.text_area("Observações")

with col_rasc:
    st.subheader("💾 Backup")
    n_orc = st.text_input("Nº Orçamento", value=f"ORC-{date.today().year}-001")
    dados_backup = {"cliente": {"nome": nome_cli, "n_orc": n_orc}, "itens": st.session_state.itens_orcamento.to_dict(orient="records")}
    st.download_button("📥 Guardar", data=json.dumps(dados_backup), file_name=f"backup_{n_orc}.json", use_container_width=True)

st.divider()

# --- 3. ADIÇÃO DE ITENS (O TEU LAYOUT FAVORITO) ---
st.subheader("🔍 1. Adicionar Itens")
base_dados = carregar_base()
lista_artigos = base_dados.apply(lambda x: f"{x['CÓDIGO']} - {x['DESCRIÇÃO']}", axis=1).tolist()

# Layout em linha como na tua imagem
c_sel, c_uni, c_pre, c_qtd, c_add = st.columns([3, 0.6, 0.8, 0.8, 1])

with c_sel:
    st.selectbox("Artigo:", options=[""] + lista_artigos, key="sel_artigo", on_change=atualizar_campos)

with c_uni:
    st.text_input("Unid.", value=st.session_state.unid_preview, disabled=True)

with c_pre:
    st.text_input("Preço Unit.", value=st.session_state.preco_preview, disabled=True)

with c_qtd:
    qtd_val = st.number_input("Qtd", min_value=0.01, value=1.0, step=0.5)

with c_add:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("✅ Adicionar", use_container_width=True):
        if st.session_state.sel_artigo:
            cod_sel = st.session_state.sel_artigo.split(" - ")[0]
            row = base_dados[base_dados["CÓDIGO"] == cod_sel].iloc[0]
            novo = pd.DataFrame([{"CÓDIGO": row["CÓDIGO"], "Artigo": row["DESCRIÇÃO"], "UNID": row["UNID"], "Preço Unitário": float(row["Preço Unitário"]), "Quantidade": qtd_val}])
            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo], ignore_index=True)
            st.rerun()

st.divider()

# --- SECÇÃO 2: ITEM EXTRA ---
st.subheader("✍️ 2. Item Extra (Manual)")
c_art_ex, c_uni_ex, c_pre_ex, c_qtd_ex, c_add_ex = st.columns([3, 0.6, 0.8, 0.8, 1])
with c_art_ex:
    artigo_ex = st.text_input("Descrição do Artigo Extra:", placeholder="Ex: Mão-de-obra...")
with c_uni_ex:
    uni_ex = st.text_input("Unid:", key="u_ex")
with c_pre_ex:
    pre_ex = st.number_input("Preço (€):", min_value=0.0, key="p_ex")
with c_qtd_ex:
    q_ex = st.number_input("Qtd:", min_value=0.01, value=1.0, key="q_ex")
with c_add_ex:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("➕ Adicionar Extra", use_container_width=True):
        if artigo_ex:
            novo_ex = pd.DataFrame([{"CÓDIGO": "EXTRA", "Artigo": artigo_ex, "UNID": uni_ex, "Preço Unitário": float(pre_ex), "Quantidade": q_ex}])
            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo_ex], ignore_index=True)
            st.rerun()

# 4. RESUMO E TABELA (Mantido conforme original)
st.divider()
if not st.session_state.itens_orcamento.empty:
    st.markdown("### 📋 Resumo do Orçamento")
    taxa_iva = st.selectbox("Taxa de IVA:", [23, 13, 6, 0])
    df_f = st.session_state.itens_orcamento.copy()
    df_f["Subtotal"] = df_f["Quantidade"] * df_f["Preço Unitário"]
    
    df_editado = st.data_editor(df_f, use_container_width=True, hide_index=True, num_rows="dynamic")
    st.session_state.itens_orcamento = df_editado[["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"]]
    
    # Cálculos e PDF (Logica mantida para não alterar o teu código base)
    sub = df_editado["Subtotal"].sum()
    total = sub * (1 + taxa_iva/100)
    st.metric("Total Final (c/ IVA)", f"{total:.2f} €")
    
    if st.button("🗑️ Limpar Tudo"):
        st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])
        st.rerun()
