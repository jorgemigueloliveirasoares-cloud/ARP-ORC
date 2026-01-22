import streamlit as st
import pandas as pd
import os

# 1. CONFIGURAÇÃO
st.set_page_config(page_title="Gestor de Orçamentos", layout="wide")

# 2. CARREGAMENTO E LIMPEZA DA BASE
def carregar_base():
    caminho = "Cópia de Preços Tabela atual.xlsx"
    if os.path.exists(caminho):
        try:
            df = pd.read_excel(caminho)
            df.columns = [str(c).strip() for c in df.columns]
            
            # Mapeamento dinâmico das colunas
            col_preco = "VALORES ATUAIS JANEIRO 2025"
            df = df[["CÓDIGO", "DESCRIÇÃO", "UNID", col_preco]].dropna(subset=["CÓDIGO"])
            df.rename(columns={col_preco: "Preço Unitário"}, inplace=True)
            
            # Limpeza crucial: remover espaços e converter tudo para texto para a pesquisa funcionar
            df["CÓDIGO"] = df["CÓDIGO"].astype(str).str.strip()
            df["DESCRIÇÃO"] = df["DESCRIÇÃO"].astype(str).str.strip()
            df["Preço Unitário"] = pd.to_numeric(df["Preço Unitário"], errors='coerce').fillna(0.0)
            
            return df
        except Exception as e:
            st.error(f"Erro ao carregar Excel: {e}")
    return pd.DataFrame(columns=["CÓDIGO", "DESCRIÇÃO", "UNID", "Preço Unitário"])

# Inicialização do Estado
if "base_dados" not in st.session_state:
    st.session_state.base_dados = carregar_base()

if "itens_orcamento" not in st.session_state:
    st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])

# 3. ÁREA DE PESQUISA (MELHORADA)
st.subheader("🔍 1. Pesquisar e Adicionar")
# O segredo para a pesquisa não falhar é garantir que o termo de pesquisa é limpo
termo = st.text_input("Pesquise por nome ou código (ex: picar, lixar, arp...):", key="search_bar").strip()

if termo:
    # Filtro que ignora maiúsculas/minúsculas e lida com valores NA
    base = st.session_state.base_dados
    mask = (base["DESCRIÇÃO"].str.contains(termo, case=False, na=False)) | \
           (base["CÓDIGO"].str.contains(termo, case=False, na=False))
    
    resultados = base[mask].head(15)
    
    if not resultados.empty:
        # Layout da lista de resultados
        for i, row in resultados.iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([1, 4, 1, 1, 0.5])
                c1.write(f"**{row['CÓDIGO']}**")
                c2.write(row["DESCRIÇÃO"])
                c3.write(f"{row['Preço Unitário']:.2f}€")
                
                # Input de Qtd sem os botões + / - (apenas manual)
                qtd_input = c4.text_input("Qtd", key=f"q_in_{row['CÓDIGO']}", label_visibility="collapsed", placeholder="0")
                
                if c5.button("➕", key=f"btn_add_{row['CÓDIGO']}"):
                    if qtd_input:
                        try:
                            val_qtd = float(qtd_input.replace(',', '.'))
                            if val_qtd > 0:
                                novo_item = pd.DataFrame([{
                                    "CÓDIGO": row["CÓDIGO"],
                                    "Artigo": row["DESCRIÇÃO"],
                                    "UNID": row["UNID"],
                                    "Preço Unitário": row["Preço Unitário"],
                                    "Quantidade": val_qtd
                                }])
                                st.session_state.itens_orcamento = pd.concat([st.session_state.itens_orcamento, novo_item], ignore_index=True)
                                st.rerun()
                        except ValueError:
                            st.toast(f"Quantidade inválida para {row['CÓDIGO']}", icon="⚠️")
    else:
        st.warning("Nenhum artigo encontrado com esse termo.")

# 4. ITENS APURADOS (COM COLUNA DE SUBTOTAL)
st.divider()
st.subheader("📝 2. Itens Apurados")

if not st.session_state.itens_orcamento.empty:
    # Preparar DataFrame para o Editor (com cálculo do subtotal)
    df_apurados = st.session_state.itens_orcamento.copy()
    df_apurados["Subtotal (€)"] = df_apurados["Quantidade"] * df_apurados["Preço Unitário"]
    
    # Editor de dados
    df_editado = st.data_editor(
        df_apurados,
        use_container_width=True,
        hide_index=True,
        column_config={
            "CÓDIGO": st.column_config.TextColumn("Cód", disabled=True),
            "Artigo": st.column_config.TextColumn("Descrição", disabled=True),
            "UNID": st.column_config.TextColumn("UNID", disabled=True),
            "Preço Unitário": st.column_config.NumberColumn("V. Unit (€)", format="%.2f"),
            "Quantidade": st.column_config.NumberColumn("Qtd", format="%.2f"),
            "Subtotal (€)": st.column_config.NumberColumn("Subtotal (€)", format="%.2f", disabled=True)
        },
        key="editor_apurados"
    )
    
    # Rodapé com Totais
    c_tot, c_upd = st.columns([4, 1])
    total_geral = df_editado["Subtotal (€)"].sum()
    c_tot.markdown(f"### **Total Geral: {total_geral:,.2f} €**")
    
    if c_upd.button("💾 Atualizar Cálculos", use_container_width=True):
        # Salva apenas as colunas base (o subtotal é recalculado na visualização)
        st.session_state.itens_orcamento = df_editado[["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"]]
        st.rerun()
else:
    st.info("A lista de orçamento está vazia.")

# Sidebar para limpar
with st.sidebar:
    if st.button("🗑️ Limpar Todo o Orçamento"):
        st.session_state.itens_orcamento = pd.DataFrame(columns=["CÓDIGO", "Artigo", "UNID", "Preço Unitário", "Quantidade"])
        st.rerun()
