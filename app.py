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
# 1. CONFIGURAÇÃO
# --------------------------------------------------
st.set_page_config(page_title="Orçamentador Pro", layout="wide")

LOGO_PATH = "logo.png" 
EXCEL_PATH = "Cópia de Preços Tabela atual.xlsx"

# --------------------------------------------------
# 2. FUNÇÕES DE DADOS (CORRIGIDAS)
# --------------------------------------------------
def carregar_base_limpa():
    if os.path.exists(EXCEL_PATH):
        try:
            df = pd.read_excel(EXCEL_PATH)
            colunas = ["CÓDIGO", "DESCRIÇÃO", "UNID", "VALORES ATUAIS JANEIRO 2025"]
            df = df[colunas].dropna(subset=["CÓDIGO", "DESCRIÇÃO"])
            df.rename(columns={"VALORES ATUAIS JANEIRO 2025": "Preço Unitário"}, inplace=True)
            df["Quantidade"] = 0.0
            df["CÓDIGO"] = df["CÓDIGO"].astype(str).str.strip() # Limpeza de espaços
            # Definir o CÓDIGO como o ID real da linha
            df = df.set_index("CÓDIGO", drop=False)
            return df
        except Exception as e:
            st.error(f"Erro no Excel: {e}")
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário", "Quantidade"])

def sincronizar_dados(key_editor):
    """Sincronização por ID de CÓDIGO (Impede a troca de itens)"""
    if key_editor in st.session_state:
        edicoes = st.session_state[key_editor]
        res_dados = st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]["dados"]
        
        # Obter a "chave" (CÓDIGO) de cada linha editada
        # O Streamlit devolve o índice do dataframe que enviamos
        for row_id, alteracoes in edicoes["edited_rows"].items():
            for col, val in alteracoes.items():
                res_dados.at[row_id, col] = val
        
        # Processar remoções
        for row_id in edicoes["deleted_rows"]:
            res_dados.at[row_id, "Quantidade"] = 0.0

# --------------------------------------------------
# 3. ESTADO DA SESSÃO
# --------------------------------------------------
if "lista_orcamentos" not in st.session_state:
    st.session_state["lista_orcamentos"] = {
        "Orçamento 1": {
            "cliente": "", "morada": "", "telefone": "", 
            "dados": carregar_base_limpa(), "notas": ""
        }
    }
    st.session_state["orc_atual"] = "Orçamento 1"

res = st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]

# --------------------------------------------------
# 4. CABEÇALHO (LOGO E TOTAIS)
# --------------------------------------------------
col_log, col_info, col_exp = st.columns([1, 2, 1.5])

with col_log:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=150)

with col_info:
    st.subheader(f"📋 {st.session_state['orc_atual']}")
    c1, c2 = st.columns(2)
    res["cliente"] = c1.text_input("Cliente", res["cliente"])
    res["telefone"] = c2.text_input("Telefone", res["telefone"])
    res["morada"] = st.text_input("Morada", res["morada"])

with col_exp:
    # Cálculo de Totais (Só itens com Qtd > 0)
    df_finais = res["dados"][res["dados"]["Quantidade"] > 0].copy()
    if not df_finais.empty:
        total = (df_finais["Quantidade"] * df_finais["Preço Unitário"]).sum()
        st.markdown(f"### **Total: {total:,.2f} €**")
        
        # Botão PDF Simples
        pdf_io = io.BytesIO()
        doc = SimpleDocTemplate(pdf_io, pagesize=A4)
        elements = [Paragraph(f"Orçamento: {res['cliente']}", getSampleStyleSheet()['Title'])]
        # (Restante lógica do PDF...)
        doc.build(elements)
        st.download_button("⬇️ Baixar PDF", pdf_io.getvalue(), "orcamento.pdf")
    else:
        st.info("Adicione quantidades abaixo.")

# --------------------------------------------------
# 5. PESQUISA (NÃO TROCA ITENS)
# --------------------------------------------------
st.divider()
st.subheader("🔍 1. Pesquisar e Adicionar")
pesquisa = st.text_input("Procure por Nome ou Código (Ex: arp2202)...")

# Filtro inteligente
mask = (res["dados"]["DESCRIÇÃO"].str.contains(pesquisa, case=False, na=False)) | \
       (res["dados"]["CÓDIGO"].str.contains(pesquisa, case=False, na=False))

# IMPORTANTE: Passamos o DataFrame com o index de CÓDIGO
df_search = res["dados"][mask & (res["dados"]["Quantidade"] == 0)]

st.data_editor(
    df_search,
    column_config={
        "CÓDIGO": st.column_config.TextColumn("Cód", disabled=True),
        "DESCRIÇÃO": st.column_config.TextColumn("Descrição", disabled=True),
        "Preço Unitário": st.column_config.NumberColumn("Preço Base (€)", format="%.2f", disabled=True),
        "Quantidade": st.column_config.NumberColumn("Qtd", min_value=0.0)
    },
    hide_index=True, # Agora podemos esconder o index visualmente porque ele está no 'id' interno
    use_container_width=True,
    key=f"search_{st.session_state['orc_atual']}",
    on_change=sincronizar_dados, args=(f"search_{st.session_state['orc_atual']}",)
)

# --------------------------------------------------
# 6. APURADOS (ESTILO IMAGEM ANEXADA)
# --------------------------------------------------
st.markdown("---")
st.subheader("📝 2. Itens Apurados (No Orçamento)")

df_apurados = res["dados"][res["dados"]["Quantidade"] > 0]

if not df_apurados.empty:
    st.data_editor(
        df_apurados,
        column_config={
            "CÓDIGO": st.column_config.TextColumn("Cód", disabled=True),
            "DESCRIÇÃO": st.column_config.TextColumn("Artigo", width="large", disabled=True),
            "Preço Unitário": st.column_config.NumberColumn("V. Unit (€)", format="%.2f"),
            "Quantidade": st.column_config.NumberColumn("Qtd", min_value=0.0)
        },
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
        key=f"edit_{st.session_state['orc_atual']}",
        on_change=sincronizar_dados, args=(f"edit_{st.session_state['orc_atual']}",)
    )
    res["notas"] = st.text_area("Notas", res["notas"])
else:
    st.warning("Lista de apurados vazia.")
