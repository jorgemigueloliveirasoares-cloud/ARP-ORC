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
# 2. Funções de Dados
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
            st.error("Erro ao carregar colunas do Excel. Verifique o ficheiro.")
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário", "Quantidade"])

def sincronizar_dados(key_editor):
    """Sincroniza as tabelas editáveis com a base de dados principal na sessão"""
    if key_editor in st.session_state:
        edicoes = st.session_state[key_editor]
        res = st.session_state["lista_orcamentos"][st.session_state["orc_atual"]]
        
        # Processar alterações de valores (Preço ou Quantidade)
        for row_idx, alteracoes in edicoes["edited_rows"].items():
            for col, val in alteracoes.items():
                res["dados"].at[row_idx, col] = val
        
        # Processar remoções (O 'X' ou Delete na tabela)
        for row_idx in edicoes["deleted_rows"]:
            res["dados"].at[row_idx, "Quantidade"] = 0.0

# --------------------------------------------------
# 3. Inicialização do Estado
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
# 4. Interface de Cabeçalho (Dados do Cliente e Exportação)
# --------------------------------------------------
col_log, col_info, col_exp = st.columns([1, 2, 1.2])

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
    st.markdown("### 📄 Exportação")
    iva_p = st.selectbox("IVA (%)", [0, 6, 13, 23], index=3)
    
    # Calcular Totais
    df_finais = res["dados"][res["dados"]["Quantidade"] > 0].copy()
    if not df_finais.empty:
        df_finais["Total"] = df_finais["Quantidade"] * df_finais["Preço Unitário"]
        subtotal = df_finais["Total"].sum()
        total_final = subtotal * (1 + iva_p/100)
        
        st.markdown(f"**Subtotal:** {subtotal:.2f} €")
        st.markdown(f"**Total c/ IVA:** {total_final:.2f} €")
        
        # Botão PDF (Simplificado)
        if st.button("Gerar Orçamento PDF"):
            st.success("PDF pronto para download (Implementar função doc.build)")
    else:
        st.caption("Adicione itens na pesquisa para exportar.")

# --------------------------------------------------
# 5. Pesquisa de Artigos
# --------------------------------------------------
st.divider()
st.subheader("🔍 1. Pesquisar Artigos")
pesquisa = st.text_input("Filtrar por nome ou código...")

# Mostrar itens que não estão na lista de apurados
mask = res["dados"]["DESCRIÇÃO"].str.contains(pesquisa, case=False, na=False)
df_search = res["dados"][mask & (res["dados"]["Quantidade"] == 0)]

st.data_editor(
    df_search,
    column_config={
        "CÓDIGO": st.column_config.TextColumn("Cód", width="small", disabled=True),
        "DESCRIÇÃO": st.column_config.TextColumn("Descrição", width="large", disabled=True),
        "UNID": st.column_config.TextColumn("UN", width="small", disabled=True),
        "Preço Unitário": st.column_config.NumberColumn("Preço Base (€)", format="%.2f", disabled=True),
        "Quantidade": st.column_config.NumberColumn("Adicionar Qnt", min_value=0.0)
    },
    hide_index=True, use_container_width=True,
    key=f"search_{st.session_state['orc_atual']}",
    on_change=sincronizar_dados, args=(f"search_{st.session_state['orc_atual']}",)
)

# --------------------------------------------------
# 6. Itens Apurados (Com eliminação de linha)
# --------------------------------------------------
st.markdown("---")
st.subheader("📝 2. Itens Apurados (Lista Final)")

df_apurados = res["dados"][res["dados"]["Quantidade"] > 0]

if not df_apurados.empty:
    st.info("💡 **Para eliminar uma linha:** Selecione-a na margem esquerda e prima a tecla **Delete** no teclado ou utilize o ícone de lixo.")
    
    st.data_editor(
        df_apurados,
        column_config={
            "DESCRIÇÃO": st.column_config.TextColumn("Artigo", width="large", disabled=True),
            "UNID": st.column_config.TextColumn("UM", width="small", disabled=True),
            "Preço Unitário": st.column_config.NumberColumn("V. Unit (€)", format="%.2f"),
            "Quantidade": st.column_config.NumberColumn("Qnt", min_value=0.0)
        },
        hide_index=True, 
        use_container_width=True,
        num_rows="dynamic",  # Ativa a funcionalidade de adicionar/remover linhas
        key=f"edit_{st.session_state['orc_atual']}",
        on_change=sincronizar_dados, args=(f"edit_{st.session_state['orc_atual']}",)
    )
    
    # Notas adicionais
    res["notas"] = st.text_area("Notas / Observações do Orçamento", res["notas"])
else:
    st.write("Nenhum item selecionado. Use a barra de pesquisa acima.")

# --------------------------------------------------
# 7. Sidebar (Gestão de Ficheiros)
# --------------------------------------------------
with st.sidebar:
    st.title("Configurações")
    if st.button("🗑️ Limpar Tudo"):
        st.session_state.clear()
        st.rerun()
    
    st.divider()
    st.markdown("### Backup Local")
    st.download_button("💾 Guardar Progresso", pickle.dumps(st.session_state["lista_orcamentos"]), "backup.pkl")
