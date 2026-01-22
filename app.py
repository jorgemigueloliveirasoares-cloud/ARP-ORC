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
st.set_page_config(page_title="Gestor de Orçamentos", layout="wide")

LOGO_PATH = "logo.png" 
EXCEL_PATH = "Cópia de Preços Tabela atual.xlsx"

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
            st.error("Erro ao ler o Excel. Verifique se o ficheiro e as colunas estão corretos.")
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário", "Quantidade"])

def sincronizar_dados(key_editor):
    if key_editor in st.session_state:
        edicoes = st.session_state[key_editor]
        res = st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]
        
        for row_idx, alteracoes in edicoes["edited_rows"].items():
            for col, val in alteracoes.items():
                res["dados"].at[row_idx, col] = val
        
        for row_idx in edicoes["deleted_rows"]:
            res["dados"].at[row_idx, "Quantidade"] = 0.0

# --------------------------------------------------
# 3. Estado da Sessão
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
# 4. Interface Superior
# --------------------------------------------------
col_log, col_info, col_exp = st.columns([1, 2, 1.5])

with col_log:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=180)
    else:
        st.warning("logo.png não encontrado.")

with col_info:
    st.markdown(f"### 📋 {st.session_state['orc_atual']}")
    c1, c2 = st.columns(2)
    res["cliente"] = c1.text_input("Nome do Cliente", res["cliente"])
    res["telefone"] = c2.text_input("Telefone", res["telefone"])
    res["morada"] = st.text_input("Morada", res["morada"])

with col_exp:
    st.markdown("### 📄 Exportação e Total")
    iva_p = st.selectbox("IVA (%)", [0, 6, 13, 23], index=3)
    
    df_finais = res["dados"][res["dados"]["Quantidade"] > 0].copy()
    
    if not df_finais.empty:
        df_finais["Total_Linha"] = df_finais["Quantidade"] * df_finais["Preço Unitário"]
        subtotal = df_finais["Total_Linha"].sum()
        valor_iva = subtotal * (iva_p / 100)
        total_final = subtotal + valor_iva
        
        st.markdown(f"**Subtotal:** {subtotal:,.2f} €")
        st.markdown(f"#### **TOTAL COM IVA: {total_final:,.2f} €**")
        
        c_pdf, c_xls = st.columns(2)
        
        with c_pdf:
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, topMargin=20)
            styles = getSampleStyleSheet()
            elements = []
            
            # --- LOGOTIPO NO PDF ---
            if os.path.exists(LOGO_PATH):
                logo_pdf = Image(LOGO_PATH, width=120, height=60)
                logo_pdf.hAlign = 'CENTER'
                elements.append(logo_pdf)
                elements.append(Spacer(1, 15))
            
            title_st = ParagraphStyle('T', parent=styles['Title'], alignment=TA_CENTER, fontSize=18)
            elements.append(Paragraph(f"ORÇAMENTO", title_st))
            elements.append(Spacer(1, 10))
            
            # Dados do Cliente
            elements.append(Paragraph(f"<b>Cliente:</b> {res['cliente']}", styles['Normal']))
            elements.append(Paragraph(f"<b>Telefone:</b> {res['telefone']}", styles['Normal']))
            elements.append(Paragraph(f"<b>Morada:</b> {res['morada']}", styles['Normal']))
            elements.append(Paragraph(f"<b>Data:</b> {date.today().strftime('%d/%m/%Y')}", styles['Normal']))
            elements.append(Spacer(1, 20))
            
            # Tabela de Itens
            data_pdf = [["Descrição", "Un", "Qtd", "Preço Unit.", "Total"]]
            for _, r in df_finais.iterrows():
                data_pdf.append([
                    Paragraph(r["DESCRIÇÃO"], styles['Normal']), 
                    r["UNID"], 
                    f"{r['Quantidade']}", 
                    f"{r['Preço Unitário']:,.2f}€", 
                    f"{r['Total_Linha']:,.2f}€"
                ])
            
            # Linhas de Total
            data_pdf.append(["", "", "", "SUBTOTAL:", f"{subtotal:,.2f}€"])
            data_pdf.append(["", "", "", f"IVA ({iva_p}%):", f"{valor_iva:,.2f}€"])
            data_pdf.append(["", "", "", "TOTAL FINAL:", f"{total_final:,.2f}€"])
            
            table = Table(data_pdf, colWidths=[240, 30, 40, 80, 80])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#eeeeee")),
                ('GRID', (0,0), (-1,-4), 0.5, colors.grey),
                ('ALIGN', (3,0), (-1,-1), 'RIGHT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ]))
            elements.append(table)
            
            if res["notas"]:
                elements.append(Spacer(1, 20))
                elements.append(Paragraph("<b>Observações:</b>", styles['Normal']))
                elements.append(Paragraph(res["notas"], styles['Normal']))
                
            doc.build(elements)
            st.download_button("⬇️ Baixar PDF", pdf_buffer.getvalue(), f"Orcamento_{res['cliente']}.pdf", "application/pdf")
            
        with c_xls:
            output_ex = io.BytesIO()
            with pd.ExcelWriter(output_ex, engine='xlsxwriter') as writer:
                df_finais.to_excel(writer, index=False, sheet_name='Itens')
                pd.DataFrame([{"Subtotal": subtotal, "IVA": valor_iva, "Total": total_final}]).to_excel(writer, index=False, sheet_name='Resumo')
            st.download_button("⬇️ Baixar Excel", output_ex.getvalue(), f"Orcamento_{res['cliente']}.xlsx")
    else:
        st.warning("Adicione quantidades para ver o total.")

# --------------------------------------------------
# 5. Tabelas de Edição (Corpo)
# --------------------------------------------------
st.divider()
st.subheader("🔍 1. Pesquisar e Adicionar Artigos")
pesquisa = st.text_input("Filtrar por nome ou código...")

mask = res["dados"]["DESCRIÇÃO"].str.contains(pesquisa, case=False, na=False)
df_search = res["dados"][mask & (res["dados"]["Quantidade"] == 0)]

st.data_editor(
    df_search,
    column_config={
        "CÓDIGO": None, 
        "Preço Unitário": st.column_config.NumberColumn("Preço (€)", format="%.2f", disabled=True),
        "Quantidade": st.column_config.NumberColumn("Qtd", min_value=0.0)
    },
    hide_index=True, use_container_width=True,
    key=f"search_{st.session_state['orc_atual']}",
    on_change=sincronizar_dados, args=(f"search_{st.session_state['orc_atual']}",)
)

st.markdown("---")
st.subheader("📝 2. Itens Apurados (Lista Final)")

df_apurados = res["dados"][res["dados"]["Quantidade"] > 0]

if not df_apurados.empty:
    st.data_editor(
        df_apurados,
        column_config={
            "DESCRIÇÃO": st.column_config.TextColumn("Artigo", width="large", disabled=True),
            "Preço Unitário": st.column_config.NumberColumn("V. Unit (€)", format="%.2f"),
            "Quantidade": st.column_config.NumberColumn("Qnt", min_value=0.0)
        },
        hide_index=True, use_container_width=True,
        num_rows="dynamic",
        key=f"edit_{st.session_state['orc_atual']}",
        on_change=sincronizar_dados, args=(f"edit_{st.session_state['orc_atual']}",)
    )
    res["notas"] = st.text_area("Notas / Observações", res["notas"])

# --------------------------------------------------
# 6. Sidebar
# --------------------------------------------------
with st.sidebar:
    st.header("💾 Backup")
    st.download_button("📥 Guardar Backup", pickle.dumps(st.session_state["lista_orcamentos"]), f"backup_{date.today()}.pkl")
    if st.button("➕ Novo Orçamento"):
        novo = f"Orçamento {len(st.session_state['lista_orcamentos']) + 1}"
        st.session_state["lista_orcamentos"][novo] = {
            "cliente": "", "morada": "", "telefone": "", "obra": "", "data_visita": date.today(), "notas": "", "dados": carregar_base_limpa()
        }
        st.session_state["orc_atual"] = novo
        st.rerun()
