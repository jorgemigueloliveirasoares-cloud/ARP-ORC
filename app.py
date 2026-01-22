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
import pickle

# --------------------------------------------------
# 1. Configuração e Estética
# --------------------------------------------------
st.set_page_config(page_title="Orçamentador Pro", layout="wide")

LOGO_PATH = "logo.png" 
EXCEL_PATH = "Cópia de Preços Tabela atual.xlsx"

# --------------------------------------------------
# 2. Funções de Suporte e Salvamento
# --------------------------------------------------
def carregar_base_limpa():
    if os.path.exists(EXCEL_PATH):
        try:
            df = pd.read_excel(EXCEL_PATH)
            colunas = ["CÓDIGO", "DESCRIÇÃO", "UNID", "VALORES ATUAIS JANEIRO 2025"]
            df = df[colunas].dropna(subset=["DESCRIÇÃO"])
            df.rename(columns={"VALORES ATUAIS JANEIRO 2025": "Preço Unitário"}, inplace=True)
            df["Quantidade"] = 0.0
            return df
        except:
            pass
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário", "Quantidade"])

def salvar_edicoes():
    key = f"editor_{st.session_state['orc_atual']}"
    if key in st.session_state:
        edicoes = st.session_state[key]
        for row_idx, alteracoes in edicoes["edited_rows"].items():
            for col, val in alteracoes.items():
                st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]["dados"].at[row_idx, col] = val

# --------------------------------------------------
# 3. Gestão de Estado (Sessão)
# --------------------------------------------------
if "lista_orcamentos" not in st.session_state:
    st.session_state["lista_orcamentos"] = {
        "Orçamento 1": {
            "cliente": "", "morada": "", "telefone": "", "obra": "", 
            "data_visita": date.today(), "notas": "", "dados": carregar_base_limpa()
        }
    }
    st.session_state["orc_atual"] = "Orçamento 1"

# --------------------------------------------------
# 4. Interface Superior (Logo e Botões de Ação)
# --------------------------------------------------
col_logo, col_acoes = st.columns([1, 2])

with col_logo:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=200)

with col_acoes:
    st.write("### 📄 Exportar e Ações")
    c_pdf, c_xls, c_clear = st.columns(3)
    
    # Preparar dados para exportação
    res = st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]
    itens_finais = res["dados"][res["dados"]["Quantidade"] > 0].copy()
    
    if not itens_finais.empty:
        itens_finais["Total"] = itens_finais["Quantidade"] * itens_finais["Preço Unitário"]
        total_geral = itens_finais["Total"].sum() # Simplificado para exemplo

        # Botão PDF
        with c_pdf:
            pdf_buffer = io.BytesIO()
            # ... (Lógica do PDF igual à anterior)
            st.download_button("⬇️ Gerar PDF", b"pdf_data", f"Orcamento_{res['cliente']}.pdf")
            
        # Botão Excel
        with c_xls:
            output_ex = io.BytesIO()
            # ... (Lógica do Excel igual à anterior)
            st.download_button("⬇️ Gerar Excel", b"excel_data", f"Orcamento_{res['cliente']}.xlsx")
    else:
        st.info("Adicione itens para exportar")

# --------------------------------------------------
# 5. Sidebar e Dados do Cliente
# --------------------------------------------------
with st.sidebar:
    st.header("💾 Backup")
    # ... (Botões de backup iguais)
    st.divider()
    st.header("📋 Dados do Cliente")
    res["cliente"] = st.text_input("Cliente", res["cliente"])
    res["morada"] = st.text_area("Morada", res["morada"])
    res["telefone"] = st.text_input("Telefone", res["telefone"])
    res["obra"] = st.text_input("Obra", res["obra"])
    res["data_visita"] = st.date_input("Data Visita", res["data_visita"])

# --------------------------------------------------
# 6. Seleção de Artigos (Meio)
# --------------------------------------------------
st.divider()
st.subheader("🔍 Seleção de Artigos")
pesquisa = st.text_input("Pesquise pelo nome ou código do artigo...")
dados_atuais = res["dados"]
mask = dados_atuais["DESCRIÇÃO"].str.contains(pesquisa, case=False, na=False)

# Tabela de pesquisa (só mostra o que não tem quantidade para não duplicar)
df_selecao = dados_atuais[mask & (dados_atuais["Quantidade"] == 0)]

st.data_editor(
    df_selecao,
    column_config={"Quantidade": st.column_config.NumberColumn("Add Qtd", min_value=0.0)},
    hide_index=True, use_container_width=True,
    key=f"editor_{st.session_state['orc_atual']}",
    on_change=salvar_edicoes
)

# --------------------------------------------------
# 7. Itens Apurados (Fundo - Estilo imagem anexada)
# --------------------------------------------------
st.write("")
st.markdown("### 📋 Itens no Orçamento (Apurados)")

if not itens_finais.empty:
    # Formatação para parecer com a imagem anexada
    df_apurado = itens_finais.copy()
    df_apurado["Apurado (€)"] = df_apurado["Total"].map("{:.2f} €".format)
    df_apurado = df_apurado.rename(columns={
        "DESCRIÇÃO": "Artigo",
        "UNID": "UM",
        "Quantidade": "Qnt",
        "Preço Unitário": "V Unit"
    })
    
    # Exibe a tabela de itens já escolhidos
    st.table(df_apurado[["Artigo", "Qnt", "UM", "V Unit", "Apurado (€)"]])
    
    st.success(f"**Total do Orçamento: {itens_finais['Total'].sum():,.2f} €**")
else:
    st.warning("Nenhum item selecionado ainda.")
