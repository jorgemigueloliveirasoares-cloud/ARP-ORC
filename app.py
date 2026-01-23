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

# --- CABEÇALHO JMOS V 1.1 ---
st.markdown("<h1 style='text-align: center; color: #0073B4;'>JMOS V 1.1</h1>", unsafe_allow_html=True)

if os.path.exists("logo.png"):
    col_l1, col_l2, col_l3 = st.columns([2, 1, 2])
    with col_l2:
        st.image("logo.png", use_container_width=True)

st.divider()

# 2. DADOS DO CLIENTE E BACKUP
col_cli, col_rasc = st.columns([3, 1.2])

with col_cli:
    st.subheader("📋 Dados do Cliente")
    nome_cli = st.text_input("Nome do Cliente", key="nome_cli_input")
    morada_cli = st.text_input("Morada", key="morada_cli_input")
    c1, c2 = st.columns(2)
    tel_cli = c1.text_input("Telefone", key="tel_cli_input")
    email_cli = c2.text_input("Email", key="email_cli_input")
    obs_cli = st.text_area("Observações / Condições de Pagamento", key="obs_cli_input")

with col_rasc:
    st.subheader("💾 Backup / Sistema")
    n_orc = st.text_input("Nº Orçamento", value=f"ORC-{date.today().year}-001")
    
    dados_para_backup = {
        "cliente": {"nome": nome_cli, "morada": morada_cli, "tel": tel_cli, "email": email_cli, "obs": obs_cli, "n_orc": n_orc},
        "itens": st.session_state.itens_orcamento.to_dict(orient="records")
    }
    
    st.download_button(
        label="📥 Guardar Backup (JSON)",
        data=json.dumps(dados_para_backup, indent=4),
        file_name=f"backup_{n_orc}.json",
        use_container_width=True
    )
    
    st.markdown("---")
    arquivo_upload = st.file_uploader("📂 Restaurar Backup", type="json")
    if arquivo_upload is not None:
        try:
            conteudo = json.load(arquivo_upload)
            st.session_state.itens_orcamento = pd.DataFrame(conteudo["itens"])
            st.success("Backup carregado!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro no backup: {e}")

st.divider()

# --- 3. ADIÇÃO DE ITENS ---
st.subheader("🔍 1. Adicionar Itens da Tabela")
base_dados = carregar_base()
lista_artigos = base_dados.apply(lambda x: f"{x['CÓDIGO']} - {x['DESCRIÇÃO']}", axis=1).tolist()

c_sel, c_uni, c_pre, c_qtd, c_add = st.columns([3, 0.6, 0.8, 0.8, 1])

unid_def = ""
preco_def = 0.0
artigo_escolhido = c_sel.selectbox("Artigo:", options=[""] + lista_artigos, key="sel_artigo_main")

if artigo_escolhido:
    cod_temp = artigo_escolhido.split(" - ")[0]
    row_temp = base_dados[base_dados["CÓDIGO"] == cod_temp].iloc[0]
    unid_def = str(row_temp["UNID"])
    preco_def = float(row_temp["Preço Unitário"])

with c_uni:
    st.text_input("Unid.", value=unid_def, disabled=True, key=f"unid_{artigo_escolhido}")

with c_pre:
    preco_final = st.number_input("Preço Unit (€)", value=preco_def, format="%.2f", step=0.01, key=f"preco_{artigo_escolhido}")

with c_qtd:
    qtd_val = st.number_input("Qtd", min_value=0.01, value=1.00, step=0.10, format="%.2f", key="q_tab_global")

with c_add:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("✅ Adicionar", use_container_width=True):
        if artigo_escolhido:
            cod_sel = artigo_escolhido.split(" - ")[0]
            desc_sel = artigo_escolhido.split(" - ", 1)[1]
            novo = pd.DataFrame([{
                "CÓDIGO": cod_sel, "Artigo": desc_sel, "UNID": unid_def, 
                "Preço Unitário": float(preco_final), "Quantidade": float(qtd_val)
            }])
            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo], ignore_index=True)
            st.rerun()

st.divider()

# --- SECÇÃO 2: ITEM EXTRA (MANUAL) ---
st.subheader("✍️ 2. Item Extra (Manual)")
c_art_ex, c_uni_ex, c_pre_ex, c_qtd_ex, c_add_ex = st.columns([3, 0.6, 0.8, 0.8, 1])
with c_art_ex:
    artigo_ex = st.text_input("Descrição do Artigo Extra:", placeholder="Ex: Mão-de-obra...")
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

# --- 4. RESUMO E EXPORTAÇÃO ---
st.divider()
if not st.session_state.itens_orcamento.empty:
    st.markdown("### 📋 Resumo do Orçamento")
    taxa_iva = st.selectbox("Taxa de IVA:", [23, 13, 6, 0], format_func=lambda x: f"{x}%")
    
    df_f = st.session_state.itens_orcamento.copy()
    df_f["Subtotal"] = df_f["Quantidade"] * df_f["Preço Unitário"]
    
    df_editado = st.data_editor(
        df_f, use_container_width=True, hide_index=True, num_rows="dynamic",
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

    # Funções de ficheiro
    def criar_pdf():
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20, bottomMargin=20)
        sty = getSampleStyleSheet()
        elems = []
        if os.path.exists("logo.png"):
            img = RLImage("logo.png", width=1.25*inch, height=0.6*inch)
            img.hAlign = 'CENTER'
            elems.append(img)
        elems.append(Paragraph(f"ORÇAMENTO: {n_orc}", sty['Title']))
        elems.append(Paragraph(f"<b>Cliente:</b> {nome_cli}", sty['Normal']))
        data = [["Artigo", "Qtd", "Unid", "Preço", "Total"]]
        for _, r in df_editado.iterrows():
            data.append([Paragraph(str(r['Artigo']), sty['Normal']), f"{r['Quantidade']:.2f}", r['UNID'], f"{r['Preço Unitário']:.2f}€", f"{r['Subtotal']:.2f}€"])
        data.append(["", "", "", "TOTAL:", f"{total_val:,.2f}€"])
        t = Table(data, colWidths=[280, 45, 45, 75, 75])
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), AZUL_LOGO), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1, len(df_editado)), 0.5, colors.grey)]))
        elems.append(t)
        doc.build(elems)
        return buf.getvalue()

    def criar_excel():
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_editado.to_excel(writer, index=False, sheet_name='Orçamento')
            # O xlsxwriter permite personalizar mais se precisares no futuro
        return output.getvalue()

    # BOTÕES DE AÇÃO LADO A LADO
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.download_button("📥 Baixar PDF JMOS", data=criar_pdf(), file_name=f"{n_orc}.pdf", use_container_width=True)
    
    with c2:
        st.download_button("📊 Baixar Excel", data=criar_excel(), file_name=f"{n_orc}.xlsx", 
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                           use_container_width=True)
    
    with c3:
        if st.button("🗑️ Limpar Tudo", use_container_width=True):
            st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])
            st.rerun()
