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
    
    u_backup = st.file_uploader("📂 Upload de Backup", type="json", label_visibility="collapsed")
    if u_backup:
        carregados = json.load(u_backup)
        st.session_state.itens_orcamento = pd.DataFrame(carregados["itens"])
        st.success("Dados carregados!")

st.divider()

# 3. ADIÇÃO DE ITENS
st.subheader("🔍 1. Adicionar Itens")
tab1, tab2 = st.tabs(["🔎 Pesquisar Excel (Escolha Pendente)", "➕ Manual"])

with tab1:
    base = carregar_base()
    # Prepara a lista para o dropdown: "CÓDIGO - DESCRIÇÃO"
    lista_artigos = base.apply(lambda x: f"{x['CÓDIGO']} - {x['DESCRIÇÃO']}", axis=1).tolist()
    
    escolha = st.selectbox(
        "Pesquise o código ou nome do artigo:",
        options=[""] + lista_artigos,
        index=0,
        help="Escreva para filtrar a lista automaticamente"
    )

    if escolha:
        # Recupera os dados do item selecionado
        cod_selecionado = escolha.split(" - ")[0]
        row = base[base["CÓDIGO"] == cod_selecionado].iloc[0]
        
        st.info(f"**Selecionado:** {row['DESCRIÇÃO']} ({row['Preço Unitário']:.2f}€/{row['UNID']})")
        
        col_q, col_b = st.columns([1, 1])
        qtd_txt = col_q.text_input("Introduza a Quantidade", value="1", key="qtd_sel")
        
        if col_b.button("✅ Adicionar ao Orçamento", use_container_width=True):
            qtd_limpa = qtd_txt.replace(',', '.').strip()
            try:
                v = float(qtd_limpa)
                if v > 0:
                    novo = pd.DataFrame([{
                        "CÓDIGO": row["CÓDIGO"], 
                        "Artigo": row["DESCRIÇÃO"], 
                        "UNID": row["UNID"], 
                        "Preço Unitário": float(row["Preço Unitário"]), 
                        "Quantidade": v
                    }])
                    st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo], ignore_index=True)
                    st.rerun()
                else:
                    st.error("A quantidade deve ser superior a zero.")
            except ValueError:
                st.error("Quantidade inválida. Use números.")

with tab2:
    m1, m2, m3, m4 = st.columns([3, 1, 1, 1])
    m_desc = m1.text_input("Descrição Manual")
    m_prec = m2.number_input("Preço €", min_value=0.0, step=0.01, format="%.2f")
    m_qtd = m3.number_input("Qtd", min_value=0.0, step=0.01, format="%.2f")
    if m4.button("Adicionar Item"):
        if m_desc and m_qtd > 0:
            nm = pd.DataFrame([{"CÓDIGO": "EXTRA", "Artigo": m_desc, "UNID": "un", "Preço Unitário": m_prec, "Quantidade": m_qtd}])
            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, nm], ignore_index=True)
            st.rerun()

# 4. TABELA FINAL E EXPORTAÇÕES
st.divider()
if not st.session_state.itens_orcamento.empty:
    df_final = st.session_state.itens_orcamento.copy()
    df_final["Subtotal"] = df_final["Quantidade"] * df_final["Preço Unitário"]
    
    st.markdown("### 📋 Resumo do Orçamento")
    df_editado = st.data_editor(
        df_final,
        column_config={
            "Preço Unitário": st.column_config.NumberColumn("Preço Unitário", format="%.2f €"),
            "Quantidade": st.column_config.NumberColumn("Quantidade", format="%.2f"),
            "Subtotal": st.column_config.NumberColumn("Subtotal", format="%.2f €"),
        },
        use_container_width=True,
        hide_index=True
    )
    
    st.session_state.itens_orcamento = df_editado[["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"]]
    total_val = df_editado["Subtotal"].sum()
    st.write(f"### **Total: {total_val:,.2f}€**")

    def criar_pdf(df, total):
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20, bottomMargin=20)
        sty = getSampleStyleSheet()
        estilo_tabela = sty['Normal']
        estilo_tabela.fontSize = 9
        estilo_tabela.leading = 11 
        
        elems = []
        if os.path.exists("logo.png"):
            img = RLImage("logo.png", width=1.5*inch, height=0.8*inch)
            img.hAlign = 'LEFT'
            elems.append(img)
            
        elems.append(Paragraph(f"ORÇAMENTO: {n_orc}", sty['Title']))
        elems.append(Spacer(1, 10))
        
        cli_info = f"<b>Cliente:</b> {nome_cli}<br/><b>Morada:</b> {morada_cli}<br/><b>Tel:</b> {tel_cli}<br/><b>Email:</b> {email_cli}"
        elems.append(Paragraph(cli_info, sty['Normal']))
        elems.append(Spacer(1, 20))
        
        data = [["Artigo / Descrição", "Qtd", "Unid", "Preço Unit.", "Total"]]
        for _, r in df.iterrows():
            art_p = Paragraph(str(r['Artigo']), estilo_tabela)
            data.append([
                art_p, 
                f"{float(r['Quantidade']):.2f}", 
                r['UNID'], 
                f"{float(r['Preço Unitário']):.2f}€", 
                f"{(float(r['Quantidade']) * float(r['Preço Unitário'])):.2f}€"
            ])
        
        data.append(["", "", "", "TOTAL:", f"{total:,.2f}€"])
        
        t = Table(data, colWidths=[280, 45, 45, 65, 65])
        t.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
            ('ALIGN', (1,0), (-1,-1), 'CENTER'),
            ('ALIGN', (3,0), (4,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        elems.append(t)
        
        if obs_cli:
            elems.append(Spacer(1, 20))
            elems.append(Paragraph(f"<b>Observações:</b><br/>{obs_cli}", sty['Normal']))
            
        doc.build(elems)
        return buf.getvalue()

    c_pdf, c_xls, c_limp = st.columns(3)
    c_pdf.download_button("📥 Baixar PDF", data=criar_pdf(df_editado, total_val), file_name=f"{n_orc}.pdf", use_container_width=True)
    
    buf_x = io.BytesIO()
    with pd.ExcelWriter(buf_x, engine='xlsxwriter') as wr:
        df_editado.to_excel(wr, index=False)
    c_xls.download_button("📊 Baixar Excel", data=buf_x.getvalue(), file_name=f"{n_orc}.xlsx", use_container_width=True)

    if c_limp.button("🗑️ Limpar Tudo", use_container_width=True):
        st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])
        st.rerun()
