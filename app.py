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
# 1. CONFIGURAÇÃO E ESTÉTICA
# --------------------------------------------------
st.set_page_config(page_title="Orçamentador Pro", layout="wide")

LOGO_PATH = "logo.png" 
EXCEL_PATH = "Cópia de Preços Tabela atual.xlsx"

# --------------------------------------------------
# 2. FUNÇÕES DE DADOS E SINCRONIZAÇÃO
# --------------------------------------------------
def carregar_base_limpa():
    if os.path.exists(EXCEL_PATH):
        try:
            df = pd.read_excel(EXCEL_PATH)
            # Ajuste de colunas (conforme o seu ficheiro)
            colunas = ["CÓDIGO", "DESCRIÇÃO", "UNID", "VALORES ATUAIS JANEIRO 2025"]
            df = df[colunas].dropna(subset=["DESCRIÇÃO"])
            df.rename(columns={"VALORES ATUAIS JANEIRO 2025": "Preço Unitário"}, inplace=True)
            df["Quantidade"] = 0.0
            # Garantir que CÓDIGO é texto para a pesquisa funcionar sempre
            df["CÓDIGO"] = df["CÓDIGO"].astype(str)
            return df
        except Exception as e:
            st.error(f"Erro ao ler o Excel: {e}")
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário", "Quantidade"])

def sincronizar_dados(key_editor):
    """Sincroniza as edições das tabelas com a base de dados principal via index real"""
    if key_editor in st.session_state:
        edicoes = st.session_state[key_editor]
        res = st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]
        
        # Processar Edições (Quantidade ou Preço)
        for row_idx, alteracoes in edicoes["edited_rows"].items():
            for col, val in alteracoes.items():
                res["dados"].at[row_idx, col] = val
        
        # Processar Remoções (Botão X ou Delete)
        for row_idx in edicoes["deleted_rows"]:
            res["dados"].at[row_idx, "Quantidade"] = 0.0

# --------------------------------------------------
# 3. GESTÃO DE ESTADO (SESSÃO)
# --------------------------------------------------
if "lista_orcamentos" not in st.session_state:
    st.session_state["lista_orcamentos"] = {
        "Orçamento 1": {
            "cliente": "", "morada": "", "telefone": "", "obra": "", 
            "data_visita": date.today(), "notas": "", "dados": carregar_base_limpa()
        }
    }
    st.session_state["orc_atual"] = "Orçamento 1"

res = st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]

# --------------------------------------------------
# 4. INTERFACE SUPERIOR (DADOS E EXPORTAÇÃO)
# --------------------------------------------------
col_log, col_info, col_exp = st.columns([1, 2, 1.5])

with col_log:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=180)

with col_info:
    st.markdown(f"### 📋 {st.session_state['orc_atual']}")
    c1, c2 = st.columns(2)
    res["cliente"] = c1.text_input("Nome do Cliente", res["cliente"])
    res["telefone"] = c2.text_input("Telefone", res["telefone"])
    res["morada"] = st.text_input("Morada", res["morada"])

with col_exp:
    st.markdown("### 📄 Exportação e Totais")
    iva_p = st.selectbox("IVA (%)", [0, 6, 13, 23], index=3)
    
    df_finais = res["dados"][res["dados"]["Quantidade"] > 0].copy()
    
    if not df_finais.empty:
        df_finais["Total_Linha"] = df_finais["Quantidade"] * df_finais["Preço Unitário"]
        subtotal = df_finais["Total_Linha"].sum()
        valor_iva = subtotal * (iva_p / 100)
        total_final = subtotal + valor_iva
        
        st.markdown(f"**Subtotal:** {subtotal:,.2f} € | **IVA:** {valor_iva:,.2f} €")
        st.markdown(f"#### **TOTAL: {total_final:,.2f} €**")
        
        c_pdf, c_xls = st.columns(2)
        
        # --- GERAÇÃO DE PDF ---
        with c_pdf:
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, topMargin=20)
            styles = getSampleStyleSheet()
            elements = []
            
            if os.path.exists(LOGO_PATH):
                logo_pdf = Image(LOGO_PATH, width=100, height=50)
                logo_pdf.hAlign = 'CENTER'
                elements.append(logo_pdf)
                elements.append(Spacer(1, 10))
            
            title_st = ParagraphStyle('T', parent=styles['Title'], alignment=TA_CENTER, fontSize=18)
            elements.append(Paragraph("ORÇAMENTO", title_st))
            elements.append(Paragraph(f"<b>Cliente:</b> {res['cliente']} | <b>Telefone:</b> {res['telefone']}", styles['Normal']))
            elements.append(Paragraph(f"<b>Morada:</b> {res['morada']}", styles['Normal']))
            elements.append(Spacer(1, 15))
            
            data_pdf = [["Descrição", "Un", "Qtd", "Preço", "Total"]]
            for _, r in df_finais.iterrows():
                data_pdf.append([Paragraph(r["DESCRIÇÃO"], styles['Normal']), r["UNID"], f"{r['Quantidade']}", f"{r['Preço Unitário']:,.2f}€", f"{r['Total_Linha']:,.2f}€"])
            
            data_pdf.append(["", "", "", "TOTAL FINAL:", f"{total_final:,.2f}€"])
            
            table = Table(data_pdf, colWidths=[240, 30, 40, 70, 70])
            table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f0f0f0")), ('GRID', (0,0), (-1,-2), 0.5, colors.grey), ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold')]))
            elements.append(table)
            
            doc.build(elements)
            st.download_button("⬇️ Baixar PDF", pdf_buffer.getvalue(), f"Orcamento_{res['cliente']}.pdf", "application/pdf")

        # --- GERAÇÃO DE EXCEL ---
        with c_xls:
            output_ex = io.BytesIO()
            with pd.ExcelWriter(output_ex, engine='xlsxwriter') as writer:
                df_finais.to_excel(writer, index=False, sheet_name='Itens')
                pd.DataFrame([{"Subtotal": subtotal, "IVA": valor_iva, "Total": total_final}]).to_excel(writer, index=False, sheet_name='Resumo')
            st.download_button("⬇️ Baixar Excel", output_ex.getvalue(), f"Orcamento_{res['cliente']}.xlsx")
    else:
        st.info("Adicione itens para ver o total e exportar.")

# --------------------------------------------------
# 5. ZONA DE PESQUISA (NOME OU CÓDIGO)
# --------------------------------------------------
st.divider()
st.subheader("🔍 1. Pesquisar e Adicionar Artigos")
pesquisa = st.text_input("Pesquise por NOME ou CÓDIGO do artigo...")

# Lógica de filtro duplo corrigida
mask_pesquisa = (
    res["dados"]["DESCRIÇÃO"].str.contains(pesquisa, case=False, na=False) | 
    res["dados"]["CÓDIGO"].str.contains(pesquisa, case=False, na=False)
)

# Apenas itens que ainda têm Qtd = 0 aparecem na pesquisa
df_search = res["dados"][mask_pesquisa & (res["dados"]["Quantidade"] == 0)]

st.data_editor(
    df_search,
    column_config={
        "CÓDIGO": st.column_config.TextColumn("Cód"),
        "Preço Unitário": st.column_config.NumberColumn("Preço Base (€)", format="%.2f", disabled=True),
        "Quantidade": st.column_config.NumberColumn("Qtd", min_value=0.0)
    },
    hide_index=False, # Essencial para sincronização por index
    use_container_width=True,
    key=f"search_{st.session_state['orc_atual']}",
    on_change=sincronizar_dados, args=(f"search_{st.session_state['orc_atual']}",)
)

# --------------------------------------------------
# 6. ITENS APURADOS (EDIÇÃO E REMOÇÃO DINÂMICA)
# --------------------------------------------------
st.markdown("---")
st.subheader("📝 2. Itens no Orçamento (Apurados)")

df_apurados = res["dados"][res["dados"]["Quantidade"] > 0]

if not df_apurados.empty:
    st.caption("🗑️ Para remover: Selecione a linha à esquerda e prima 'Delete' ou use o ícone de lixo.")
    st.data_editor(
        df_apurados,
        column_config={
            "DESCRIÇÃO": st.column_config.TextColumn("Artigo", width="large", disabled=True),
            "Preço Unitário": st.column_config.NumberColumn("Preço Unit. (€)", format="%.2f"),
            "Quantidade": st.column_config.NumberColumn("Qtd", min_value=0.0)
        },
        hide_index=False,
        use_container_width=True,
        num_rows="dynamic", # Ativa o botão de apagar/X
        key=f"edit_{st.session_state['orc_atual']}",
        on_change=sincronizar_dados, args=(f"edit_{st.session_state['orc_atual']}",)
    )
    res["notas"] = st.text_area("Notas / Condições", res["notas"])
else:
    st.warning("A lista de apurados está vazia.")

# --------------------------------------------------
# 7. SIDEBAR (BACKUP E GESTÃO)
# --------------------------------------------------
with st.sidebar:
    st.header("💾 Gestão")
    st.download_button("📥 Guardar Backup (PKL)", pickle.dumps(st.session_state["lista_orcamentos"]), f"backup_{date.today()}.pkl")
    arq = st.file_uploader("📂 Restaurar Backup", type=["pkl"])
    if arq:
        st.session_state["lista_orcamentos"] = pickle.loads(arq.read())
        st.rerun()
    st.divider()
    if st.button("➕ Novo Trabalho"):
        nome = f"Orçamento {len(st.session_state['lista_orcamentos']) + 1}"
        st.session_state["lista_orcamentos"][nome] = {"cliente": "", "morada": "", "telefone": "", "obra": "", "data_visita": date.today(), "notas": "", "dados": carregar_base_limpa()}
        st.session_state["orc_atual"] = nome
        st.rerun()
