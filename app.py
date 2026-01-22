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
import pickle

# --------------------------------------------------
# 1. Configuração e Estética
# --------------------------------------------------
st.set_page_config(page_title="Orçamentador Pro", layout="wide")

LOGO_PATH = "logo.png" 
EXCEL_PATH = "Cópia de Preços Tabela atual.xlsx"

if os.path.exists(LOGO_PATH):
    st.image(LOGO_PATH, width=250)

# --------------------------------------------------
# 2. Funções de Suporte
# --------------------------------------------------
def carregar_base_limpa():
    if os.path.exists(EXCEL_PATH):
        try:
            df = pd.read_excel(EXCEL_PATH)
            colunas = ["CÓDIGO", "DESCRIÇÃO", "UNID", "VALORES ATUAIS JANEIRO 2025"]
            df = df[colunas].dropna(subset=["DESCRIÇÃO"])
            df.rename(columns={"VALORES ATUAIS JANEIRO 2025": "Preço Unitário"}, inplace=True)
            df["Quantidade"] = 0.0
            return df
        except:
            pass
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário", "Quantidade"])

# --------------------------------------------------
# 3. Gestão de Estado (Sessão)
# --------------------------------------------------
if "lista_orcamentos" not in st.session_state:
    st.session_state["lista_orcamentos"] = {
        "Orçamento 1": {"cliente": "", "obra": "", "notas": "", "dados": carregar_base_limpa()}
    }
    st.session_state["orc_atual"] = "Orçamento 1"

# --------------------------------------------------
# 4. Sidebar: Gestão de Sessões e Backup
# --------------------------------------------------
with st.sidebar:
    st.header("💾 Sistema de Backup")
    
    # Exportar Rascunhos
    estado_para_gravar = {
        "lista": st.session_state["lista_orcamentos"],
        "atual": st.session_state["orc_atual"]
    }
    st.download_button(
        label="📥 Guardar Rascunhos no PC",
        data=pickle.dumps(estado_para_gravar),
        file_name=f"backup_orcamentos_{date.today()}.pkl",
        help="Baixa um ficheiro com todos os orçamentos para continuar noutro dia."
    )
    
    # Restaurar Rascunhos
    arquivo_backup = st.file_uploader("📂 Abrir Backup do PC", type=["pkl"])
    if arquivo_backup:
        dados_restaurados = pickle.loads(arquivo_backup.read())
        st.session_state["lista_orcamentos"] = dados_restaurados["lista"]
        st.session_state["orc_atual"] = dados_restaurados["atual"]
        st.success("Backup restaurado!")
        st.rerun()

    st.divider()
    st.header("📂 Alternar Orçamentos")
    opcoes = list(st.session_state["lista_orcamentos"].keys())
    escolha = st.selectbox("Selecionar Trabalho:", opcoes, index=opcoes.index(st.session_state["orc_atual"]))
    
    if escolha != st.session_state["orc_atual"]:
        st.session_state["orc_atual"] = escolha
        st.rerun()

    if st.button("➕ Novo Orçamento"):
        novo_nome = f"Orçamento {len(st.session_state['lista_orcamentos']) + 1}"
        st.session_state["lista_orcamentos"][novo_nome] = {"cliente": "", "obra": "", "notas": "", "dados": carregar_base_limpa()}
        st.session_state["orc_atual"] = novo_nome
        st.rerun()

    st.divider()
    res = st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]
    res["cliente"] = st.text_input("Cliente", res["cliente"])
    res["obra"] = st.text_input("Obra", res["obra"])
    iva_percent = st.selectbox("IVA (%)", [0, 6, 13, 23], index=3)

# --------------------------------------------------
# 5. Área de Trabalho Principal
# --------------------------------------------------
st.title(f"📐 Editando: {st.session_state['orc_atual']}")
dados_atuais = st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]["dados"]

# Adicionar Item Manual
with st.expander("➕ Adicionar item personalizado"):
    c1, c2, c3, c4 = st.columns([1, 3, 1, 1])
    n_cod = c1.text_input("Cód")
    n_des = c2.text_input("Descrição")
    n_uni = c3.text_input("Unid")
    n_pre = c4.number_input("Preço Unit. (€)", min_value=0.0, format="%.2f")
    if st.button("Inserir na Lista"):
        novo = pd.DataFrame([{"CÓDIGO": n_cod, "DESCRIÇÃO": n_des, "UNID": n_uni, "Preço Unitário": n_pre, "Quantidade": 0.0}])
        st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]["dados"] = pd.concat([dados_atuais, novo], ignore_index=True)
        st.rerun()

# Pesquisa e Edição
pesquisa = st.text_input("🔍 Pesquisar na base de dados...")
mask = dados_atuais["DESCRIÇÃO"].str.contains(pesquisa, case=False, na=False) | \
       dados_atuais["CÓDIGO"].astype(str).str.contains(pesquisa, case=False, na=False)

df_view = dados_atuais[mask | (dados_atuais["Quantidade"] > 0)].copy()

# A chave dinâmica garante que o editor atualize após carregar o backup
editor_key = f"editor_{st.session_state['orc_atual']}"

edited_df = st.data_editor(
    df_view,
    column_config={
        "Preço Unitário": st.column_config.NumberColumn("Preço (€)", format="%.2f"),
        "Quantidade": st.column_config.NumberColumn("Qtd", min_value=0.0, step=0.1)
    },
    hide_index=True, 
    use_container_width=True,
    key=editor_key
)

# Sincronização rigorosa com o estado global
if edited_df is not None:
    for idx in edited_df.index:
        st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]["dados"].at[idx, "Quantidade"] = edited_df.loc[idx, "Quantidade"]
        st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]["dados"].at[idx, "Preço Unitário"] = edited_df.loc[idx, "Preço Unitário"]

st.divider()
res["notas"] = st.text_area("📝 Notas / Observações do Orçamento", res["notas"])

# --------------------------------------------------
# 6. Totais e Exportação (PDF e Excel)
# --------------------------------------------------
itens_finais = st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]["dados"].copy()
itens_finais = itens_finais[itens_finais["Quantidade"] > 0]

if not itens_finais.empty:
    itens_finais["Total"] = itens_finais["Quantidade"] * itens_finais["Preço Unitário"]
    subtotal = itens_finais["Total"].sum()
    valor_iva = subtotal * (iva_percent / 100)
    total_geral = subtotal + valor_iva

    c1, c2, c3 = st.columns(3)
    c1.metric("Subtotal", f"{subtotal:,.2f} €")
    c2.metric(f"IVA ({iva_percent}%)", f"{valor_iva:,.2f} €")
    c3.subheader(f"TOTAL: {total_geral:,.2f} €")

    st.write("### Gerar Documentos")
    col_pdf, col_xls = st.columns(2)

    with col_pdf:
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        if os.path.exists(LOGO_PATH):
            img = Image(LOGO_PATH, width=150, height=75)
            img.hAlign = 'CENTER'
            elements.append(img)
            elements.append(Spacer(1, 15))

        title_st = ParagraphStyle('T', parent=styles['Title'], alignment=TA_CENTER)
        elements.append(Paragraph(f"ORÇAMENTO: {res['obra']}", title_st))
        elements.append(Paragraph(f"<b>Cliente:</b> {res['cliente']} | <b>Data:</b> {date.today()}", styles['Normal']))
        elements.append(Spacer(1, 20))

        data = [["Cód", "Descrição", "Un", "Qtd", "Preço", "Total"]]
        for _, r in itens_finais.iterrows():
            data.append([r["CÓDIGO"], r["DESCRIÇÃO"][:55], r["UNID"], f"{r['Quantidade']:.2f}", f"{r['Preço Unitário']:.2f}€", f"{r['Total']:.2f}€"])
        
        data.append(["", "", "", "", "TOTAL:", f"{total_geral:,.2f}€"])

        table = Table(data, colWidths=[40, 240, 30, 40, 70, 70])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f2f2f2")),
            ('GRID', (0,0), (-1,-2), 0.5, colors.grey),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
        ]))
        elements.append(table)

        if res["notas"]:
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("<b>Observações:</b>", styles['Normal']))
            elements.append(Paragraph(res["notas"], styles['Normal']))

        doc.build(elements)
        st.download_button("⬇️ Baixar PDF", pdf_buffer.getvalue(), f"Orcamento_{res['cliente']}.pdf", "application/pdf")

    with col_xls:
        output_ex = io.BytesIO()
        with pd.ExcelWriter(output_ex, engine='xlsxwriter') as writer:
            itens_finais.to_excel(writer, index=False, sheet_name='Itens')
            df_resumo = pd.DataFrame([{"Cliente": res["cliente"], "Obra": res["obra"], "Total": total_geral, "Notas": res["notas"]}])
            df_resumo.to_excel(writer, index=False, sheet_name='Resumo')
            
        st.download_button("⬇️ Baixar Excel", output_ex.getvalue(), f"Orcamento_{res['cliente']}.xlsx")
else:
    st.info("Insira quantidades para desbloquear os botões de exportação.")
