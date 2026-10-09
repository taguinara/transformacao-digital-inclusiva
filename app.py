# -*- coding: utf-8 -*-
"""
Dashboard de curadoria - Transformação Digital Inclusiva
Execute com:  streamlit run app.py
"""

from pathlib import Path
import pandas as pd
import streamlit as st

CSV = Path("saida/metadados_limpos.csv")

st.set_page_config(
    page_title="Curadoria TDI",
    page_icon="📚",
    layout="wide",
)

# ----------------------------------------------------------------------
# CARREGAR DADOS
# ----------------------------------------------------------------------
@st.cache_data
def carregar():
    df = pd.read_csv(CSV, sep=";", dtype=str).fillna("")
    return df


if not CSV.exists():
    st.error(f"Arquivo '{CSV}' não encontrado. "
             "Rode primeiro `python metadados.py`.")
    st.stop()

df = carregar()

# ----------------------------------------------------------------------
# CABEÇALHO
# ----------------------------------------------------------------------
st.title("📚 Curadoria de Metadados")
st.caption("Projeto: Transformação Digital Inclusiva — cidadania, "
           "acessibilidade e ensino")

# ----------------------------------------------------------------------
# MÉTRICAS
# ----------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Registros", len(df))
col2.metric("Áreas", df["Area"].nunique() if "Area" in df else 0)
col3.metric("Subáreas", df["Subarea"].nunique() if "Subarea" in df else 0)
urls = df["Qtd_URLs"].astype(int).sum() if "Qtd_URLs" in df else 0
col4.metric("URLs de fonte", urls)

st.divider()

# ----------------------------------------------------------------------
# FILTROS (BARRA LATERAL)
# ----------------------------------------------------------------------
st.sidebar.header("🔎 Filtros")

areas = sorted(a for a in df["Area"].unique() if a)
area_sel = st.sidebar.multiselect("Área", areas, default=areas)

subs = sorted(
    s for s in df.loc[df["Area"].isin(area_sel), "Subarea"].unique() if s
)
sub_sel = st.sidebar.multiselect("Subárea", subs, default=subs)

busca = st.sidebar.text_input("Buscar texto (tema, termo, garantia)")

filtrado = df[df["Area"].isin(area_sel) & df["Subarea"].isin(sub_sel)].copy()

if busca:
    mask = filtrado.apply(
        lambda r: busca.lower() in " ".join(r.astype(str)).lower(),
        axis=1,
    )
    filtrado = filtrado[mask]

st.sidebar.caption(f"{len(filtrado)} registro(s) após filtros")

# ----------------------------------------------------------------------
# GRÁFICOS
# ----------------------------------------------------------------------
st.subheader("📊 Distribuição")
g1, g2 = st.columns(2)

with g1:
    st.markdown("**Por Área**")
    st.bar_chart(filtrado["Area"].value_counts())

with g2:
    st.markdown("**Top 10 Subáreas**")
    st.bar_chart(filtrado["Subarea"].value_counts().head(10))

st.divider()

# ----------------------------------------------------------------------
# TABELA
# ----------------------------------------------------------------------
st.subheader("📋 Registros")
colunas_mostrar = [c for c in [
    "Area", "Subarea", "Tema_Escopo",
    "Subarea_Termo", "URLs",
] if c in filtrado.columns]

st.dataframe(
    filtrado[colunas_mostrar],
    use_container_width=True,
    hide_index=True,
)

# ----------------------------------------------------------------------
# DETALHE EXPANSÍVEL
# ----------------------------------------------------------------------
st.subheader("🔍 Detalhe do registro")
if not filtrado.empty:
    idx = st.selectbox(
        "Selecione um tema",
        filtrado.index,
        format_func=lambda i: f"{filtrado.at[i, 'Area']} → "
                              f"{filtrado.at[i, 'Tema_Escopo']}",
    )
    reg = filtrado.loc[idx]
    for col in filtrado.columns:
        valor = str(reg[col]).strip()
        if valor:
            st.markdown(f"**{col}:**{valor}")

# ----------------------------------------------------------------------
# DOWNLOADS
# ----------------------------------------------------------------------
st.divider()
st.subheader("⬇️ Exportar")

c1, c2 = st.columns(2)
with c1:
    st.download_button(
        "Baixar CSV filtrado",
        filtrado.to_csv(index=False, sep=";", encoding="utf-8-sig"),
        file_name="metadados_filtrados.csv",
        mime="text/csv",
    )
with c2:
    st.download_button(
        "Baixar JSON filtrado",
        filtrado.to_json(orient="records", force_ascii=False, indent=2),
        file_name="metadados_filtrados.json",
        mime="application/json",
    )