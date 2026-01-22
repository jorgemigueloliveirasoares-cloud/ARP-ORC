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

# 1. Configuração Estética
st.set_page_config(page_title="Orçamentador Pro", layout="wide")

LOGO_PATH = "logo.png" 
EXCEL_PATH = "Cópia de Preços Tabela atual.xlsx"

# Exibição do Logo na Web
if os.path.exists(LOGO_PATH):
    st.image(LOGO_PATH, width=250)

st.title("📐 Sistema de Orçamentação Web")

# 2. Lógica de Carregamento Automático
def carregar_base():
    if os.path.exists(EXCEL_PATH):
        try:
            df = pd.read_excel(EXCEL_PATH)
            # Ajuste exato das colunas conforme o seu ficheiro
            colunas = ["CÓDIGO", "DESCRIÇÃO", "UNID", "VALORES ATUAIS JANEIRO 2025"]
            df = df[colunas].dropna(subset=["DESCRIÇÃO"])
            df.rename(columns={"VALORES ATUAIS JANEIRO 2025": "Preço Unitário"}, inplace=True)
            df["Quantidade"] = 0.0
            return df
        except Exception as e:
            st.error(f"Erro ao ler Excel: {e}")
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário", "Quantidade"])

if "dados" not in st.session_state:
    st.session_state["dados"] = carregar_base()

# 3. Sidebar: Informações do Cliente
with st.sidebar:
    st.header("📋 Dados do Cliente")
    cliente = st.text_input("Cliente", "Consumidor Final")
    obra = st.text_input("Obra", "Reabilitação")
    data_orc = st.date_input("Data", value=date.today())
    iva_percent = st.selectbox("IVA (%)", [0, 6, 13, 23], index=3)

# 4. Campo para Itens Manuais
st.subheader("➕ Adicionar item personalizado")
with st.expander("Clique para definir um item que não existe na tabela"):
    c1, c2, c3, c4 = st.columns([1, 3, 1, 1])
    n_cod = c1.text_input("Cód")
    n_des = c2.text_input("Descrição")
    n_uni = c3.text_input("Unid")
    n_pre = c4.number_input("Preço (€)", min_value=0.0, format="%.2f")
    
    if st.button("Inserir na Lista"):
        if n_des:
            novo = pd.DataFrame([{"CÓDIGO": n_cod, "DESCRIÇÃO": n_des, "UNID": n_uni, "Preço Unitário": n_pre, "Quantidade": 0.0}])
            st.session_state["dados"] = pd.concat([st.session_state["dados"], novo], ignore_index=True)
            st.success("Item adicionado!")
            st.rerun()

# 5. Pesquisa e Edição da Tabela
pesquisa = st.text_input("🔍 Pesquisar na base de dados...")
df_f = st.session_state["dados"]
mask = df_f["DESCRIÇÃO"].str.contains(pesquisa, case=False, na=False) | \
       df_f["CÓDIGO"].astype(str).str.contains(pesquisa, case=False, na=False)

# Mostra o que foi pesquisado + o que já tem quantidade > 0
df_view = df_f[mask | (df_f["Quantidade"] > 0)].copy()

edited_df = st.data_editor(
    df_view,
    column_config={
        "Preço Unitário": st.column_config.NumberColumn("Preço (€)", format="%.2f"),
        "Quantidade": st.column_config.NumberColumn("Qtd", min_value=0.0, step=0.1)
    },
    hide_index=True, use_container_width=True
)

# Sincronizar edições
for idx in edited_df.index:
    st.session_state["dados"].at[idx, "Quantidade"] = edited_df.loc[idx, "Quantidade"]
    st.session_state["dados"].at[idx, "Preço Unitário"] = edited_df.loc[idx, "Preço Unitário"]

# 6. Cálculos e Exportação PDF
itens_finais = st.session_state["dados"][st.session_state["dados"]["Quantidade"] > 0].copy()

if not itens_finais.empty:
    itens_finais["Total"] = itens_finais["Quantidade"] * itens_finais["Preço Unitário"]
    subtotal = itens_finais["Total"].sum()
    valor_iva = subtotal * (iva_percent/100)
    total_geral = subtotal + valor_iva

    st.divider()
    col_a, col_b = st.columns(2)
    col_a.metric("Subtotal", f"{subtotal:,.2f} €")
    col_b.metric("TOTAL COM IVA", f"{total_geral:,.2f} €")

    if st.button("📄 Gerar Orçamento PDF"):
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Logo no PDF
        if os.path.exists(LOGO_PATH):
            img = Image(LOGO_PATH, width=120, height=60)
            img.hAlign = 'CENTER'
            elements.append(img)
            elements.append(Spacer(1, 15))

        # Título e Cabeçalho
        title_st = ParagraphStyle('T', parent=styles['Title'], alignment=TA_CENTER)
        elements.append(Paragraph(f"ORÇAMENTO: {obra}", title_st))
        elements.append(Paragraph(f"<b>Cliente:</b> {cliente}<br/><b>Data:</b> {data_orc}", styles['Normal']))
        elements.append(Spacer(1, 20))

        # Tabela
        data = [["Cód", "Descrição", "Un", "Qtd", "Preço", "Total"]]
        for _, r in itens_finais.iterrows():
            data.append([r["CÓDIGO"], r["DESCRIÇÃO"][:55], r["UNID"], f"{r['Quantidade']:.2f}", f"{r['Preço Unitário']:.2f}€", f"{r['Total']:.2f}€"])
        
        data.append(["", "", "", "", "TOTAL:", f"{total_geral:,.2f}€"])

        table = Table(data, colWidths=[40, 240, 30, 40, 70, 70])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f2f2f2")),
            ('GRID', (0,0), (-1,-2), 0.5, colors.grey),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        elements.append(table)
        
        doc.build(elements)
        st.download_button("⬇️ Descarregar PDF", pdf_buffer.getvalue(), f"Orcamento_{cliente}.pdf")
