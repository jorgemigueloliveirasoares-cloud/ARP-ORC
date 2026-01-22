import streamlit as st
import pandas as pd
import os
import io

# 1. CONFIGURAÇÃO
st.set_page_config(page_title="Gestor de Orçamentos", layout="wide")

# 2. CARREGAR DADOS (SIMPLIFICADO PARA O EXEMPLO)
def carregar_base():
    # Simulando a base com base nas tuas imagens (ex: ARP901-A)
    data = {
        "CÓDIGO": ["ARP901 - A", "ARP101", "ARP2202"],
        "DESCRIÇÃO": ["Pintar tinta plástica interior/exterior (regular) < 50m2", "Abrir roços em alvernaria", "Proteção da zona a intervir"],
        "UNID": ["m2", "ml", "dia"],
        "Preço Unitário": [10.90, 18.00, 37.80]
    }
    return pd.DataFrame(data)

if "base_dados" not in st.session_state:
    st.session_state.base_dados = carregar_base()

if "itens_orcamento" not in st.session_state:
    st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])

# 3. PESQUISA E ADIÇÃO
st.subheader("🔍 1. Pesquisar e Adicionar")
pesquisa = st.text_input("Pesquisar por nome ou código:", key="busca")

if pesquisa:
    mask = (st.session_state.base_dados["DESCRIÇÃO"].str.contains(pesquisa, case=False)) | \
           (st.session_state.base_dados["CÓDIGO"].str.contains(pesquisa, case=False))
    resultados = st.session_state.base_dados[mask].head(10)
    
    for i, row in resultados.iterrows():
        cols = st.columns([1, 3, 1, 1, 0.5])
        cols[0].write(row["CÓDIGO"])
        cols[1].write(row["DESCRIÇÃO"])
        cols[2].write(f"{row['Preço Unitário']:.2f}€")
        
        # Campo de texto para Qtd Manual
        qtd_txt = cols[3].text_input("Qtd", key=f"txt_{row['CÓDIGO']}", label_visibility="collapsed")
        
        if cols[4].button("➕", key=f"btn_{row['CÓDIGO']}"):
            if qtd_txt:
                try:
                    v_qtd = float(qtd_txt.replace(',', '.'))
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
                    st.error("Formato de quantidade inválido.")

# 4. ITENS APURADOS COM TOTAL POR LINHA
st.divider()
st.subheader("📝 2. Itens Apurados")

if not st.session_state.itens_orcamento.empty:
    # Criar cópia para visualização com cálculo de total
    df_view = st.session_state.itens_orcamento.copy()
    df_view["Preço Unitário"] = pd.to_numeric(df_view["Preço Unitário"])
    df_view["Quantidade"] = pd.to_numeric(df_view["Quantidade"])
    
    # CÁLCULO DO VALOR TOTAL POR ITEM
    df_view["Total Item (€)"] = df_view["Quantidade"] * df_view["Preço Unitário"]
    
    df_editado = st.data_editor(
        df_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "CÓDIGO": st.column_config.TextColumn("Cód", disabled=True),
            "Artigo": st.column_config.TextColumn("Descrição", disabled=True),
            "Preço Unitário": st.column_config.NumberColumn("V. Unit (€)", format="%.2f"),
            "Quantidade": st.column_config.NumberColumn("Qtd", format="%.2f"),
            "Total Item (€)": st.column_config.NumberColumn("Total Item (€)", format="%.2f", disabled=True)
        }
    )
    
    if st.button("💾 Atualizar Totais"):
        # Grava apenas as colunas originais (sem o total calculado para não duplicar)
        st.session_state.itens_orcamento = df_editado[["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"]]
        st.rerun()
    
    total_geral = df_view["Total Item (€)"].sum()
    st.markdown(f"### **Total Geral: {total_geral:,.2f} €**")
