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

# --------------------------------------------------
# 2. Funções de Dados e Sincronização
# --------------------------------------------------
def carregar_base_limpa():
    if os.path.exists(EXCEL_PATH):
        try:
            df = pd.read_excel(EXCEL_PATH)
            # Define as colunas exatas do teu ficheiro
            colunas = ["CÓDIGO", "DESCRIÇÃO", "UNID", "VALORES ATUAIS JANEIRO 2025"]
            df = df[colunas].dropna(subset=["DESCRIÇÃO"])
            df.rename(columns={"VALORES ATUAIS JANEIRO 2025": "Preço Unitário"}, inplace=True)
            df["Quantidade"] = 0.0
            # Converter códigos para texto para evitar erros de pesquisa
            df["CÓDIGO"] = df["CÓDIGO"].astype(str)
            return df
        except Exception as e:
            st.error(f"Erro ao ler o ficheiro Excel: {e}")
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário", "Quantidade"])

def sincronizar_dados(key_editor):
    """
    Usa o índice real do DataFrame para garantir que a edição 
    corresponde sempre ao artigo certo, mesmo com filtros ativos.
    """
    if key_editor in st.session_state:
        edicoes = st.session_state[key_editor]
        res = st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]
        
        # Sincroniza edições (Quantidade ou Preço Unitário)
        for row_idx, alteracoes in edicoes["edited_rows"].items():
            for col, val in alteracoes.items():
                res["dados"].at[row_idx, col] = val
        
        # Sincroniza remoções (quando apagas a linha com X ou Delete)
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
# 4. Interface Superior (Cabeçalho e Totais)
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
    st.markdown("### 📄 Exportação e Valores")
    iva_p = st.selectbox("IVA (%)", [0, 6, 13, 23], index=3)
    
    df_finais = res["dados"][res["dados"]["Quantidade"] > 0].copy()
    
    if not df_finais.empty:
        df_finais["Total_Linha"] = df_finais["Quantidade"] * df_finais["Preço Unitário"]
        subtotal = df_finais["Total_Linha"].sum()
        total_final = subtotal * (1 + iva_p/100)
        
        st.markdown(f"**Total Orçamentado: {total_final:,.2f} €**")
        
        # Botões de Download
        c_pdf, c_xls = st.columns(2)
        with c_pdf:
            # Geração do PDF
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = []
            
            if os.path.exists(LOGO_PATH):
                elements.append(Image(LOGO_PATH, width=100, height=50))
            
            elements.append(Paragraph(f"Orçamento - {res['cliente']}", styles['Title']))
            
            # Tabela simples para o PDF
            data_pdf = [["Artigo", "Qtd", "Preço", "Total"]]
            for _, r in df_finais.iterrows():
                data_pdf.append([r["DESCRIÇÃO"][:50], r["Quantidade"], f"{r['Preço Unitário']:.2f}€", f"{r['Total_Linha']:.2f}€"])
            
            t = Table(data_pdf)
            t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
            elements.append(t)
            doc.build(elements)
            st.download_button("⬇️ PDF", pdf_buffer.getvalue(), f"Orcamento_{res['cliente']}.pdf")
            
        with c_xls:
            output_ex = io.BytesIO()
            with pd.ExcelWriter(output_ex, engine='xlsxwriter') as writer:
                df_finais.to_excel(writer, index=False, sheet_name='Orçamento')
            st.download_button("⬇️ Excel", output_ex.getvalue(), f"Orcamento_{res['cliente']}.xlsx")
    else:
        st.info("Adicione itens para ver o total.")

# --------------------------------------------------
# 5. Zona de Pesquisa (Resolvendo a troca de itens)
# --------------------------------------------------
st.divider()
st.subheader("🔍 1. Pesquisar e Adicionar Artigos")
pesquisa = st.text_input("Pesquise por NOME ou CÓDIGO do artigo...")

# Filtro duplo (Código ou Nome)
mask_pesquisa = (
    res["dados"]["DESCRIÇÃO"].str.contains(pesquisa, case=False, na=False) | 
    res["dados"]["CÓDIGO"].str.contains(pesquisa, case=False, na=False)
)

# Mostra apenas o que não tem quantidade e corresponde à pesquisa
df_search = res["dados"][mask_pesquisa & (res["dados"]["Quantidade"] == 0)]

st.data_editor(
    df_search,
    column_config={
        "CÓDIGO": st.column_config.TextColumn("Cód", disabled=True),
        "DESCRIÇÃO": st.column_config.TextColumn("Artigo", disabled=True),
        "Preço Unitário": st.column_config.NumberColumn("Preço Base (€)", format="%.2f", disabled=True),
        "Quantidade": st.column_config.NumberColumn("Qtd", min_value=0.0)
    },
    hide_index=False, # MANTIDO FALSO para garantir que o Streamlit usa o índice real da base de dados
    use_container_width=True,
    key=f"search_{st.session_state['orc_atual']}",
    on_change=sincronizar_dados, args=(f"search_{st.session_state['orc_atual']}",)
)

# --------------------------------------------------
# 6. Itens Apurados
# --------------------------------------------------
st.markdown("---")
st.subheader("📝 2. Itens no Orçamento (Apurados)")

df_apurados = res["dados"][res["dados"]["Quantidade"] > 0]

if not df_apurados.empty:
    st.data_editor(
        df_apurados,
        column_config={
            "CÓDIGO": st.column_config.TextColumn("Cód", disabled=True),
            "DESCRIÇÃO": st.column_config.TextColumn("Artigo", disabled=True),
            "Preço Unitário": st.column_config.NumberColumn("V. Unit (€)", format="%.2f"),
            "Quantidade": st.column_config.NumberColumn("Qtd", min_value=0.0)
        },
        hide_index=False, 
        use_container_width=True,
        num_rows="dynamic",
        key=f"edit_{st.session_state['orc_atual']}",
        on_change=sincronizar_dados, args=(f"edit_{st.session_state['orc_atual']}",)
    )
    res["notas"] = st.text_area("Observações", res["notas"])
else:
    st.warning("Nenhum item adicionado.")
