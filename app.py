import streamlit as st
import pandas as pd
import os
import io
from datetime import date

# Bibliotecas para PDF e Excel
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# --------------------------------------------------
# 1. CONFIGURAÇÃO E DADOS
# --------------------------------------------------
st.set_page_config(page_title="Orçamentador Pro", layout="wide")

LOGO_PATH = "logo.png"
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

if "itens_orcamento" not in st.session_state:
    st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])

# --------------------------------------------------
# 2. CABEÇALHO (DADOS DO CLIENTE)
# --------------------------------------------------
col_log, col_cli, col_num = st.columns([1.2, 2.5, 1])

with col_log:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=180)

with col_cli:
    st.markdown("### **Dados do Cliente**")
    nome_cli = st.text_input("Nome do Cliente", key="nome_cli")
    morada_cli = st.text_input("Morada", key="morada_cli")
    c1, c2 = st.columns(2)
    tel_cli = c1.text_input("Telefone", key="tel_cli")
    email_cli = c2.text_input("Email", key="email_cli")

with col_num:
    st.markdown("### **Identificação**")
    n_orc = st.text_input("Nº Orçamento", value=f"ORC-{date.today().year}-{date.today().month:02d}-001")
    data_emissao = st.date_input("Data", date.today())

st.divider()

# --------------------------------------------------
# 3. PESQUISA E SELECÇÃO (CÓDIGO ANTERIOR)
# --------------------------------------------------
termo = st.text_input("Pesquise por nome ou código:", key="search_bar").strip()
if termo:
    base = carregar_base()
    mask = (base["DESCRIÇÃO"].str.contains(termo, case=False, na=False)) | (base["CÓDIGO"].str.contains(termo, case=False, na=False))
    resultados = base[mask].head(10)
    for i, row in resultados.iterrows():
        c1, c2, c3, c4, c5 = st.columns([1, 4, 1, 1, 0.5])
        c1.write(row["CÓDIGO"])
        c2.write(row["DESCRIÇÃO"])
        c3.write(f"{row['Preço Unitário']:.2f}€")
        qtd_txt = c4.text_input("Qtd", key=f"q_{row['CÓDIGO']}", label_visibility="collapsed")
        if c5.button("➕", key=f"b_{row['CÓDIGO']}"):
            if qtd_txt:
                v = float(qtd_txt.replace(',', '.'))
                novo = pd.DataFrame([{"CÓDIGO": row["CÓDIGO"], "Artigo": row["DESCRIÇÃO"], "UNID": row["UNID"], "Preço Unitário": row["Preço Unitário"], "Quantidade": v}])
                st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo], ignore_index=True)
                st.rerun()

# --------------------------------------------------
# 4. TABELA DE APURADOS
# --------------------------------------------------
st.divider()
if not st.session_state.itens_orcamento.empty:
    df_v = st.session_state.itens_orcamento.copy()
    df_v["Subtotal (€)"] = df_v["Quantidade"] * df_v["Preço Unitário"]
    
    df_editado = st.data_editor(df_v, use_container_width=True, hide_index=True,
        column_config={
            "CÓDIGO": st.column_config.TextColumn("Cód", disabled=True),
            "Artigo": st.column_config.TextColumn("Descrição", disabled=True),
            "Subtotal (€)": st.column_config.NumberColumn("Subtotal", format="%.2f", disabled=True)
        }, key="editor")
    
    total_geral = df_editado["Subtotal (€)"].sum()
    st.markdown(f"## **Total Geral: {total_geral:,.2f} €**")

    # --------------------------------------------------
    # 5. BOTÕES DE EXPORTAÇÃO
    # --------------------------------------------------
    exp_pdf, exp_xls, exp_limpar = st.columns(3)

    # LÓGICA PDF
    with exp_pdf:
        def gerar_pdf():
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = []
            
            # Título e Cabeçalho
            elements.append(Paragraph(f"<b>ORÇAMENTO: {n_orc}</b>", styles['Title']))
            elements.append(Paragraph(f"Cliente: {nome_cli}<br/>Morada: {morada_cli}<br/>Tel: {tel_cli}<br/>Email: {email_cli}", styles['Normal']))
            elements.append(Spacer(1, 20))
            
            # Tabela de Itens
            dados_tabela = [["Cód", "Artigo", "Qtd", "V. Unit", "Subtotal"]]
            for _, r in df_editado.iterrows():
                dados_tabela.append([r['CÓDIGO'], r['Artigo'][:50], f"{r['Quantidade']}", f"{r['Preço Unitário']:.2f}€", f"{r['Subtotal (€)']:.2f}€"])
            
            dados_tabela.append(["", "", "", "TOTAL:", f"{total_geral:,.2f}€"])
            
            t = Table(dados_tabela, colWidths=[60, 250, 40, 70, 70])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ]))
            elements.append(t)
            doc.build(elements)
            return buffer.getvalue()

        st.download_button("📥 Gerar PDF", data=gerar_pdf(), file_name=f"{n_orc}.pdf", mime="application/pdf", use_container_width=True)

    # LÓGICA EXCEL
    with exp_xls:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_editado.to_excel(writer, index=False, sheet_name='Orçamento')
        st.download_button("📊 Gerar Excel", data=output.getvalue(), file_name=f"{n_orc}.xlsx", mime="application/vnd.ms-excel", use_container_width=True)

    with exp_limpar:
        if st.button("🗑️ Limpar Tudo", use_container_width=True):
            st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])
            st.rerun()
