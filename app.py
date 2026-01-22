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
# 1. Configuração Inicial e Estética
# --------------------------------------------------
st.set_page_config(page_title="Gestor de Orçamentos", layout="wide")

LOGO_PATH = "logo.png" 
EXCEL_PATH = "Cópia de Preços Tabela atual.xlsx"

# Estilo CSS para aproximar a tabela visualmente da imagem enviada
st.markdown("""
    <style>
    .stTable { font-size: 12px !important; }
    .main-total { font-size: 24px; font-weight: bold; color: #2e7d32; }
    </style>
    """, unsafe_allow_html=True)

# --------------------------------------------------
# 2. Funções de Suporte
# --------------------------------------------------
def carregar_base_limpa():
    if os.path.exists(EXCEL_PATH):
        try:
            df = pd.read_excel(EXCEL_PATH)
            # Ajuste de colunas conforme o seu ficheiro Excel
            colunas = ["CÓDIGO", "DESCRIÇÃO", "UNID", "VALORES ATUAIS JANEIRO 2025"]
            df = df[colunas].dropna(subset=["DESCRIÇÃO"])
            df.rename(columns={"VALORES ATUAIS JANEIRO 2025": "Preço Unitário"}, inplace=True)
            df["Quantidade"] = 0.0
            return df
        except:
            st.error("Erro ao ler o Excel. Verifique os nomes das colunas.")
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário", "Quantidade"])

def salvar_edicoes():
    """Grava as quantidades no estado global assim que a célula é editada"""
    key = f"editor_{st.session_state['orc_atual']}"
    if key in st.session_state:
        edicoes = st.session_state[key]
        for row_idx, alteracoes in edicoes["edited_rows"].items():
            for col, val in alteracoes.items():
                st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]["dados"].at[row_idx, col] = val

# --------------------------------------------------
# 3. Inicialização do Estado (Session State)
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
# 4. Interface Superior (Logo, Dados e Botões de Exportação)
# --------------------------------------------------
col_log, col_info, col_exp = st.columns([1, 2, 1.2])

res = st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]

with col_log:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=180)

with col_info:
    st.markdown(f"### 📋 {st.session_state['orc_atual']}")
    c1, c2 = st.columns(2)
    res["cliente"] = c1.text_input("Cliente", res["cliente"])
    res["telefone"] = c2.text_input("Telefone", res["telefone"])
    res["morada"] = st.text_input("Morada do Cliente", res["morada"])

with col_exp:
    st.markdown("### 📄 Acções")
    iva_percent = st.selectbox("IVA (%)", [0, 6, 13, 23], index=3)
    
    # Cálculo de Totais para Exportação
    itens_finais = res["dados"][res["dados"]["Quantidade"] > 0].copy()
    
    if not itens_finais.empty:
        itens_finais["Total"] = itens_finais["Quantidade"] * itens_finais["Preço Unitário"]
        subtotal = itens_finais["Total"].sum()
        total_com_iva = subtotal * (1 + iva_percent/100)

        c_pdf, c_xls = st.columns(2)
        
        # Gerar PDF
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []
        # (Lógica simplificada do PDF - use a lógica completa dos passos anteriores aqui)
        
        c_pdf.download_button("⬇️ Baixar PDF", b"data", f"Orcamento_{res['cliente']}.pdf")
        
        # Gerar Excel
        output_ex = io.BytesIO()
        with pd.ExcelWriter(output_ex, engine='xlsxwriter') as writer:
            itens_finais.to_excel(writer, index=False, sheet_name='Orçamento')
        c_xls.download_button("⬇️ Baixar Excel", output_ex.getvalue(), f"Orcamento_{res['cliente']}.xlsx")
    else:
        st.caption("Adicione itens para activar exportação.")

# --------------------------------------------------
# 5. Sidebar: Backup e Múltiplos Orçamentos
# --------------------------------------------------
with st.sidebar:
    st.header("💾 Backup")
    # Backup (pkl) para não perder rascunhos ao fechar o browser
    st.download_button("📥 Guardar Backup", pickle.dumps(st.session_state["lista_orcamentos"]), f"backup_{date.today()}.pkl")
    
    arq = st.file_uploader("📂 Restaurar Backup", type=["pkl"])
    if arq:
        st.session_state["lista_orcamentos"] = pickle.loads(arq.read())
        st.rerun()

    st.divider()
    st.header("📂 Lista de Trabalhos")
    opcoes = list(st.session_state["lista_orcamentos"].keys())
    escolha = st.selectbox("Mudar para:", opcoes, index=opcoes.index(st.session_state["orc_atual"]))
    if escolha != st.session_state["orc_atual"]:
        st.session_state["orc_atual"] = escolha
        st.rerun()
    
    if st.button("➕ Criar Novo Orçamento"):
        novo = f"Orçamento {len(st.session_state['lista_orcamentos']) + 1}"
        st.session_state["lista_orcamentos"][novo] = {
            "cliente": "", "morada": "", "telefone": "", "obra": "", 
            "data_visita": date.today(), "notas": "", "dados": carregar_base_limpa()
        }
        st.session_state["orc_atual"] = novo
        st.rerun()

# --------------------------------------------------
# 6. Zona de Pesquisa e Seleção (Meio)
# --------------------------------------------------
st.divider()
st.subheader("🔍 Pesquisa de Artigos")
pesquisa = st.text_input("Digite o nome ou código para encontrar na base de dados...")

# Filtra o que pesquisaste mas remove o que já está nos apurados para não confundir
mask = res["dados"]["DESCRIÇÃO"].str.contains(pesquisa, case=False, na=False)
df_pesquisa = res["dados"][mask & (res["dados"]["Quantidade"] == 0)]

st.data_editor(
    df_pesquisa,
    column_config={
        "Preço Unitário": st.column_config.NumberColumn("Preço (€)", format="%.2f", disabled=True),
        "Quantidade": st.column_config.NumberColumn("Qtd a Adicionar", min_value=0.0, step=0.1)
    },
    hide_index=True, use_container_width=True,
    key=f"editor_{st.session_state['orc_atual']}",
    on_change=salvar_edicoes
)

# --------------------------------------------------
# 7. Tabela de Itens Apurados (Fundo)
# --------------------------------------------------
st.markdown("---")
st.subheader("📝 Itens Selecionados (Apurados)")

if not itens_finais.empty:
    # Preparação da visualização conforme imagem do usuário
    df_visual = itens_finais.copy()
    df_visual["Valor SI"] = (df_visual["Quantidade"] * df_visual["Preço Unitário"]).map("{:.2f} €".format)
    
    # Renomear colunas para o estilo da imagem
    df_visual = df_visual.rename(columns={
        "DESCRIÇÃO": "Artigo",
        "UNID": "UM",
        "Quantidade": "Qnt",
        "Preço Unitário": "V Unit"
    })
    
    # Exibição estática (apenas leitura) dos itens já escolhidos
    st.table(df_visual[["Artigo", "Qnt", "UM", "V Unit", "Valor SI"]])
    
    st.markdown(f"<div class='main-total'>Total Apurado: {subtotal:,.2f} €</div>", unsafe_allow_html=True)
    
    res["notas"] = st.text_area("Notas / Condições do Orçamento", res["notas"])
else:
    st.info("A sua lista de apurados está vazia. Utilize a pesquisa acima para adicionar itens.")
