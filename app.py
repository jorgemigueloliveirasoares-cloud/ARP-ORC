import streamlit as st
import pandas as pd
import os
import io
import json
from datetime import date

# Bibliotecas para PDF (ReportLab)
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

# --------------------------------------------------
# 1. CONFIGURAÇÃO E CARREGAMENTO DE DADOS
# --------------------------------------------------
st.set_page_config(page_title="Gestor de Orçamentos Pro", layout="wide")

@st.cache_data
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

if "itens_orcamento" not in st.session_state:
    st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])

# --------------------------------------------------
# 2. CABEÇALHO: LOGO, CLIENTE E RASCUNHO
# --------------------------------------------------
col_log, col_cli, col_rasc = st.columns([1.2, 2.5, 1.2])

with col_log:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=180)
    else:
        st.warning("⚠️ logo.png não encontrado.")

with col_cli:
    st.markdown("### 📋 Dados do Cliente")
    nome_cli = st.text_input("Nome do Cliente", key="nome_cli")
    morada_cli = st.text_input("Morada", key="morada_cli")
    c1, c2 = st.columns(2)
    tel_cli = c1.text_input("Telefone", key="tel_cli")
    email_cli = c2.text_input("Email", key="email_cli")
    obs_cli = st.text_area("Notas / Observações (Aparecem no PDF)", key="obs_cli", height=80)

with col_rasc:
    st.markdown("### 💾 Gestão de Rascunhos")
    n_orc = st.text_input("Nº Orçamento", value=f"ORC-{date.today().year}-{date.today().month:02d}-001")
    
    # Botão para Guardar rascunho em JSON (Inclui Notas agora)
    dados_rasc = {
        "cliente": {
            "nome": nome_cli, "morada": morada_cli, "tel": tel_cli, 
            "email": email_cli, "n_orc": n_orc, "obs": obs_cli
        },
        "itens": st.session_state.itens_orcamento.to_dict(orient="records")
    }
    st.download_button("📥 Guardar Rascunho (JSON)", data=json.dumps(dados_rasc), 
                       file_name=f"Rascunho_{n_orc}.json", mime="application/json", use_container_width=True)
    
    # Upload para carregar rascunho
    u_rasc = st.file_uploader("📂 Carregar Rascunho", type="json", label_visibility="collapsed")
    if u_rasc:
        carregados = json.load(u_rasc)
        st.session_state.itens_orcamento = pd.DataFrame(carregados["itens"])
        st.success("Rascunho carregado!")

st.divider()

# --------------------------------------------------
# 3. ADIÇÃO DE ITENS (EXCEL VS MANUAL)
# --------------------------------------------------
st.subheader("🔍 1. Adicionar Itens ao Orçamento")
t1, t2 = st.tabs(["🔎 Pesquisar no Excel", "➕ Criar Artigo Manual"])

with t1:
    termo = st.text_input("Procurar (nome ou código):", key="search").strip()
    if termo:
        base = carregar_base()
        mask = (base["DESCRIÇÃO"].str.contains(termo, case=False, na=False)) | (base["CÓDIGO"].str.contains(termo, case=False, na=False))
        res = base[mask].head(12)
        if not res.empty:
            for i, row in res.iterrows():
                c1, c2, c3, c4, c5 = st.columns([1, 4, 1, 1, 0.5])
                c1.write(f"**{row['CÓDIGO']}**")
                c2.write(row["DESCRIÇÃO"])
                c3.write(f"{row['Preço Unitário']:.2f}€")
                qtd_tx = c4.text_input("Qtd", key=f"q_{row['CÓDIGO']}", label_visibility="collapsed", placeholder="0")
                if c5.button("➕", key=f"b_{row['CÓDIGO']}"):
                    if qtd_tx:
                        v = float(qtd_tx.replace(',', '.'))
                        novo = pd.DataFrame([{"CÓDIGO": row["CÓDIGO"], "Artigo": row["DESCRIÇÃO"], "UNID": row["UNID"], "Preço Unitário": row["Preço Unitário"], "Quantidade": v}])
                        st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo], ignore_index=True)
                        st.rerun()

with t2:
    m1, m2, m3, m4, m5, m6 = st.columns([1, 3, 1, 1, 1, 1])
    m_cod = m1.text_input("Cód", value="EXTRA")
    m_desc = m2.text_input("Descrição do Item")
    m_unid = m3.text_input("Unid", value="un")
    m_prec = m4.number_input("Preço €", min_value=0.0)
    m_qtd = m5.number_input("Qtd", min_value=0.0)
    if m6.button("Adicionar", use_container_width=True):
        if m_desc and m_qtd > 0:
            novo_m = pd.DataFrame([{"CÓDIGO": m_cod, "Artigo": m_desc, "UNID": m_unid, "Preço Unitário": m_prec, "Quantidade": m_qtd}])
            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo_m], ignore_index=True)
            st.rerun()

# --------------------------------------------------
# 4. TABELA DE APURADOS E TOTAIS
# --------------------------------------------------
st.divider()
st.subheader("📝 2. Itens Apurados")

if not st.session_state.itens_orcamento.empty:
    df_v = st.session_state.itens_orcamento.copy()
    df_v["Subtotal (€)"] = df_v["Quantidade"] * df_v["Preço Unitário"]
    
    df_editado = st.data_editor(df_v, use_container_width=True, hide_index=True,
        column_config={
            "CÓDIGO": st.column_config.TextColumn("Cód", disabled=True),
            "Artigo": st.column_config.TextColumn("Descrição", disabled=True),
            "Subtotal (€)": st.column_config.NumberColumn("Subtotal", format="%.2f", disabled=True)
        }, key="editor_final")
    
    total_g = df_editado["Subtotal (€)"].sum()
    st.markdown(f"## **Total Geral: {total_g:,.2f} €**")

    # --------------------------------------------------
    # 5. GERAÇÃO DE PDF COM LOGO E OBSERVAÇÕES
    # --------------------------------------------------
    col_pdf, col_xls, col_del = st.columns(3)

    def criar_pdf(df, total):
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20)
        sty = getSampleStyleSheet()
        elems = []
        
        # 1. Logo
        if os.path.exists("logo.png"):
            logo = RLImage("logo.png", width=1.5*inch, height=0.8*inch)
            logo.hAlign = 'LEFT'
            elems.append(logo)
        
        # 2. Título e Dados Cliente
        elems.append(Paragraph(f"<b>ORÇAMENTO: {n_orc}</b>", sty['Title']))
        elems.append(Spacer(1, 12))
        elems.append(Paragraph(f"<b>Cliente:</b> {nome_cli}<br/><b>Morada:</b> {morada_cli}<br/><b>Tel:</b> {tel_cli}", sty['Normal']))
        elems.append(Spacer(1, 15))
        
        # 3. Tabela de Preços
        data = [["Cód", "Artigo", "Qtd", "Unid", "Preço Unit.", "Subtotal"]]
        for _, r in df.iterrows():
            data.append([r['CÓDIGO'], r['Artigo'][:55], f"{r['Quantidade']}", r['UNID'], f"{r['Preço Unitário']:.2f}€", f"{r['Subtotal (€)']:.2f}€"])
        data.append(["", "", "", "", "<b>TOTAL:</b>", f"<b>{total:,.2f}€</b>"])
        
        t = Table(data, colWidths=[60, 230, 40, 40, 70, 70])
        t.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (2,0), (-1,-1), 'CENTER'),
            ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ]))
        elems.append(t)
        
        # 4. Observações (Novidade)
        if obs_cli:
            elems.append(Spacer(1, 20))
            elems.append(Paragraph("<b>Observações / Condições:</b>", sty['Normal']))
            elems.append(Spacer(1, 5))
            # Substituir quebras de linha para o PDF
            obs_formatada = obs_cli.replace('\n', '<br/>')
            elems.append(Paragraph(obs_formatada, sty['Normal']))
        
        doc.build(elems)
        return buf.getvalue()

    with col_pdf:
        st.download_button("📥 Gerar PDF Completo", data=criar_pdf(df_editado, total_g), file_name=f"Orcamento_{nome_cli}.pdf", use_container_width=True)

    with col_xls:
        buf_x = io.BytesIO()
        with pd.ExcelWriter(buf_x, engine='xlsxwriter') as wr:
            df_editado.to_excel(wr, index=False)
        st.download_button("📊 Gerar Excel", data=buf_x.getvalue(), file_name=f"Orcamento_{nome_cli}.xlsx", use_container_width=True)

    with col_del:
        if st.button("🗑️ Limpar Tudo"):
            st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])
            st.rerun()

    if st.button("💾 Atualizar Totais"):
        st.session_state.itens_orcamento = df_editado[["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"]]
        st.rerun()
