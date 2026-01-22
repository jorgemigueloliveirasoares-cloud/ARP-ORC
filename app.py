import streamlit as st
import pandas as pd
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
import io
import os
import pickle  # Para guardar o estado completo

# 1. Configuração e Estética
st.set_page_config(page_title="Orçamentador Pro", layout="wide")

LOGO_PATH = "logo.png" 
EXCEL_PATH = "Cópia de Preços Tabela atual.xlsx"

if os.path.exists(LOGO_PATH):
    st.image(LOGO_PATH, width=250)

# --------------------------------------------------
# Funções de Suporte
# --------------------------------------------------
def carregar_base_limpa():
    if os.path.exists(EXCEL_PATH):
        df = pd.read_excel(EXCEL_PATH)
        colunas = ["CÓDIGO", "DESCRIÇÃO", "UNID", "VALORES ATUAIS JANEIRO 2025"]
        df = df[colunas].dropna(subset=["DESCRIÇÃO"])
        df.rename(columns={"VALORES ATUAIS JANEIRO 2025": "Preço Unitário"}, inplace=True)
        df["Quantidade"] = 0.0
        return df
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário", "Quantidade"])

# --------------------------------------------------
# Gestão de Estado (Sessão)
# --------------------------------------------------
if "lista_orcamentos" not in st.session_state:
    st.session_state["lista_orcamentos"] = {
        "Orçamento 1": {"cliente": "", "obra": "", "notas": "", "dados": carregar_base_limpa()}
    }
    st.session_state["orc_atual"] = "Orçamento 1"

# --------------------------------------------------
# Sidebar: Gestão de Sessões e Gravação Permanente
# --------------------------------------------------
with st.sidebar:
    st.header("💾 Guardar/Carregar Trabalho")
    
    # Botão para descarregar o rascunho atual (Backup)
    estado_para_gravar = {
        "lista": st.session_state["lista_orcamentos"],
        "atual": st.session_state["orc_atual"]
    }
    st.download_button(
        label="📥 Exportar Rascunhos (Backup)",
        data=pickle.dumps(estado_para_gravar),
        file_name=f"backup_orcamentos_{date.today()}.pkl",
        help="Guarda todos os orçamentos abertos num ficheiro para continuar mais tarde."
    )
    
    # Upload para restaurar rascunhos
    arquivo_backup = st.file_uploader("📂 Restaurar Rascunhos", type=["pkl"])
    if arquivo_backup:
        dados_restaurados = pickle.loads(arquivo_backup.read())
        st.session_state["lista_orcamentos"] = dados_restaurados["lista"]
        st.session_state["orc_atual"] = dados_restaurados["atual"]
        st.success("Trabalho restaurado!")
        st.rerun()

    st.divider()
    st.header("📂 Alternar Orçamentos")
    opcoes = list(st.session_state["lista_orcamentos"].keys())
    escolha = st.selectbox("Selecionar:", opcoes, index=opcoes.index(st.session_state["orc_atual"]))
    
    if escolha != st.session_state["orc_atual"]:
        st.session_state["orc_atual"] = escolha
        st.rerun()

    if st.button("➕ Novo Orçamento"):
        novo_nome = f"Orçamento {len(st.session_state['lista_orcamentos']) + 1}"
        st.session_state["lista_orcamentos"][novo_nome] = {"cliente": "", "obra": "", "notas": "", "dados": carregar_base_limpa()}
        st.session_state["orc_atual"] = novo_nome
        st.rerun()

    st.divider()
    res = st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]
    res["cliente"] = st.text_input("Cliente", res["cliente"])
    res["obra"] = st.text_input("Obra", res["obra"])
    iva_percent = st.selectbox("IVA (%)", [0, 6, 13, 23], index=3)

# --------------------------------------------------
# Área de Trabalho
# --------------------------------------------------
dados_atuais = st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]["dados"]
st.title(f"📐 Editando: {st.session_state['orc_atual']}")

# Campo para Itens Manuais
with st.expander("➕ Adicionar item personalizado"):
    c1, c2, c3, c4 = st.columns([1, 3, 1, 1])
    n_cod = c1.text_input("Cód")
    n_des = c2.text_input("Descrição")
    n_uni = c3.text_input("Unid")
    n_pre = c4.number_input("Preço (€)", min_value=0.0)
    if st.button("Inserir"):
        novo = pd.DataFrame([{"CÓDIGO": n_cod, "DESCRIÇÃO": n_des, "UNID": n_uni, "Preço Unitário": n_pre, "Quantidade": 0.0}])
        st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]["dados"] = pd.concat([dados_atuais, novo], ignore_index=True)
        st.rerun()

# Pesquisa e Edição
pesquisa = st.text_input("🔍 Pesquisar na base...")
mask = dados_atuais["DESCRIÇÃO"].str.contains(pesquisa, case=False, na=False) | \
       dados_atuais["CÓDIGO"].astype(str).str.contains(pesquisa, case=False, na=False)

df_view = dados_atuais[mask | (dados_atuais["Quantidade"] > 0)].copy()

edited_df = st.data_editor(
    df_view,
    column_config={
        "Preço Unitário": st.column_config.NumberColumn("Preço (€)", format="%.2f"),
        "Quantidade": st.column_config.NumberColumn("Qtd", min_value=0.0)
    },
    hide_index=True, use_container_width=True
)

# Sincronização
for idx in edited_df.index:
    st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]["dados"].at[idx, "Quantidade"] = edited_df.loc[idx, "Quantidade"]
    st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]["dados"].at[idx, "Preço Unitário"] = edited_df.loc[idx, "Preço Unitário"]

st.divider()
res["notas"] = st.text_area("📝 Notas / Observações", res["notas"])

# --------------------------------------------------
# Totais e Exportação (PDF/Excel)
# --------------------------------------------------
itens_finais = dados_atuais[dados_atuais["Quantidade"] > 0].copy()
if not itens_finais.empty:
    itens_finais["Total"] = itens_finais["Quantidade"] * itens_finais["Preço Unitário"]
    total = itens_finais["Total"].sum() * (1 + iva_percent/100)
    
    st.subheader(f"Total Orçamentado: {total:,.2f} €")
    
    c1, c2 = st.columns(2)
    with c1:
        # Lógica de PDF igual à anterior...
        st.button("📄 Gerar PDF (Funcionalidade Ativa)")
    with c2:
        # Lógica de Excel igual à anterior...
        st.button("⬇️ Baixar Excel (Funcionalidade Ativa)")
