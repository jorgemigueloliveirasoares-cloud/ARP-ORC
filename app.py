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

# 1. CONFIGURAÇÃO INICIAL
st.set_page_config(page_title="Orçamentador Pro", layout="wide")
AZUL_LOGO = colors.Color(0/255, 115/255, 180/255) 

@st.cache_data(ttl=600)
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
            df["Preço Unitário"] = pd.to_numeric(df["Preço Unitário"], errors='coerce').fillna(0.0)
            return df
        except Exception as e:
            st.error(f"Erro ao ler Excel: {e}")
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário"])

if "itens_orcamento" not in st.session_state:
    st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])

# 2. CABEÇALHO E DADOS DO CLIENTE
col_log, col_cli, col_rasc = st.columns([1.2, 2.5, 1.2])
with col_log:
    if os.path.exists("logo.png"): st.image("logo.png", width=180)
with col_cli:
    st.subheader("📋 Dados do Cliente")
    nome_cli = st.text_input("Nome do Cliente")
    morada_cli = st.text_input("Morada")
    c1, c2 = st.columns(2)
    tel_cli = c1.text_input("Telefone")
    email_cli = c2.text_input("Email")
with col_rasc:
    st.subheader("💾 Backup")
    n_orc = st.text_input("Nº Orçamento", value=f"ORC-{date.today().year}-001")
    dados_backup = {"cliente": {"nome": nome_cli, "n_orc": n_orc}, "itens": st.session_state.itens_orcamento.to_dict(orient="records")}
    st.download_button("📥 Backup", data=json.dumps(dados_backup), file_name=f"{n_orc}.json", use_container_width=True)

st.divider()

# 3. ADIÇÃO DE ITENS (MELHORADO PARA ITENS FORA DA TABELA)
st.subheader("🔍 1. Adicionar Itens")
base = carregar_base()
lista_artigos = base.apply(lambda x: f"{x['CÓDIGO']} - {x['DESCRIÇÃO']}", axis=1).tolist()

# Linha de entrada principal
col_pesq, col_unid, col_prec, col_qtd, col_btn = st.columns([2.5, 0.5, 0.7, 0.6, 1])

with col_pesq:
    escolha = st.selectbox("Pesquise na tabela ou escreva um item novo:", options=[""] + lista_artigos, index=0)
    # Se não escolheu nada da lista, permite escrever manual (opcional visual)
    item_manual = st.text_input("Ou descreva um item novo aqui (se não estiver na lista):", key="manual_txt")

with col_unid:
    unid_input = st.text_input("Unid", value="un")

with col_prec:
    # Se escolher da lista, o preço é automático, senão é manual
    preco_sugerido = 0.0
    if escolha:
        cod_sel = escolha.split(" - ")[0]
        preco_sugerido = float(base[base["CÓDIGO"] == cod_sel]["Preço Unitário"].values[0])
        unid_input = str(base[base["CÓDIGO"] == cod_sel]["UNID"].values[0])
    
    preco_input = st.number_input("Preço €", min_value=0.0, value=preco_sugerido, step=0.01, format="%.2f")

with col_qtd:
    qtd_input = st.number_input("Qtd", min_value=0.01, value=1.0)

with col_btn:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    add_click = st.button("✅ Adicionar", use_container_width=True)

if add_click:
    # Lógica de decisão: Prioridade para a lista, depois para o texto manual
    desc_final = ""
    cod_final = "EXTRA"
    
    if escolha:
        cod_final = escolha.split(" - ")[0]
        desc_final = escolha.split(" - ", 1)[1]
    elif item_manual:
        desc_final = item_manual
        cod_final = "MANUAL"
    
    if desc_final:
        novo_item = pd.DataFrame([{
            "CÓDIGO": cod_final,
            "Artigo": desc_final,
            "UNID": unid_input,
            "Preço Unitário": preco_input,
            "Quantidade": qtd_input
        }])
        st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo_item], ignore_index=True)
        st.toast(f"Item adicionado!", icon="✔️")
        st.rerun()
    else:
        st.error("Por favor, selecione um artigo ou escreva uma descrição.")

# 4. RESUMO, IVA E PDF
st.divider()
if not st.session_state.itens_orcamento.empty:
    st.markdown("### 📋 Resumo")
    col_iva, _ = st.columns([1, 4])
    taxa_iva = col_iva.selectbox("IVA:", [23, 13, 6, 0], format_func=lambda x: f"{x}%" if x > 0 else "Isento")

    df_exibicao = st.session_state.itens_orcamento.copy()
    df_exibicao["Subtotal"] = df_exibicao["Quantidade"] * df_exibicao["Preço Unitário"]
    
    df_editado = st.data_editor(df_exibicao, use_container_width=True, hide_index=True)
    st.session_state.itens_orcamento = df_editado[["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"]]
    
    sub_total = df_editado["Subtotal"].sum()
    v_iva = sub_total * (taxa_iva / 100)
    total_g = sub_total + v_iva

    c_t1, c_t2, c_t3 = st.columns(3)
    c_t1.metric("Subtotal", f"{sub_total:,.2f}€")
    c_t2.metric(f"IVA ({taxa_iva}%)", f"{v_iva:,.2f}€")
    c_t3.metric("TOTAL", f"{total_g:,.2f}€")

    def gerar_pdf(df, sub, iva, tot, tx):
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4)
        sty = getSampleStyleSheet()
        elems = []
        if os.path.exists("logo.png"):
            img = RLImage("logo.png", width=1.5*inch, height=0.8*inch)
            img.hAlign = 'LEFT'
            elems.append(img)
        elems.append(Paragraph(f"ORÇAMENTO: {n_orc}", sty['Title']))
        elems.append(Spacer(1, 10))
        elems.append(Paragraph(f"<b>Cliente:</b> {nome_cli}<br/><b>Email:</b> {email_cli}", sty['Normal']))
        elems.append(Spacer(1, 15))
        
        data = [["Descrição", "Qtd", "Unid", "Preço Unit.", "Total"]]
        for _, r in df.iterrows():
            data.append([Paragraph(r['Artigo'], sty['Normal']), f"{r['Quantidade']:.2f}", r['UNID'], f"{r['Preço Unitário']:.2f}€", f"{(r['Quantidade']*r['Preço Unitário']):.2f}€"])
        
        data.append(["", "", "", "SUBTOTAL:", f"{sub:,.2f}€"])
        data.append(["", "", "", f"IVA ({tx}%):", f"{iva:,.2f}€"])
        data.append(["", "", "", "TOTAL FINAL:", f"{tot:,.2f}€"])
        
        t = Table(data, colWidths=[280, 45, 45, 75, 75])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), AZUL_LOGO),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (3,0), (4,-1), 'RIGHT'),
            ('GRID', (0,0), (-1, len(df)), 0.5, colors.grey),
            ('FONTNAME', (3, -1), (3, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (3,-1), (4,-1), colors.lightgrey),
        ]))
        elems.append(t)
        doc.build(elems)
        return buf.getvalue()

    st.download_button("📥 Descarregar PDF Profissional", data=gerar_pdf(df_editado, sub_total, v_iva, total_g, taxa_iva), file_name=f"{n_orc}.pdf", use_container_width=True)
