import streamlit as st
import pandas as pd
import os
from datetime import date

# --------------------------------------------------
# 1. CONFIGURAÇÃO E DADOS
# --------------------------------------------------
st.set_page_config(page_title="Orçamentador Pro", layout="wide")

LOGO_PATH = "logo.png"  # Certifica-te que o ficheiro está na mesma pasta
EXCEL_PATH = "Cópia de Preços Tabela atual.xlsx"

def carregar_base():
    if os.path.exists(EXCEL_PATH):
        try:
            df = pd.read_excel(EXCEL_PATH)
            df.columns = [str(c).strip() for c in df.columns]
            col_preco = "VALORES ATUAIS JANEIRO 2025"
            df = df[["CÓDIGO", "DESCRIÇÃO", "UNID", col_preco]].dropna(subset=["CÓDIGO"])
            df.rename(columns={col_preco: "Preço Unitário"}, inplace=True)
            df["CÓDIGO"] = df["CÓDIGO"].astype(str).str.strip()
            df["DESCRIÇÃO"] = df["DESCRIÇÃO"].astype(str).str.strip()
            return df
        except: pass
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário"])

# Estado da Sessão
if "base_dados" not in st.session_state:
    st.session_state.base_dados = carregar_base()
if "itens_orcamento" not in st.session_state:
    st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])

# --------------------------------------------------
# 2. CABEÇALHO PROFISSIONAL (LOGO + CLIENTE)
# --------------------------------------------------
# Criamos 3 colunas para o topo
col_log, col_cli, col_num = st.columns([1.2, 2.5, 1])

with col_log:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=180)
    else:
        st.info("Coloque 'logo.png' na pasta.")

with col_cli:
    st.markdown("### **Dados do Cliente**")
    c_nome = st.text_input("Nome do Cliente", placeholder="Ex: João Silva")
    c_morada = st.text_input("Morada", placeholder="Ex: Rua das Flores, nº 10")
    
    # Linha dupla para Contactos
    c1, c2 = st.columns(2)
    c_tel = c1.text_input("Contacto Telefónico", placeholder="910 000 000")
    c_email = c2.text_input("Email", placeholder="cliente@email.com")

with col_num:
    st.markdown("### **Identificação**")
    # Geração automática de número de orçamento simples
    data_hoje = date.today().strftime("%Y/%m")
    n_orc = st.text_input("Nº Orçamento", value=f"ORC-{data_hoje}-001")
    st.date_input("Data de Emissão", date.today())

st.divider()

# --------------------------------------------------
# 3. PESQUISA E ADIÇÃO
# --------------------------------------------------
st.subheader("🔍 1. Pesquisar e Adicionar Artigos")
termo = st.text_input("Pesquise por nome ou código:", key="search_bar").strip()

if termo:
    base = st.session_state.base_dados
    mask = (base["DESCRIÇÃO"].str.contains(termo, case=False, na=False)) | \
           (base["CÓDIGO"].str.contains(termo, case=False, na=False))
    resultados = base[mask].head(12)
    
    if not resultados.empty:
        for i, row in resultados.iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([1, 4, 1, 1, 0.5])
                c1.write(f"**{row['CÓDIGO']}**")
                c2.write(row["DESCRIÇÃO"])
                c3.write(f"{row['Preço Unitário']:.2f}€")
                qtd_input = c4.text_input("Qtd", key=f"q_{row['CÓDIGO']}", label_visibility="collapsed")
                
                if c5.button("➕", key=f"btn_{row['CÓDIGO']}"):
                    if qtd_input:
                        try:
                            v = float(qtd_input.replace(',', '.'))
                            novo = pd.DataFrame([{"CÓDIGO": row["CÓDIGO"], "Artigo": row["DESCRIÇÃO"], "UNID": row["UNID"], "Preço Unitário": row["Preço Unitário"], "Quantidade": v}])
                            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo], ignore_index=True)
                            st.rerun()
                        except: st.toast("Erro na Qtd")
    else:
        st.warning("Artigo não encontrado.")

# --------------------------------------------------
# 4. ITENS APURADOS
# --------------------------------------------------
st.divider()
st.subheader("📝 2. Itens no Orçamento")

if not st.session_state.itens_orcamento.empty:
    df_view = st.session_state.itens_orcamento.copy()
    df_view["Subtotal (€)"] = df_view["Quantidade"] * df_view["Preço Unitário"]
    
    df_editado = st.data_editor(
        df_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "CÓDIGO": st.column_config.TextColumn("Cód", disabled=True),
            "Artigo": st.column_config.TextColumn("Descrição", disabled=True),
            "Preço Unitário": st.column_config.NumberColumn("V. Unit (€)", format="%.2f"),
            "Quantidade": st.column_config.NumberColumn("Qtd", format="%.2f"),
            "Subtotal (€)": st.column_config.NumberColumn("Subtotal", format="%.2f", disabled=True)
        },
        key="editor_final"
    )
    
    t_final = df_editado["Subtotal (€)"].sum()
    c_t, c_btn = st.columns([3, 1])
    c_t.markdown(f"## **Total Geral: {t_final:,.2f} €**")
    
    if c_btn.button("💾 Atualizar Totais", use_container_width=True):
        st.session_state.itens_orcamento = df_editado[["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"]]
        st.rerun()
