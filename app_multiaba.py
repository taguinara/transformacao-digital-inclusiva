# -*- coding: utf-8 -*-
"""
Dashboard multi-aba da Curadoria TDI – IBICT PD&I.
Execute localmente:  streamlit run app.py
Publicação: Streamlit Community Cloud (ver README / instruções).

Fontes de dados (nesta ordem):
  1) CSVs em ./saida (gerados por ler_excel.py e metadados.py)
  2) Upload de um arquivo .xlsx (cada planilha vira uma aba)
"""

import re
import unicodedata
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

PASTA = Path(__file__).parent / "saida"
URL_RE = re.compile(r"https?://[^\s;,|<>\"')\]]+")

ABAS = {  # chave -> (rótulo, arquivo, descrição)
    "recursos":    ("Recursos", "catalogo_recursos.csv",
                    "Catálogo de recursos curados."),
    "vocabulario": ("Vocabulário controlado", "vocabulario_controlado.csv",
                    "Termos oficialmente adotados."),
    "novos":       ("Novos termos", "novos_termos.csv",
                    "Termos candidatos à inclusão no vocabulário."),
    "relacoes":    ("Relações", "relacoes.csv",
                    "Relações entre termos e recursos."),
    "fontes":      ("Fontes", "fontes.csv",
                    "Fontes de informação consultadas."),
    "avaliacoes":  ("Avaliações", "avaliacoes.csv",
                    "Avaliações realizadas na curadoria."),
}

# Paleta Okabe-Ito: segura para daltonismo
COR_NORMAL = "#0072B2"
COR_ALTO = "#FFD600"

st.set_page_config(page_title="Curadoria TDI | IBICT PD&I", page_icon="📚",
                   layout="wide", initial_sidebar_state="expanded")

components.html(
    "<script>window.parent.document.documentElement.lang='pt-BR';</script>",
    height=0,
)


# ----------------------------------------------------------------- dados
def norm(s):
    t = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


@st.cache_data(show_spinner="Carregando abas…")
def carregar_csvs():
    dfs = {}
    for _, (rotulo, arq, _) in ABAS.items():
        p = PASTA / arq
        if p.exists():
            dfs[rotulo] = pd.read_csv(p, sep=";", dtype=str,
                                      encoding="utf-8-sig").fillna("")
    return dfs


@st.cache_data(show_spinner="Lendo o Excel…")
def carregar_excel(conteudo: bytes):
    planilhas = pd.read_excel(conteudo, sheet_name=None, dtype=str)
    return {str(k): v.fillna("") for k, v in planilhas.items()}


def colunas_url(df):
    cols = []
    for c in df.columns:
        v = df[c][df[c] != ""].head(200)
        if len(v) and v.str.match(URL_RE).mean() > 0.5:
            cols.append(c)
    return cols


def colunas_categoricas(df, urls):
    cols = []
    for c in df.columns:
        if c in urls:
            continue
        v = df[c][df[c] != ""]
        if len(v) == 0:
            continue
        n = v.nunique()
        if 2 <= n <= 60 and n <= 0.6 * len(df) and v.str.len().mean() < 80:
            cols.append(c)
    return cols


dfs = carregar_csvs()

# ----------------------------------------------------------- acessibilidade
st.sidebar.title("Curadoria TDI")
st.sidebar.caption("IBICT · Projeto PD&I")

with st.sidebar.expander("♿ Acessibilidade", expanded=True):
    fs = st.select_slider("Tamanho do texto", [90, 100, 115, 130, 150],
                          value=100, format_func=lambda v: f"{v}%")
    alto = st.checkbox("Alto contraste")
    sem_anim = st.checkbox("Reduzir animações")

if not dfs:
    st.sidebar.info("Nenhum CSV encontrado em `saida/`. "
                    "Envie o Excel para visualizar.")
    arq = st.sidebar.file_uploader("Arquivo Excel (.xlsx)", type=["xlsx"])
    if arq is None:
        st.title("Curadoria TDI")
        st.info("Envie um arquivo Excel na barra lateral, ou rode "
                "`python ler_excel.py` e `python metadados.py` e inclua a "
                "pasta `saida/` no repositório.")
        st.stop()
    dfs = carregar_excel(arq.getvalue())

# cores conforme tema
if alto:
    BG, TXT, COR, GRID = "#000000", "#FFFFFF", COR_ALTO, "#767676"
else:
    BG, TXT, COR, GRID = "#FFFFFF", "#14213D", COR_NORMAL, "#C9D3DF"

CSS = f"""
<style>
html {{ font-size: {fs}%; }}
:focus-visible {{ outline: 3px solid #D55E00 !important; outline-offset: 2px; }}
[data-testid="stMetric"] {{
    border: 1px solid {GRID}; border-left: 6px solid {COR};
    border-radius: 8px; padding: .6rem .9rem;
}}
.stTabs [data-baseweb="tab"] {{ font-weight: 600; }}
a {{ text-decoration: underline; }}
@media (prefers-reduced-motion: reduce) {{
  * {{ animation: none !important; transition: none !important; }}
}}
</style>
"""
if sem_anim:
    CSS += ("<style>*{animation:none!important;transition:none!important;"
            "scroll-behavior:auto!important;}</style>")
if alto:
    CSS += """
<style>
.stApp, [data-testid="stSidebar"], [data-testid="stHeader"] {
    background:#000 !important; }
.stApp *, [data-testid="stSidebar"] * { color:#fff !important; }
.stApp a { color:#FFD600 !important; }
input, textarea, [data-baseweb="select"] > div, [data-baseweb="input"] {
    background:#111 !important; border-color:#fff !important; }
button { border:2px solid #fff !important; }
[data-testid="stMetric"] { border-color:#fff !important; }
.stTabs [aria-selected="true"] { border-bottom:4px solid #FFD600 !important; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------- gráficos
def barras(df, rotulo_cat, top, explodir, key):
    s = df[rotulo_cat]
    s = s[s != ""]
    if explodir:
        s = s.str.split(r"\s*[;|]\s*", regex=True).explode().str.strip()
        s = s[s != ""]
    c = (s.value_counts().head(top).rename_axis("Categoria")
         .reset_index(name="Quantidade"))
    base = alt.Chart(c).encode(
        y=alt.Y("Categoria:N", sort="-x", title=None,
                axis=alt.Axis(labelLimit=420)),
        x=alt.X("Quantidade:Q", title="Quantidade de registros"),
        tooltip=["Categoria", "Quantidade"])
    graf = (base.mark_bar(color=COR) +
            base.mark_text(align="left", dx=4, color=TXT, fontSize=13)
            .encode(text="Quantidade:Q"))
    graf = (graf.properties(height=max(180, 30 * len(c)), background=BG)
            .configure_axis(labelColor=TXT, titleColor=TXT, gridColor=GRID,
                            domainColor=TXT, labelFontSize=13,
                            titleFontSize=14)
            .configure_view(strokeWidth=0))
    return graf, c


# ------------------------------------------------------------------ abas
def render_aba(rotulo, df, chave, descricao=""):
    if df.empty:
        st.info("Esta aba não possui registros.")
        return
    if descricao:
        st.caption(descricao)

    urls = colunas_url(df)
    cats = colunas_categoricas(df, urls)

    # ---- filtros
    with st.expander("🔎 Busca e filtros", expanded=True):
        busca = st.text_input("Buscar em todas as colunas (sem acentos)",
                              key=f"b_{chave}")
        filtros = {}
        if cats:
            escolhidas = st.multiselect("Filtrar por coluna", cats,
                                        key=f"fc_{chave}")
            for c in escolhidas:
                op = sorted(df[c][df[c] != ""].unique())
                filtros[c] = st.multiselect(c, op, key=f"f_{chave}_{c}")

    f = df
    if busca:
        alvo = norm(busca)
        base = df.astype(str).apply(lambda col: col.map(norm))
        f = f[base.apply(lambda r: alvo in " ".join(r), axis=1)]
    for c, vals in filtros.items():
        if vals:
            f = f[f[c].isin(vals)]

    # ---- indicadores
    k1, k2, k3, k4 = st.columns(4)
    pct = 100 * (df != "").to_numpy().mean()
    k1.metric("Registros exibidos", f"{len(f):,}".replace(",", "."))
    k2.metric("Total na aba", f"{len(df):,}".replace(",", "."))
    k3.metric("Colunas", len(df.columns))
    k4.metric("Preenchimento", f"{pct:.0f}%")

    if f.empty:
        st.warning("Nenhum registro encontrado com os filtros atuais.")
        return

    # ---- gráfico
    if cats:
        st.subheader("Distribuição")
        c1, c2, c3 = st.columns([3, 1, 2])
        col = c1.selectbox("Agrupar por", cats, key=f"g_{chave}")
        top = c2.number_input("Top", 5, 30, 10, key=f"t_{chave}")
        expl = c3.checkbox("Separar valores múltiplos (; ou |)",
                           value=True, key=f"e_{chave}")
        graf, dados = barras(f, col, int(top), expl, chave)
        st.altair_chart(graf, use_container_width=True)
        with st.expander("Ver os dados do gráfico em tabela (alternativa "
                         "textual)"):
            st.dataframe(dados, hide_index=True, use_container_width=True)

    # ---- tabela
    st.subheader("Tabela de registros")
    cfg = {c: st.column_config.LinkColumn(c, display_text=r"https?://(?:www\.)?([^/]+)")
           for c in urls}
    vis = f.reset_index(drop=True)
    if alto:
        vis = vis.style.set_properties(
            **{"background-color": "#000000", "color": "#FFFFFF"})
    st.dataframe(vis, column_config=cfg, hide_index=True,
                 use_container_width=True, height=420)
    st.download_button("⬇️ Baixar seleção (CSV)",
                       f.to_csv(index=False, sep=";").encode("utf-8-sig"),
                       file_name=f"{norm(rotulo).replace(' ', '_')}.csv",
                       mime="text/csv", key=f"d_{chave}")

    # ---- ficha
    with st.expander("📄 Ficha de um registro"):
        primeira = f.columns[0]
        opcoes = list(f.index)
        i = st.selectbox(
            "Escolha o registro", opcoes, key=f"r_{chave}",
            format_func=lambda x: f"{str(f.loc[x, primeira])[:90] or '(sem título)'}")
        for c, v in f.loc[i].items():
            if v != "":
                st.markdown(f"**{c}:** {v}")


st.title("📚 Curadoria TDI")
st.markdown("Painel de visualização da curadoria – **IBICT · Projeto PD&I**.")

rotulos = list(dfs.keys())
abas = st.tabs(["Visão geral"] + rotulos)

with abas[0]:
    resumo = pd.DataFrame({
        "Aba": rotulos,
        "Registros": [len(dfs[r]) for r in rotulos],
        "Colunas": [len(dfs[r].columns) for r in rotulos],
    })
    cols = st.columns(min(len(rotulos), 6) or 1)
    for col, (_, r) in zip(cols, resumo.iterrows()):
        col.metric(r["Aba"], f"{r['Registros']:,}".replace(",", "."))
    graf = (alt.Chart(resumo).mark_bar(color=COR).encode(
        y=alt.Y("Aba:N", sort="-x", title=None),
        x=alt.X("Registros:Q", title="Registros"),
        tooltip=["Aba", "Registros", "Colunas"])
        .properties(height=max(180, 38 * len(resumo)), background=BG)
        .configure_axis(labelColor=TXT, titleColor=TXT, gridColor=GRID,
                        domainColor=TXT, labelFontSize=13, titleFontSize=14)
        .configure_view(strokeWidth=0))
    st.altair_chart(graf, use_container_width=True)
    with st.expander("Ver em tabela"):
        st.dataframe(resumo, hide_index=True, use_container_width=True)

desc = {v[0]: v[2] for v in ABAS.values()}
for aba, r in zip(abas[1:], rotulos):
    with aba:
        render_aba(r, dfs[r], norm(r).replace(" ", "_"), desc.get(r, ""))

st.divider()
st.caption("IBICT · Projeto PD&I · Painel desenvolvido com Streamlit. "
           "Gráficos com paleta segura para daltonismo e alternativa em "
           "tabela.")