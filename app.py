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

# Inicialização do estado
if "itens_orcamento" not in st.session_state:
    st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])

# 2. CABEÇALHO E DADOS DO CLIENTE
col_log, col_cli, col_rasc = st.columns([1.2, 2.5, 1.2])

with col_log:
    if os.path.exists("logo.png"): 
        st.image("logo.png", width=180)

with col_cli:
    st.subheader("📋 Dados do Cliente")
    nome_cli = st.text_input("Nome do Cliente", key="nome_cli")
    morada_cli = st.text_input("Morada", key="morada_cli")
    c1, c2 = st.columns(2)
    tel_cli = c1.text_input("Telefone", key="tel_cli")
    email_cli = c2.text_input("Email do Cliente", key="email_cli")
    obs_cli = st.text_area("Notas / Observações", key="obs_cli")

with col_rasc:
    st.subheader("💾 Backup / Rascunho")
    n_orc = st.text_input("Nº Orçamento", value=f"ORC-{date.today().year}-001")
    
    dados_backup = {
        "cliente": {"nome": nome_cli, "morada": morada_cli, "tel": tel_cli, "email": email_cli, "obs": obs_cli, "n_orc": n_orc},
        "itens": st.session_state.itens_orcamento.to_dict(orient="records")
    }
    st.download_button("📥 Guardar Backup", data=json.dumps(dados_backup), file_name=f"backup_{n_orc}.json", use_container_width=True)
    
    u_backup = st.file_uploader("📂 Upload", type="json", label_visibility="collapsed")
    if u_backup:
        carregados = json.load(u_backup)
        st.session_state.itens_orcamento = pd.DataFrame(carregados["itens"])
        st.success("Carregado!")
        st.rerun()

st.divider()

# --- 3. ADIÇÃO DE ITENS (FIX: TUDO NUMA LINHA COM ATUALIZAÇÃO REAL-TIME) ---
st.subheader("🔍 1. Adicionar Itens")
base = carregar_base()
lista_artigos = base.apply(lambda x: f"{x['CÓDIGO']} - {x['DESCRIÇÃO']}", axis=1).tolist()

# Criamos as colunas idênticas à tua imagem preferida
c_sel, c_uni, c_pre, c_qtd, c_add = st.columns([3, 0.6, 0.8, 0.8, 1])

with c_sel:
    escolha = st.selectbox("Artigo:", options=[""] + lista_artigos, index=0)

# Procuramos os dados da base assim que o utilizador seleciona
unid_val = ""
preco_val = ""

if escolha:
    codigo_extraido = escolha.split(" - ")[0]
    # Filtra a base para buscar unidade e preço
    dados_item = base[base["CÓDIGO"] == codigo_extraido].iloc[0]
    unid_val = str(dados_item["UNID"])
    preco_val = f"{float(dados_item['Preço Unitário']):.2f} €"

with c_uni:
    st.text_input("Unid.", value=unid_val, disabled=True, key="preview_unid")

with c_pre:
    st.text_input("Preço Unit.", value=preco_val, disabled=True, key="preview_preco")

with c_qtd:
    qtd_val = st.number_input("Qtd", min_value=0.01, value=1.0, step=0.5, key="input_qtd")

with c_add:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    btn_add = st.button("✅ Adicionar", use_container_width=True)

if btn_add and escolha:
    row = base[base["CÓDIGO"] == escolha.split(" - ")[0]].iloc[0]
    novo = pd.DataFrame([{
        "CÓDIGO": row["CÓDIGO"], 
        "Artigo": row["DESCRIÇÃO"], 
        "UNID": row["UNID"], 
        "Preço Unitário": float(row["Preço Unitário"]), 
        "Quantidade": qtd_val
    }])
    st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo], ignore_index=True)
    st.rerun()

st.divider()

# --- SECÇÃO 2: ITEM EXTRA (MANUAL) ---
st.subheader("✍️ 2. Item Extra (Manual)")
c_art_ex, c_uni_ex, c_pre_ex, c_qtd_ex, c_add_ex = st.columns([3, 0.6, 0.8, 0.8, 1])

with c_art_ex:
    artigo_extra = st.text_input("Descrição do Artigo Extra:", placeholder="Ex: Mão-de-obra...")
with c_uni_ex:
    unidade_extra = st.text_input("Unid:", key="uni_manual")
with c_pre_ex:
    preco_extra = st.number_input("Preço (€):", min_value=0.0, key="pre_manual")
with c_qtd_ex:
    qtd_extra = st.number_input("Qtd:", min_value=0.01, value=1.0, key="qtd_manual")
with c_add_ex:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("➕ Adicionar Extra", use_container_width=True):
        if artigo_extra:
            novo_ex = pd.DataFrame([{
                "CÓDIGO": "EXTRA", "Artigo": artigo_extra, "UNID": unidade_extra, 
                "Preço Unitário": float(preco_extra), "Quantidade": qtd_extra
            }])
            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo_ex], ignore_index=True)
            st.rerun()

# 4. RESUMO E GESTÃO DE IVA
st.divider()
if not st.session_state.itens_orcamento.empty:
    st.markdown("### 📋 Resumo do Orçamento")
    
    col_iva_sel, _ = st.columns([1, 4])
    taxa_iva = col_iva_sel.selectbox("Taxa de IVA:", [23, 13, 6, 0], format_func=lambda x: f"{x}%" if x > 0 else "Isento")

    df_final = st.session_state.itens_orcamento.copy()
    df_final["Subtotal"] = df_final["Quantidade"] * df_final["Preço Unitário"]
    
    df_editado = st.data_editor(
        df_final,
        column_config={
            "Preço Unitário": st.column_config.NumberColumn("Preço Unitário", format="%.2f €"),
            "Subtotal": st.column_config.NumberColumn("Subtotal", format="%.2f €"),
            "Quantidade": st.column_config.NumberColumn("Quantidade", format="%.2f"),
        },
        use_container_width=True, hide_index=True, num_rows="dynamic"
    )
    
    st.session_state.itens_orcamento = df_editado[["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"]]
    
    sub_val = df_editado["Subtotal"].sum()
    iva_val = sub_val * (taxa_iva / 100)
    total_val = sub_val + iva_val

    # Função PDF (Mantida conforme o teu padrão original)
    def criar_pdf(df, sub, iva_v, total_f, taxa):
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20, bottomMargin=20)
        sty = getSampleStyleSheet()
        est_tab = sty['Normal']
        est_tab.fontSize = 8
        elems = []
        if os.path.exists("logo.png"):
            img = RLImage("logo.png", width=1.5*inch, height=0.8*inch)
            img.hAlign = 'LEFT'
            elems.append(img)
        elems.append(Paragraph(f"ORÇAMENTO: {n_orc}", sty['Title']))
        elems.append(Spacer(1, 15))
        cli_info = f"<b>Cliente:</b> {nome_cli}<br/><b>Morada:</b> {morada_cli}<br/><b>Email:</b> {email_cli}"
        elems.append(Paragraph(cli_info, sty['Normal']))
        elems.append(Spacer(1, 15))
        data = [["Artigo / Descrição", "Qtd", "Unid", "Preço Unit.", "Total"]]
        for _, r in df.iterrows():
            data.append([Paragraph(str(r['Artigo']), est_tab), f"{r['Quantidade']:.2f}", r['UNID'], f"{r['Preço Unitário']:.2f}€", f"{r['Subtotal']:.2f}€"])
        num_itens = len(df)
        data.append(["", "", "", "SUBTOTAL:", f"{sub:,.2f}€"])
        data.append(["", "", "", f"IVA ({taxa}%):", f"{iva_v:,.2f}€"])
        data.append(["", "", "", "TOTAL FINAL:", f"{total_f:,.2f}€"])
        t = Table(data, colWidths=[280, 45, 45, 75, 75])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), AZUL_LOGO),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (1,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1, num_itens), 0.5, colors.grey),
            ('BACKGROUND', (3, -1), (4, -1), colors.lightgrey),
        ]))
        elems.append(t)
        if obs_cli:
            elems.append(Spacer(1, 20))
            elems.append(Paragraph(f"<b>Observações:</b><br/>{obs_cli}", sty['Normal']))
        doc.build(elems)
        return buf.getvalue()

    c1, c2, c3 = st.columns(3)
    c1.download_button("📥 Baixar PDF", data=criar_pdf(df_editado, sub_val, iva_val, total_val, taxa_iva), file_name=f"{n_orc}.pdf", use_container_width=True)
    buf_x = io.BytesIO()
    with pd.ExcelWriter(buf_x, engine='xlsxwriter') as wr:
        df_editado.to_excel(wr, index=False)
    c2.download_button("📊 Baixar Excel", data=buf_x.getvalue(), file_name=f"{n_orc}.xlsx", use_container_width=True)
    if c3.button("🗑️ Limpar Tudo", use_container_width=True):
        st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])
        st.rerun()
