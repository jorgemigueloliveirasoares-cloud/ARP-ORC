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
st.set_page_config(page_title="JMOS V 1.1 - Orçamentador Pro", layout="wide")

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

# Inicialização do Estado
if "itens_orcamento" not in st.session_state:
    st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])
if "unid_preview" not in st.session_state:
    st.session_state.unid_preview = ""
if "preco_editavel" not in st.session_state:
    st.session_state.preco_editavel = 0.0

def atualizar_campos():
    escolha = st.session_state.sel_artigo
    if escolha:
        base = carregar_base()
        cod = escolha.split(" - ")[0]
        item = base[base["CÓDIGO"] == cod].iloc[0]
        st.session_state.unid_preview = str(item["UNID"])
        st.session_state.preco_editavel = float(item["Preço Unitário"])
    else:
        st.session_state.unid_preview = ""
        st.session_state.preco_editavel = 0.0

# --- CABEÇALHO JMOS V 1.1 ---
st.markdown("<h1 style='text-align: center; color: #0073B4;'>JMOS V 1.1</h1>", unsafe_allow_html=True)

if os.path.exists("logo.png"):
    col_l1, col_l2, col_l3 = st.columns([2, 1, 2])
    with col_l2:
        st.image("logo.png", use_container_width=True)

st.divider()

# 2. DADOS DO CLIENTE
col_cli, col_rasc = st.columns([3, 1.2])
with col_cli:
    st.subheader("📋 Dados do Cliente")
    nome_cli = st.text_input("Nome do Cliente")
    morada_cli = st.text_input("Morada")
    c1, c2 = st.columns(2)
    tel_cli = c1.text_input("Telefone")
    email_cli = c2.text_input("Email")
    obs_cli = st.text_area("Observações / Condições de Pagamento")

with col_rasc:
    st.subheader("💾 Sistema")
    n_orc = st.text_input("Nº Orçamento", value=f"ORC-{date.today().year}-001")
    dados_backup = {"cliente": {"nome": nome_cli, "n_orc": n_orc}, "itens": st.session_state.itens_orcamento.to_dict(orient="records")}
    st.download_button("📥 Guardar Rascunho", data=json.dumps(dados_backup), file_name=f"backup_{n_orc}.json", use_container_width=True)

st.divider()

# --- 3. ADIÇÃO DE ITENS ---
st.subheader("🔍 1. Adicionar Itens da Tabela")
base_dados = carregar_base()
lista_artigos = base_dados.apply(lambda x: f"{x['CÓDIGO']} - {x['DESCRIÇÃO']}", axis=1).tolist()

c_sel, c_uni, c_pre, c_qtd, c_add = st.columns([3, 0.6, 0.8, 0.8, 1])

with c_sel:
    st.selectbox("Artigo:", options=[""] + lista_artigos, key="sel_artigo", on_change=atualizar_campos)

with c_uni:
    st.text_input("Unid.", value=st.session_state.unid_preview, disabled=True)

with c_pre:
    # Formatado com 2 casas decimais
    novo_preco = st.number_input("Preço Unit (€)", value=st.session_state.preco_editavel, format="%.2f", step=0.01, key="input_preco_edit")

with c_qtd:
    # Quantidade também com 2 casas decimais
    qtd_val = st.number_input("Qtd", min_value=0.01, value=1.00, step=0.10, format="%.2f", key="q_tab")

with c_add:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("✅ Adicionar", use_container_width=True):
        if st.session_state.sel_artigo:
            cod_sel = st.session_state.sel_artigo.split(" - ")[0]
            desc_sel = st.session_state.sel_artigo.split(" - ", 1)[1]
            novo = pd.DataFrame([{
                "CÓDIGO": cod_sel, 
                "Artigo": desc_sel, 
                "UNID": st.session_state.unid_preview, 
                "Preço Unitário": float(novo_preco),
                "Quantidade": float(qtd_val)
            }])
            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo], ignore_index=True)
            st.rerun()

st.divider()

# --- SECÇÃO 2: ITEM EXTRA ---
st.subheader("✍️ 2. Item Extra (Manual)")
c_art_ex, c_uni_ex, c_pre_ex, c_qtd_ex, c_add_ex = st.columns([3, 0.6, 0.8, 0.8, 1])
with c_art_ex:
    artigo_ex = st.text_input("Descrição do Artigo Extra:", placeholder="Ex: Serviço de transporte...")
with c_uni_ex:
    uni_ex = st.text_input("Unid:", key="u_ex_man")
with c_pre_ex:
    pre_ex = st.number_input("Preço (€):", min_value=0.0, format="%.2f", key="p_ex_man")
with c_qtd_ex:
    q_ex = st.number_input("Qtd:", min_value=0.01, value=1.00, format="%.2f", key="q_ex_man")
with c_add_ex:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("➕ Adicionar Extra", use_container_width=True):
        if artigo_ex:
            novo_ex = pd.DataFrame([{"CÓDIGO": "EXTRA", "Artigo": artigo_ex, "UNID": uni_ex, "Preço Unitário": float(pre_ex), "Quantidade": float(q_ex)}])
            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo_ex], ignore_index=True)
            st.rerun()

# 4. RESUMO E TABELA
st.divider()
if not st.session_state.itens_orcamento.empty:
    st.markdown("### 📋 Resumo do Orçamento")
    taxa_iva = st.selectbox("Taxa de IVA:", [23, 13, 6, 0], format_func=lambda x: f"{x}%")
    
    df_f = st.session_state.itens_orcamento.copy()
    df_f["Subtotal"] = df_f["Quantidade"] * df_f["Preço Unitário"]
    
    # Configuração de colunas para forçar 2 casas decimais no editor
    df_editado = st.data_editor(
        df_f, 
        use_container_width=True, 
        hide_index=True, 
        num_rows="dynamic",
        column_config={
            "Preço Unitário": st.column_config.NumberColumn(format="%.2f €"),
            "Quantidade": st.column_config.NumberColumn(format="%.2f"),
            "Subtotal": st.column_config.NumberColumn(format="%.2f €"),
        }
    )
    st.session_state.itens_orcamento = df_editado[["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"]]
    
    sub_val = df_editado["Subtotal"].sum()
    iva_val = sub_val * (taxa_iva / 100)
    total_val = sub_val + iva_val

    def criar_pdf(df, sub, iva_v, total_f, taxa):
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20, bottomMargin=20)
        sty = getSampleStyleSheet()
        est_tab = sty['Normal']
        est_tab.fontSize = 8
        
        elems = []
        if os.path.exists("logo.png"):
            img = RLImage("logo.png", width=1.25*inch, height=0.6*inch)
            img.hAlign = 'CENTER'
            elems.append(img)
            
        elems.append(Paragraph("JMOS V 1.1", sty['Normal']))
        elems.append(Paragraph(f"ORÇAMENTO: {n_orc}", sty['Title']))
        elems.append(Spacer(1, 15))
        
        cli_info = f"<b>Cliente:</b> {nome_cli}<br/><b>Morada:</b> {morada_cli}<br/><b>Email:</b> {email_cli}"
        elems.append(Paragraph(cli_info, sty['Normal']))
        elems.append(Spacer(1, 15))
        
        data = [["Artigo / Descrição", "Qtd", "Unid", "Preço Unit.", "Total"]]
        for _, r in df.iterrows():
            # Forçar 2 casas decimais em todas as células do PDF
            data.append([
                Paragraph(str(r['Artigo']), est_tab), 
                f"{r['Quantidade']:.2f}", 
                r['UNID'], 
                f"{r['Preço Unitário']:.2f}€", 
                f"{r['Subtotal']:.2f}€"
            ])
        
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
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))
        elems.append(t)
        
        if obs_cli:
            elems.append(Spacer(1, 20))
            elems.append(Paragraph(f"<b>Observações:</b><br/>{obs_cli}", sty['Normal']))
            
        doc.build(elems)
        return buf.getvalue()

    c1, c2, c3 = st.columns(3)
    c1.download_button("📥 Baixar PDF JMOS", data=criar_pdf(df_editado, sub_val, iva_val, total_val, taxa_iva), file_name=f"Orcamento_{n_orc}.pdf", use_container_width=True)
    
    buf_x = io.BytesIO()
    with pd.ExcelWriter(buf_x, engine='xlsxwriter') as wr:
        df_editado.to_excel(wr, index=False)
    c2.download_button("📊 Baixar Excel", data=buf_x.getvalue(), file_name=f"Orcamento_{n_orc}.xlsx", use_container_width=True)

    if c3.button("🗑️ Limpar Tudo", use_container_width=True):
        st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])
        st.rerun()
