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

# 1. CONFIGURAÇÃO
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

# 2. CABEÇALHO
col_log, col_cli, col_rasc = st.columns([1.2, 2.5, 1.2])
with col_log:
    if os.path.exists("logo.png"): st.image("logo.png", width=180)
with col_cli:
    nome_cli = st.text_input("Nome do Cliente")
    morada_cli = st.text_input("Morada")
    tel_cli = st.text_input("Telefone")
    obs_cli = st.text_area("Notas / Observações")
with col_rasc:
    n_orc = st.text_input("Nº Orçamento", value=f"ORC-{date.today().year}-001")
    # Botão de rascunho simplificado
    dados_rasc = {"cliente": {"nome": nome_cli, "obs": obs_cli}, "itens": st.session_state.itens_orcamento.to_dict(orient="records")}
    st.download_button("💾 Guardar Rascunho", data=json.dumps(dados_rasc), file_name="rascunho.json")

st.divider()

# 3. ADIÇÃO DE ITENS (CORREÇÃO DO ERRO DE QTD)
st.subheader("🔍 1. Adicionar Itens")
tab1, tab2 = st.tabs(["🔎 Excel", "➕ Manual"])

with tab1:
    termo = st.text_input("Pesquisar Artigo:", key="search_input").strip()
    if termo:
        base = carregar_base()
        res = base[(base["DESCRIÇÃO"].str.contains(termo, case=False)) | (base["CÓDIGO"].str.contains(termo, case=False))].head(10)
        for i, row in res.iterrows():
            c1, c2, c3, c4, c5 = st.columns([1, 4, 1, 1, 0.5])
            c1.write(row["CÓDIGO"])
            c2.write(row["DESCRIÇÃO"])
            c3.write(f"{row['Preço Unitário']:.2f}€")
            # Campo de quantidade
            qtd_input = c4.text_input("Qtd", key=f"input_{row['CÓDIGO']}", label_visibility="collapsed")
            # O botão só processa se for clicado
            if c5.button("➕", key=f"btn_{row['CÓDIGO']}"):
                if qtd_input:
                    try:
                        v = float(qtd_input.replace(',', '.'))
                        if v > 0:
                            novo = pd.DataFrame([{"CÓDIGO": row["CÓDIGO"], "Artigo": row["DESCRIÇÃO"], "UNID": row["UNID"], "Preço Unitário": row["Preço Unitário"], "Quantidade": v}])
                            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo], ignore_index=True)
                            st.rerun()
                    except ValueError:
                        st.error(f"Erro: '{qtd_input}' não é um número válido.")
                else:
                    st.warning("Insira uma quantidade primeiro.")

with tab2:
    m1, m2, m3, m4, m5 = st.columns([1, 3, 1, 1, 1])
    m_desc = m2.text_input("Descrição Manual")
    m_prec = m3.number_input("Preço €", min_value=0.0)
    m_qtd = m4.number_input("Qtd", min_value=0.0)
    if m5.button("Adicionar"):
        if m_desc and m_qtd > 0:
            nm = pd.DataFrame([{"CÓDIGO": "EXTRA", "Artigo": m_desc, "UNID": "un", "Preço Unitário": m_prec, "Quantidade": m_qtd}])
            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, nm], ignore_index=True)
            st.rerun()

# 4. TABELA E PDF
st.divider()
if not st.session_state.itens_orcamento.empty:
    df_final = st.session_state.itens_orcamento.copy()
    df_final["Subtotal"] = df_final["Quantidade"] * df_final["Preço Unitário"]
    st.data_editor(df_final, use_container_width=True, hide_index=True)
    total_val = df_final["Subtotal"].sum()
    st.write(f"### Total: {total_val:.2f}€")

    def criar_pdf_corrigido(df, total):
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4)
        sty = getSampleStyleSheet()
        elems = []
        if os.path.exists("logo.png"):
            img = RLImage("logo.png", width=1.5*inch, height=0.8*inch)
            img.hAlign = 'LEFT'
            elems.append(img)
        
        elems.append(Paragraph(f"ORCAMENTO: {n_orc}", sty['Title']))
        elems.append(Spacer(1, 20))
        
        # TABELA SEM TAGS HTML (CORREÇÃO DO ERRO DO TOTAL)
        data = [["Cód", "Artigo", "Qtd", "Preço", "Total"]]
        for _, r in df.iterrows():
            data.append([r['CÓDIGO'], r['Artigo'][:50], r['Quantidade'], f"{r['Preço Unitário']:.2f}€", f"{r['Subtotal']:.2f}€"])
        
        # Linha do Total limpa
        data.append(["", "", "", "TOTAL:", f"{total:.2f}€"])
        
        t = Table(data, colWidths=[60, 260, 40, 60, 70])
        t.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), # Negrito no cabeçalho
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'), # Negrito na linha do TOTAL
            ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
            ('ALIGN', (2,0), (-1,-1), 'CENTER'),
        ]))
        elems.append(t)
        
        if obs_cli:
            elems.append(Spacer(1, 20))
            elems.append(Paragraph(f"Observações: {obs_cli}", sty['Normal']))
            
        doc.build(elems)
        return buf.getvalue()

    st.download_button("📥 Baixar PDF", data=criar_pdf_corrigido(df_final, total_val), file_name="orcamento.pdf")
    if st.button("🗑️ Limpar"):
        st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])
        st.rerun()
