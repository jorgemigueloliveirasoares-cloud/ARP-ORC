import streamlit as st
import pandas as pd
import os
import io
import json
from datetime import date

# Bibliotecas para PDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# 1. CONFIGURAÇÃO
st.set_page_config(page_title="Orçamentador Pro", layout="wide")

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
            df["DESCRIÇÃO"] = df["DESCRIÇÃO"].astype(str).str.strip()
            return df
        except: pass
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário"])

# Inicialização de variáveis de sessão
if "itens_orcamento" not in st.session_state:
    st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])

# 2. CABEÇALHO E RASCUNHOS
col_log, col_cli, col_rasc = st.columns([1.2, 2.5, 1])

with col_log:
    if os.path.exists("logo.png"): st.image("logo.png", width=180)

with col_cli:
    st.markdown("### **Dados do Cliente**")
    nome_cli = st.text_input("Nome", key="n_c")
    morada_cli = st.text_input("Morada", key="m_c")
    c1, c2 = st.columns(2)
    tel_cli = c1.text_input("Telefone", key="t_c")
    email_cli = c2.text_input("Email", key="e_c")

with col_rasc:
    st.markdown("### **Gestão de Rascunho**")
    # Guardar rascunho
    dados_rascunho = {
        "cliente": {"nome": nome_cli, "morada": morada_cli, "tel": tel_cli, "email": email_cli},
        "itens": st.session_state.itens_orcamento.to_dict(orient="records")
    }
    st.download_button("💾 Guardar Rascunho", data=json.dumps(dados_rascunho), 
                       file_name=f"Rascunho_{nome_cli or 'sem_nome'}.json", mime="application/json", use_container_width=True)
    
    # Carregar rascunho
    upload_rasc = st.file_uploader("📂 Carregar Rascunho", type="json", label_visibility="collapsed")
    if upload_rasc:
        dados_carregados = json.load(upload_rasc)
        st.session_state.itens_orcamento = pd.DataFrame(dados_carregados["itens"])
        st.info("Rascunho carregado! Por favor, preencha os dados do cliente manualmente se necessário.")

st.divider()

# 3. ADIÇÃO DE ITENS (Igual ao anterior)
st.subheader("🔍 1. Adicionar Itens")
tab_pesq, tab_man = st.tabs(["🔎 Excel", "➕ Manual"])

with tab_pesq:
    termo = st.text_input("Procurar no Excel:", key="search").strip()
    if termo:
        base = carregar_base()
        mask = (base["DESCRIÇÃO"].str.contains(termo, case=False, na=False)) | (base["CÓDIGO"].str.contains(termo, case=False, na=False))
        res = base[mask].head(8)
        for i, row in res.iterrows():
            c1, c2, c3, c4, c5 = st.columns([1, 4, 1, 1, 0.5])
            c1.write(row["CÓDIGO"])
            c2.write(row["DESCRIÇÃO"])
            c3.write(f"{row['Preço Unitário']:.2f}€")
            q_in = c4.text_input("Qtd", key=f"q_{row['CÓDIGO']}", label_visibility="collapsed")
            if c5.button("➕", key=f"b_{row['CÓDIGO']}"):
                if q_in:
                    v = float(q_in.replace(',', '.'))
                    novo = pd.DataFrame([{"CÓDIGO": row["CÓDIGO"], "Artigo": row["DESCRIÇÃO"], "UNID": row["UNID"], "Preço Unitário": row["Preço Unitário"], "Quantidade": v}])
                    st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo], ignore_index=True)
                    st.rerun()

with tab_man:
    m1, m2, m3, m4, m5, m6 = st.columns([1, 3, 1, 1, 1, 1])
    mc = m1.text_input("Cód", value="EXTRA")
    md = m2.text_input("Descrição")
    mu = m3.text_input("Unid", value="un")
    mp = m4.number_input("Preço", min_value=0.0)
    mq = m5.number_input("Qtd", min_value=0.0)
    if m6.button("Adicionar"):
        if md and mq > 0:
            nm = pd.DataFrame([{"CÓDIGO": mc, "Artigo": md, "UNID": mu, "Preço Unitário": mp, "Quantidade": mq}])
            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, nm], ignore_index=True)
            st.rerun()

# 4. TABELA FINAL E EXPORTAÇÕES
st.divider()
if not st.session_state.itens_orcamento.empty:
    df_v = st.session_state.itens_orcamento.copy()
    df_v["Subtotal (€)"] = df_v["Quantidade"] * df_v["Preço Unitário"]
    
    df_editado = st.data_editor(df_v, use_container_width=True, hide_index=True, key="editor")
    total_g = df_editado["Subtotal (€)"].sum()
    st.markdown(f"## **Total: {total_g:,.2f} €**")

    # BOTÕES DE DOWNLOAD
    col_pdf, col_xls, col_del = st.columns(3)

    # PDF
    def criar_pdf(df, total):
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4)
        sty = getSampleStyleSheet()
        elems = [Paragraph(f"<b>ORÇAMENTO</b>", sty['Title']), Spacer(1, 12)]
        elems.append(Paragraph(f"Cliente: {nome_cli}<br/>Tel: {tel_cli}", sty['Normal']))
        
        data = [["Cód", "Artigo", "Qtd", "Preço", "Total"]]
        for _, r in df.iterrows():
            data.append([r['CÓDIGO'], r['Artigo'][:50], r['Quantidade'], f"{r['Preço Unitário']:.2f}€", f"{r['Subtotal (€)']:.2f}€"])
        data.append(["", "", "", "TOTAL:", f"{total:,.2f}€"])
        
        tab = Table(data, colWidths=[60, 260, 40, 60, 70])
        tab.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black), ('BACKGROUND', (0,0), (-1,0), colors.lightgrey)]))
        elems.append(tab)
        doc.build(elems)
        return buf.getvalue()

    col_pdf.download_button("📥 Baixar PDF", data=criar_pdf(df_editado, total_g), file_name="Orcamento.pdf", use_container_width=True)

    # Excel
    buf_x = io.BytesIO()
    with pd.ExcelWriter(buf_x, engine='xlsxwriter') as wr:
        df_editado.to_excel(wr, index=False)
    col_xls.download_button("📊 Baixar Excel", data=buf_x.getvalue(), file_name="Orcamento.xlsx", use_container_width=True)

    if col_del.button("🗑️ Limpar Tudo", use_container_width=True):
        st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])
        st.rerun()
