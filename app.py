import streamlit as st
import pandas as pd
import os
import io

# 1. CONFIGURAÇÃO INICIAL
st.set_page_config(page_title="Gestor de Orçamentos", layout="wide")

# 2. CARREGAMENTO SEGURO DA BASE DE DADOS
@st.cache_data
def carregar_base():
    if os.path.exists("Cópia de Preços Tabela atual.xlsx"):
        try:
            df = pd.read_excel("Cópia de Preços Tabela atual.xlsx")
            df.columns = [c.strip() for c in df.columns]
            # Mapeamento de colunas conforme os seus ficheiros anteriores
            col_preco = "VALORES ATUAIS JANEIRO 2025"
            df = df[["CÓDIGO", "DESCRIÇÃO", "UNID", col_preco]].dropna(subset=["CÓDIGO"])
            df.rename(columns={col_preco: "Preço Unitário"}, inplace=True)
            df["CÓDIGO"] = df["CÓDIGO"].astype(str).str.strip()
            return df
        except Exception as e:
            st.error(f"Erro ao ler Excel: {e}")
    # Base de dados de recurso (fallback) para teste
    return pd.DataFrame({
        "CÓDIGO": ["ARP901-A", "ARP101", "ARP2202"],
        "DESCRIÇÃO": ["Pintar tinta plástica interior/exterior", "Abrir roços em alvernaria", "Proteção da zona a intervir"],
        "UNID": ["m2", "ml", "dia"],
        "Preço Unitário": [10.90, 18.00, 37.80]
    })

# Inicialização do Estado da Sessão
if "base_dados" not in st.session_state:
    st.session_state.base_dados = carregar_base()

if "itens_orcamento" not in st.session_state:
    st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])

# 3. ÁREA DE PESQUISA (CORRIGIDA)
st.subheader("🔍 1. Pesquisar e Adicionar")
pesquisa = st.text_input("Pesquisar por nome ou código:", value="", key="barra_pesquisa")

if pesquisa:
    # Filtro flexível para evitar que "não apareça nada"
    mask = (st.session_state.base_dados["DESCRIÇÃO"].str.contains(pesquisa, case=False, na=False)) | \
           (st.session_state.base_dados["CÓDIGO"].str.contains(pesquisa, case=False, na=False))
    
    resultados = st.session_state.base_dados[mask].head(15)
    
    if not resultados.empty:
        # Cabeçalho da Lista
        h1, h2, h3, h4, h5 = st.columns([1, 3, 1, 1, 0.5])
        h1.caption("**Cód**")
        h2.caption("**Descrição**")
        h3.caption("**Preço**")
        h4.caption("**Qtd**")
        h5.caption("**Add**")
        
        for i, row in resultados.iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([1, 3, 1, 1, 0.5])
                c1.write(row["CÓDIGO"])
                c2.write(row["DESCRIÇÃO"])
                c3.write(f"{row['Preço Unitário']:.2f}€")
                
                # Qtd Manual (Text Input)
                qtd_input = c4.text_input("Qtd", key=f"in_{row['CÓDIGO']}", label_visibility="collapsed")
                
                if c5.button("➕", key=f"btn_{row['CÓDIGO']}"):
                    if qtd_input:
                        try:
                            # Converte vírgulas em pontos para aceitar decimais
                            v_qtd = float(qtd_input.replace(',', '.'))
                            novo = pd.DataFrame([{
                                "CÓDIGO": row["CÓDIGO"],
                                "Artigo": row["DESCRIÇÃO"],
                                "UNID": row["UNID"],
                                "Preço Unitário": row["Preço Unitário"],
                                "Quantidade": v_qtd
                            }])
                            st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo], ignore_index=True)
                            st.rerun()
                        except ValueError:
                            st.toast("⚠️ Insira um número válido", icon="❌")
    else:
        st.warning("Nenhum artigo encontrado com esse termo.")

# 4. ITENS APURADOS (COM CÁLCULO DE TOTAL POR ITEM)
st.divider()
st.subheader("📝 2. Itens Apurados")

if not st.session_state.itens_orcamento.empty:
    # Preparação para visualização com Total
    df_view = st.session_state.itens_orcamento.copy()
    df_view["Total Item (€)"] = df_view["Quantidade"] * df_view["Preço Unitário"]
    
    # Edição apenas de Preço e Quantidade
    df_editado = st.data_editor(
        df_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "CÓDIGO": st.column_config.TextColumn("Cód", disabled=True),
            "Artigo": st.column_config.TextColumn("Descrição", disabled=True),
            "Preço Unitário": st.column_config.NumberColumn("V. Unit (€)", format="%.2f"),
            "Quantidade": st.column_config.NumberColumn("Qtd", format="%.2f"),
            "Total Item (€)": st.column_config.NumberColumn("Subtotal", format="%.2f", disabled=True)
        }
    )
    
    col_tot, col_save = st.columns([3, 1])
    total_geral = df_editado["Total Item (€)"].sum()
    col_tot.markdown(f"### **Total Geral: {total_geral:,.2f} €**")
    
    if col_save.button("💾 Atualizar Totais"):
        st.session_state.itens_orcamento = df_editado[["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"]]
        st.rerun()
else:
    st.info("Utilize a pesquisa acima para adicionar artigos ao orçamento.")
