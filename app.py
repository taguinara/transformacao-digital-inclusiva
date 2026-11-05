# -*- coding: utf-8 -*-
"""
Dashboard de curadoria - Transformação Digital Inclusiva (IBICT · PD&I)
Execute com:  streamlit run app.py
Dados: arquivo .xlsx na raiz do repositório (ou upload na barra lateral)
"""

import html
import io
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

AQUI = Path(__file__).parent
CSV_LIMPO = AQUI / "saida" / "metadados_limpos.csv"
XLSX_PADRAO = "curadoria_digital_vocabulario_controlado_out_2026.xlsx"
URL_RE = re.compile(r"https?://[^\s;,|<>\"')\]]+")
BASE = ["Area", "Subarea", "Tema_Escopo", "Subarea_Termo", "URLs"]

# nomes aceitos (sem acento/espaço/símbolo) para cada coluna-chave
ALIAS = {
    "Area": ["area", "areadoconhecimento", "grandearea"],
    "Subarea": ["subarea"],
    "Tema_Escopo": ["temaescopo", "tema", "escopo", "temaescopogarantia"],
    "Subarea_Termo": ["subareatermo", "termo", "termoautorizado",
                      "termopreferencial"],
    "URLs": ["urls", "url", "link", "links", "fonte", "fontes"],
}
ROTULO = {"Area": "Área", "Subarea": "Subárea", "Tema_Escopo": "Tema",
          "Subarea_Termo": "Termo", "URLs": "URLs"}

# Referência (usada só se a fonte tiver uma única aba, ex.: CSV)
ABAS_QTD = [
    ("Catálogo de recursos", 13), ("Vocabulário controlado", 113),
    ("Novos termos propostos", 25), ("Relações recurso-termo", 27),
    ("Fontes oficiais", 14), ("Avaliações críticas", 0),
]

# Paleta Okabe-Ito (segura para daltonismo)
PALETA = ["#0072B2", "#E69F00", "#009E73", "#CC79A7",
          "#56B4E9", "#D55E00", "#F0E442", "#6A4C93"]

st.set_page_config(page_title="Curadoria TDI | IBICT PD&I", page_icon="📚",
                   layout="wide", initial_sidebar_state="expanded")
components.html(
    "<script>window.parent.document.documentElement.lang='pt-BR';</script>",
    height=0)


def norm(s):
    t = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def chave(s):
    return re.sub(r"[^a-z0-9]", "", norm(s))


def esc(x):
    return html.escape(str(x), quote=True)


def achar_xlsx():
    pref = AQUI / XLSX_PADRAO
    if pref.exists():
        return pref
    cand = sorted(AQUI.glob("*.xlsx")) + sorted((AQUI / "saida").glob("*.xlsx"))
    cand = [p for p in cand if not p.name.startswith("~$")]
    return cand[0] if cand else None


def com_cabecalho(d):
    """Detecta a linha de cabeçalho (ignora títulos/linhas em branco)."""
    d = d.fillna("").astype(str).apply(lambda s: s.str.strip())
    d = d.loc[(d != "").any(axis=1)].reset_index(drop=True)
    if d.empty:
        return pd.DataFrame()
    cont = (d.head(10) != "").sum(axis=1)
    h = next((i for i in range(len(cont))
              if cont.iloc[i] >= max(2, 0.6 * cont.max())), 0)
    nomes, vistos = [], {}
    for j, v in enumerate(d.iloc[h]):
        v = v or f"Coluna {j + 1}"
        n = vistos.get(v, 0)
        vistos[v] = n + 1
        nomes.append(v if n == 0 else f"{v} ({n + 1})")
    corpo = d.iloc[h + 1:].reset_index(drop=True)
    corpo.columns = nomes
    manter = [c for c in nomes
              if not (c.startswith("Coluna ") and (corpo[c] == "").all())]
    return corpo[manter]


@st.cache_data(show_spinner="Lendo o Excel…")
def ler_xlsx(conteudo: bytes):
    brutas = pd.read_excel(io.BytesIO(conteudo), sheet_name=None,
                           header=None, dtype=str)
    return {nome: com_cabecalho(d) for nome, d in brutas.items()}


@st.cache_data(show_spinner="Lendo o CSV…")
def ler_csv(conteudo: bytes):
    d = pd.read_csv(io.BytesIO(conteudo), sep=";", dtype=str,
                    encoding="utf-8-sig").fillna("")
    return {"metadados_limpos": d}


def preparar(d):
    """Mapeia colunas para os nomes-chave; devolve (df, mapa canônico→original)."""
    d = d.copy()
    mapa = {}
    for canon, alias in ALIAS.items():
        for c in d.columns:
            if chave(c) in alias and c not in mapa.values():
                mapa[canon] = c
                break
    # alternativa: usa as primeiras colunas livres como Área/Subárea/Tema
    livres = [c for c in d.columns if c not in mapa.values()]
    for canon in ["Area", "Subarea", "Tema_Escopo"]:
        if canon not in mapa and livres:
            mapa[canon] = livres.pop(0)
    d = d.rename(columns={v: k for k, v in mapa.items()})
    for c in BASE:
        if c not in d.columns:
            d[c] = ""
    if "URLs" not in mapa:  # extrai URLs de qualquer coluna
        d["URLs"] = d.apply(lambda r: " ; ".join(dict.fromkeys(
            u for v in r.astype(str) for u in URL_RE.findall(v))), axis=1)
    d["Qtd_URLs"] = d["URLs"].map(lambda v: len(URL_RE.findall(str(v))))
    return d, mapa


def rot(mapa, canon):
    """Rótulo exibido: nome original da coluna na planilha."""
    return mapa.get(canon, ROTULO.get(canon, canon))


# ------------------------------------------------------------ acessibilidade
st.sidebar.markdown("### 📚 Curadoria TDI")
with st.sidebar.expander("♿ Acessibilidade", expanded=True):
    fs = st.select_slider("Tamanho do texto", [90, 100, 115, 130, 150],
                          value=100, format_func=lambda v: f"{v}%")
    alto = st.checkbox("Alto contraste")
    sem_anim = st.checkbox("Reduzir animações")

# ------------------------------------------------------------------ dados
dados, fonte = None, ""
xlsx = achar_xlsx()
if xlsx is not None:
    dados, fonte = ler_xlsx(xlsx.read_bytes()), xlsx.name
elif CSV_LIMPO.exists():
    dados, fonte = ler_csv(CSV_LIMPO.read_bytes()), CSV_LIMPO.name
else:
    st.sidebar.info("Nenhum arquivo de dados encontrado no repositório. "
                    "Envie o Excel (.xlsx) ou o CSV abaixo.")
    up = st.sidebar.file_uploader("Planilha de curadoria",
                                  type=["xlsx", "csv"])
    if up is None:
        st.title("📚 Curadoria de Metadados")
        st.info(
            "**Os dados da curadoria ainda não foram carregados.**\n\n"
            "Envie a planilha `.xlsx` (ou o CSV) na barra lateral.\n\n"
            f"_Administração: para abrir já com os dados, inclua "
            f"`{XLSX_PADRAO}` na raiz do repositório do GitHub._")
        st.stop()
    dados = (ler_xlsx(up.getvalue()) if up.name.lower().endswith("xlsx")
             else ler_csv(up.getvalue()))
    fonte = up.name

abas_com_dados = [n for n, d in dados.items() if len(d) > 0]
if not abas_com_dados:
    st.error("A planilha não possui abas com registros.")
    st.stop()


def pontuacao(nome):
    _, m = preparar(dados[nome])
    achou = sum(1 for k in ["Area", "Subarea", "Tema_Escopo"]
                if k in m and chave(m[k]) in ALIAS[k])
    return (achou, "vocabulario" in norm(nome), len(dados[nome]))


padrao = max(abas_com_dados, key=pontuacao)
st.sidebar.caption(f"Fonte: {fonte}")
aba_sel = st.sidebar.selectbox(
    "Aba da planilha para explorar", abas_com_dados,
    index=abas_com_dados.index(padrao))
df, mapa = preparar(dados[aba_sel])
R_AREA, R_SUB = rot(mapa, "Area"), rot(mapa, "Subarea")

# ------------------------------------------------------------------- tema
if alto:
    T = dict(bg="#000000", card="#000000", txt="#FFFFFF", mut="#FFFFFF",
             bor="#FFFFFF", h1="#000000", h2="#000000", acc="#FFD600",
             link="#FFD600", on="#FFFFFF")
    COR = "#FFD600"
else:
    T = dict(bg="#F4F8FC", card="#FFFFFF", txt="#14213D", mut="#4A5568",
             bor="#D5DEE8", h1="#0B2545", h2="#0072B2", acc="#0072B2",
             link="#0B5CAD", on="#FFFFFF")
    COR = "#0072B2"

CSS = """
<style>
html{font-size:@fs%;}
.stApp{background:@bg;}
.block-container{padding-top:1.6rem;max-width:1250px;}
:focus-visible{outline:3px solid #D55E00!important;outline-offset:2px;}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);}
.hero{background:linear-gradient(120deg,@h1 0%,@h2 100%);
  color:@on;border-radius:20px;padding:2rem 2.2rem;margin-bottom:1.2rem;
  border:2px solid @bor;position:relative;overflow:hidden;}
.hero:after{content:"";position:absolute;right:-60px;top:-60px;width:260px;
  height:260px;border-radius:50%;background:rgba(255,255,255,.10);}
.hero .eyebrow{letter-spacing:.14em;text-transform:uppercase;font-size:.8rem;
  font-weight:700;margin:0 0 .4rem;color:@on;}
.hero h1{font-size:2.1rem;line-height:1.15;margin:0 0 .5rem;padding:0;color:@on;}
.hero p.sub{margin:0;font-size:1.05rem;color:@on;max-width:60ch;}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
  gap:.8rem;margin:0 0 1.2rem;}
.kpi{background:@card;border:1px solid @bor;border-radius:14px;
  padding:.9rem 1.1rem;border-top:5px solid @acc;}
.kpi .n{font-size:2rem;font-weight:800;color:@txt;line-height:1.1;}
.kpi .l{font-size:.9rem;color:@mut;font-weight:600;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));
  gap:.9rem;}
.card{background:@card;border:1px solid @bor;border-left:8px solid var(--c);
  border-radius:14px;padding:1rem 1.1rem;color:@txt;}
.card h3{font-size:1.05rem;margin:0 0 .35rem;color:@txt;padding:0;}
.card .meta{font-size:.88rem;color:@mut;margin:.1rem 0;}
.card .big{font-size:1.9rem;font-weight:800;color:@txt;line-height:1;}
.bar{height:10px;background:@bor;border-radius:99px;margin:.55rem 0 .3rem;
  overflow:hidden;}
.bar>span{display:block;height:100%;background:var(--c);border-radius:99px;}
.chip{display:inline-block;border:1.5px solid var(--c);border-radius:99px;
  padding:.05rem .6rem;font-size:.8rem;font-weight:600;margin:.15rem .25rem
  .15rem 0;color:@txt;}
.card a{color:@link;font-weight:600;text-decoration:underline;
  margin-right:.7rem;font-size:.9rem;}
.sec{font-size:1.25rem;font-weight:800;color:@txt;margin:1.1rem 0 .6rem;}
@media (prefers-reduced-motion:no-preference){
  .card{transition:transform .15s,box-shadow .15s;}
  .card:hover{transform:translateY(-3px);box-shadow:0 8px 20px rgba(0,0,0,.12);}
}
</style>
"""
for k, v in T.items():
    CSS = CSS.replace("@" + k, v)
CSS = CSS.replace("@fs", str(fs))
if sem_anim:
    CSS += ("<style>*{animation:none!important;transition:none!important;"
            "transform:none!important;scroll-behavior:auto!important;}</style>")
if alto:
    CSS += """<style>
[data-testid="stSidebar"],[data-testid="stHeader"]{background:#000!important;}
.stApp *:not(.hero *):not(.card a){color:#fff!important;}
input,textarea,[data-baseweb="select"]>div{background:#111!important;
  border-color:#fff!important;}
button{border:2px solid #fff!important;}
.stTabs [aria-selected="true"]{border-bottom:4px solid #FFD600!important;}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)

# ------------------------------------------------------------------ filtros
st.sidebar.header("🔎 Filtros")
areas = sorted(a for a in df["Area"].unique() if a)
area_sel = st.sidebar.multiselect(R_AREA, areas, default=areas)
subs = sorted(s for s in df.loc[df["Area"].isin(area_sel), "Subarea"]
              .unique() if s)
sub_sel = st.sidebar.multiselect(R_SUB, subs, default=subs)
busca = st.sidebar.text_input("Buscar texto")

f = df[df["Area"].isin(area_sel) & df["Subarea"].isin(sub_sel)].copy()
if busca:
    alvo = norm(busca)
    f = f[f.apply(lambda r: alvo in norm(" ".join(r.astype(str))), axis=1)]
st.sidebar.caption(f"{len(f)} registro(s) após filtros")

COR_AREA = {a: PALETA[i % len(PALETA)] for i, a in enumerate(areas)}

# --------------------------------------------------------------------- hero
st.markdown(f"""
<header class="hero">
  <p class="eyebrow">IBICT · PD&amp;I</p>
  <h1>Curadoria de Metadados</h1>
  <p class="sub">Transformação Digital Inclusiva — cidadania,
  acessibilidade e ensino.</p>
</header>
<section class="kpis" aria-label="Indicadores gerais">
  <div class="kpi"><div class="n">{len(f)}</div><div class="l">Registros</div></div>
  <div class="kpi"><div class="n">{f["Area"].replace("", pd.NA).nunique()}</div><div class="l">{esc(R_AREA)} (distintos)</div></div>
  <div class="kpi"><div class="n">{f["Subarea"].replace("", pd.NA).nunique()}</div><div class="l">{esc(R_SUB)} (distintos)</div></div>
  <div class="kpi"><div class="n">{int(f["Qtd_URLs"].sum())}</div><div class="l">URLs de fonte</div></div>
</section>
""", unsafe_allow_html=True)

if f.empty:
    st.warning("Nenhum registro encontrado com os filtros atuais.")
    st.stop()

aba1, aba2, aba3, aba4 = st.tabs(
    ["🧭 Painel", "🗂️ Cartões", "📋 Tabela", "⬇️ Exportar"])

# ------------------------------------------------------------------- painel
with aba1:
    # ---- quantitativo por aba da planilha (total, não afetado pelos filtros)
    if len(dados) > 1:
        qa = pd.DataFrame({"Aba": list(dados.keys()),
                           "Registros": [len(d) for d in dados.values()]})
    else:
        qa = pd.DataFrame(ABAS_QTD, columns=["Aba", "Registros"])
    st.markdown('<div class="sec">Quantitativo por aba da planilha</div>',
                unsafe_allow_html=True)
    st.caption("Totais de todas as abas da planilha; não mudam com "
               "os filtros." + ("" if len(dados) > 1 else " (valores de referência)"))
    cards = ""
    for i, r in qa.iterrows():
        n = r["Registros"]
        nota = "nenhum registro até o momento" if n == 0 else \
            ("1 registro" if n == 1 else f"{n} registros")
        cards += (
            f'<article class="card" style="--c:{PALETA[i % len(PALETA)]}">'
            f'<h3>{esc(r["Aba"])}</h3>'
            f'<div class="big">{n}</div>'
            f'<p class="meta">{nota}</p></article>')
    st.markdown(f'<div class="grid">{cards}</div>', unsafe_allow_html=True)
    base = alt.Chart(qa).encode(
        y=alt.Y("Aba:N", sort="-x", title=None,
                axis=alt.Axis(labelLimit=320)),
        x=alt.X("Registros:Q", title="Registros"),
        tooltip=["Aba", "Registros"])
    graf = (base.mark_bar(color=COR, cornerRadiusEnd=6) +
            base.mark_text(align="left", dx=4, fontSize=13, color=T["txt"])
            .encode(text="Registros:Q"))
    graf = (graf.properties(height=250, background=T["card"])
            .configure_axis(labelColor=T["txt"], titleColor=T["txt"],
                            gridColor=T["bor"], domainColor=T["txt"],
                            labelFontSize=13, titleFontSize=14)
            .configure_view(strokeWidth=0))
    st.altair_chart(graf, use_container_width=True)
    with st.expander("Ver quantitativo em tabela"):
        tab = pd.concat([qa, pd.DataFrame(
            [{"Aba": "Total", "Registros": int(qa["Registros"].sum())}])])
        st.dataframe(tab, hide_index=True, use_container_width=True)

    st.markdown('<div class="sec">Áreas do conhecimento</div>',
                unsafe_allow_html=True)
    cont = f["Area"].value_counts()
    total = int(cont.sum())
    cards = ""
    for area, n in cont.items():
        pct = 100 * n / total
        nsub = f.loc[f["Area"] == area, "Subarea"].replace("", pd.NA).nunique()
        cards += (
            f'<article class="card" style="--c:{COR_AREA.get(area, COR)}">'
            f'<h3>{esc(area or "(sem área)")}</h3>'
            f'<div class="big">{n}</div>'
            f'<div class="bar" role="img" aria-label="{pct:.0f}% dos registros">'
            f'<span style="width:{pct:.1f}%"></span></div>'
            f'<div class="meta">{pct:.0f}% dos registros · {nsub} subárea(s)</div>'
            f'</article>')
    st.markdown(f'<div class="grid">{cards}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sec">Top 10 subáreas</div>',
                unsafe_allow_html=True)
    top = (f.loc[f["Subarea"] != "", "Subarea"].value_counts().head(10)
           .rename_axis("Subárea").reset_index(name="Registros"))
    if not top.empty:
        base = alt.Chart(top).encode(
            y=alt.Y("Subárea:N", sort="-x", title=None,
                    axis=alt.Axis(labelLimit=420)),
            x=alt.X("Registros:Q", title="Registros"),
            tooltip=["Subárea", "Registros"])
        graf = (base.mark_bar(color=COR, cornerRadiusEnd=6) +
                base.mark_text(align="left", dx=4, fontSize=13,
                               color=T["txt"]).encode(text="Registros:Q"))
        graf = (graf.properties(height=max(200, 34 * len(top)),
                                background=T["card"])
                .configure_axis(labelColor=T["txt"], titleColor=T["txt"],
                                gridColor=T["bor"], domainColor=T["txt"],
                                labelFontSize=13, titleFontSize=14)
                .configure_view(strokeWidth=0))
        st.altair_chart(graf, use_container_width=True)
        with st.expander("Ver dados do gráfico em tabela"):
            st.dataframe(top, hide_index=True, use_container_width=True)

# ------------------------------------------------------------------ cartões
with aba2:
    c1, c2 = st.columns([1, 1])
    por_pag = c1.selectbox("Cartões por página", [6, 12, 24, 48], index=1)
    npag = max(1, -(-len(f) // por_pag))
    pag = c2.number_input(f"Página (de {npag})", 1, npag, 1)
    parte = f.iloc[(pag - 1) * por_pag: pag * por_pag]

    cards = ""
    for _, r in parte.iterrows():
        titulo = r["Tema_Escopo"] or r["Subarea_Termo"] or "(sem título)"
        cor = COR_AREA.get(r["Area"], COR)
        chips = "".join(f'<span class="chip" style="--c:{cor}">{esc(x)}</span>'
                        for x in (r["Area"], r["Subarea"]) if x)
        termo = (f'<p class="meta"><strong>Termo:</strong> '
                 f'{esc(r["Subarea_Termo"])}</p>'
                 if r["Subarea_Termo"] and r["Subarea_Termo"] != titulo else "")
        links = "".join(
            f'<a href="{esc(u)}" target="_blank" rel="noopener noreferrer">'
            f'{esc(urlparse(u).netloc.replace("www.", ""))}'
            f'<span class="sr"> (abre em nova aba)</span></a>'
            for u in URL_RE.findall(r["URLs"])[:4])
        cards += (f'<article class="card" style="--c:{cor}">'
                  f'<h3>{esc(titulo)}</h3>{chips}{termo}'
                  f'<p class="meta">{links or "Sem URLs de fonte"}</p>'
                  f'</article>')
    st.markdown(f'<div class="grid">{cards}</div>', unsafe_allow_html=True)

    with st.expander("🔍 Detalhe completo de um registro"):
        idx = st.selectbox(
            "Selecione um tema", f.index,
            format_func=lambda i: f"{f.at[i, 'Area']} → "
                                  f"{f.at[i, 'Tema_Escopo'] or f.at[i, 'Subarea']}")
        for col in f.columns:
            v = str(f.loc[idx, col]).strip()
            if v and col != "Qtd_URLs":
                st.markdown(f"**{mapa.get(col, col)}:** {v}")

# ------------------------------------------------------------------- tabela
with aba3:
    volta = {k: v for k, v in mapa.items()}
    vis = f.drop(columns=["Qtd_URLs"]).rename(columns=volta)
    if alto:
        vis = vis.style.set_properties(
            **{"background-color": "#000000", "color": "#FFFFFF"})
    st.dataframe(vis, use_container_width=True, hide_index=True, height=480)

# ----------------------------------------------------------------- exportar
with aba4:
    st.caption(f"Exporta os {len(f)} registros filtrados da aba "
               f"\"{aba_sel}\".")
    d1, d2 = st.columns(2)
    d1.download_button("Baixar CSV filtrado",
                       f.to_csv(index=False, sep=";").encode("utf-8-sig"),
                       file_name="metadados_filtrados.csv", mime="text/csv")
    d2.download_button("Baixar JSON filtrado",
                       f.to_json(orient="records", force_ascii=False,
                                 indent=2),
                       file_name="metadados_filtrados.json",
                       mime="application/json")

st.caption("IBICT · Projeto PD&I · Gráficos com paleta segura para daltonismo "
           "e alternativa em tabela.")