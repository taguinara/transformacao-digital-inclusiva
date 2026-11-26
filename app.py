# -*- coding: utf-8 -*-
"""
Hub-i3 · Dashboard do Glossário de Políticas Públicas (IBICT · PD&I)
Lê a aba que contém a coluna "Termo controlado preferido" (Glossário).
"""

import html
import io
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

AQUI = Path(__file__).parent
XLSX_PADRAO = "curadoria_metadados_vocabulario_controlado_set_nov_2026.xlsx"  # em data/
URL_RE = re.compile(r"https?://[^\s;,|<>\"')\]]+")
TOPO = "(Termo de topo)"

# coluna interna -> nome na planilha (comparação sem acento/símbolo)
COLS = {
    "id": "ID_termo",
    "termo": "Termo controlado preferido",
    "area": "Área temática",
    "tg": "Termo Geral (TG) / Subárea",
    "publico": "Público-alvo (Faceta)",
    "definicao": "Definição",
    "sinonimos": "Sinônimos, remissivas e termos relacionados",
    "url_termo": "URL da fonte terminológica",
    "fonte_df": "Fonte oficial do DF / evidência local",
    "url_df": "URL oficial do DF",
    "status": "Status do termo",
    "resp": "Responsável pela decisão",
    "data": "Data de revisão",
    "obs": "Observações / lacunas",
}

# ---------------------------------------------------------------- paleta Hub-i3
AZUL, ROXO, BRANCO = "#003B8E", "#7B2CBF", "#FFFFFF"
DIA = {"--bg": BRANCO, "--surface": "#F3F6FC", "--side": AZUL, "--card": BRANCO,
       "--txt": "#0F1B3D", "--mut": "#44506B", "--bor": "#6F82B0",
       "--soft": "#D5DDF0", "--a1": AZUL, "--a2": ROXO, "--link": AZUL,
       "--tint1": "#E6EDFA", "--tint2": "#F1E7FB", "--onacc": BRANCO}
NOITE = {"--bg": "#0A1226", "--surface": "#0F1A36", "--side": "#0B2A66", "--card": "#131F40",
         "--txt": "#F2F5FF", "--mut": "#BAC5E2", "--bor": "#7088C8",
         "--soft": "#2A3A68", "--a1": "#8AB4FF", "--a2": "#C79BF2",
         "--link": "#9DC1FF", "--tint1": "#1B2B57", "--tint2": "#2C1F4D",
         "--onacc": "#0A1226"}

st.set_page_config(page_title="Hub-i3 | Glossário", page_icon="📘",
                   layout="wide", initial_sidebar_state="expanded")
_LANG = "<script>window.parent.document.documentElement.lang='pt-BR';</script>"
try:  # versões novas do Streamlit usam st.iframe; as antigas, components.html
    st.iframe(_LANG, height=1)
except Exception:
    components.html(_LANG, height=0)


# ------------------------------------------------------------------ utilitários
def norm(s):
    t = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def chave(s):
    return re.sub(r"[^a-z0-9]", "", norm(s))


def esc(x):
    return html.escape(str(x), quote=True).replace("$", "&#36;")


def partes(v):
    return [p.strip() for p in str(v).split(";") if p.strip()]


def dominio(u):
    return urlparse(u).netloc.replace("www.", "") or u


def links_html(*celulas, maximo=4):
    vistos, out = set(), []
    for c in celulas:
        for u in URL_RE.findall(str(c)):
            if u not in vistos and len(out) < maximo:
                vistos.add(u)
                out.append(
                    f'<a href="{esc(u)}" target="_blank" '
                    f'rel="noopener noreferrer">{esc(dominio(u))}'
                    f'<span class="sr"> (abre em nova aba)</span></a>')
    return "".join(out)


def achar_xlsx():
    """Procura a planilha em data/, na raiz e em saida/ (nessa ordem)."""
    pastas = [AQUI / "data", AQUI, AQUI / "saida"]
    for pasta in pastas:
        pref = pasta / XLSX_PADRAO
        if pref.exists():
            return pref
    for pasta in pastas:
        cand = [p for p in sorted(pasta.glob("*.xlsx"))
                if not p.name.startswith("~$")]
        if cand:
            return cand[0]
    return None


def montar_glossario(brutas):
    """Localiza a aba do glossário em {aba: DataFrame bruto} e devolve
    (título, descrição, DataFrame)."""
    alvo = chave(COLS["termo"])
    for nome, b in brutas.items():
        b = b.fillna("").astype(str).apply(lambda s: s.str.strip())
        for h in range(min(15, len(b))):
            # exige várias colunas do glossário (evita abas de dicionário)
            achadas = {chave(v) for v in b.iloc[h]} & \
                {chave(o) for o in COLS.values()}
            if alvo in achadas and len(achadas) >= 5:
                cab = list(b.iloc[h])
                corpo = b.iloc[h + 1:].reset_index(drop=True)
                corpo.columns = cab
                renome = {}
                for interna, original in COLS.items():
                    for c in cab:
                        if chave(c) == chave(original):
                            renome[c] = interna
                            break
                corpo = corpo.rename(columns=renome)
                for k in COLS:
                    if k not in corpo.columns:
                        corpo[k] = ""
                corpo = corpo[list(COLS)]
                corpo = corpo[corpo["termo"] != ""].reset_index(drop=True)
                titulo = b.iloc[0, 0] if h > 0 else nome
                desc = b.iloc[1, 0] if h > 1 else ""
                dt = pd.to_datetime(corpo["data"], errors="coerce")
                corpo["data"] = [d.strftime("%d/%m/%Y") if pd.notna(d) else o
                                 for d, o in zip(dt, corpo["data"])]
                corpo["publicos"] = corpo["publico"].map(partes)
                corpo["qtd_urls"] = (corpo["url_termo"] + " " +
                                     corpo["url_df"]).map(
                    lambda v: len(set(URL_RE.findall(v))))
                return titulo, desc, corpo
    return None, None, None


@st.cache_data(show_spinner="Lendo o Excel…")
def ler_glossario(conteudo: bytes):
    brutas = pd.read_excel(io.BytesIO(conteudo), sheet_name=None,
                           header=None, dtype=str)
    return montar_glossario(brutas)


def gsheets_configurado():
    """True se há [connections.gsheets] nos secrets e o pacote está instalado."""
    try:
        from streamlit_gsheets import GSheetsConnection  # noqa: F401
        return "gsheets" in st.secrets.get("connections", {})
    except Exception:
        return False


@st.cache_data(ttl=600, show_spinner="Lendo o Google Sheets…")
def ler_gsheets():
    """Lê o glossário direto do Google Sheets (atualiza a cada 10 min)."""
    from streamlit_gsheets import GSheetsConnection
    # Cria a conexão
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Lê os dados do glossário (header=None: o título fica acima do cabeçalho)
    cfg = st.secrets.get("connections", {}).get("gsheets", {})
    nome = (st.secrets.get("aba_glossario") or cfg.get("aba_glossario")
            or cfg.get("worksheet") or "Glossário 2026")
    for aba in (nome, "Glossário 2026", "Glossario 2026", None):
        try:
            kw = {"worksheet": aba} if aba else {}
            df_bruto = conn.read(header=None, **kw)
        except Exception:
            continue
        res = montar_glossario({str(aba): df_bruto.astype(object)
                                .where(df_bruto.notna(), "")})
        if res[2] is not None:
            return res
    return None, None, None


@st.cache_data(show_spinner="Lendo o CSV…")
def ler_csv(conteudo: bytes):
    d = pd.read_csv(io.BytesIO(conteudo), sep=";", dtype=str,
                    encoding="utf-8-sig").fillna("")
    inv = {chave(v): k for k, v in COLS.items()}
    d = d.rename(columns={c: inv[chave(c)] for c in d.columns
                          if chave(c) in inv})
    if "termo" not in d.columns:
        return None, None, None
    for k in COLS:
        if k not in d.columns:
            d[k] = ""
    d["publicos"] = d["publico"].map(partes)
    d["qtd_urls"] = (d["url_termo"] + " " + d["url_df"]).map(
        lambda v: len(set(URL_RE.findall(v))))
    return "Glossário", "", d


# ---------------------------------------------------------------------- dados
fonte, resultado = "", (None, None, None)
if gsheets_configurado():
    try:
        resultado, fonte = ler_gsheets(), "Google Sheets"
    except Exception as e:
        st.sidebar.warning(f"Não foi possível ler o Google Sheets: {e}")
xlsx = achar_xlsx() if resultado[2] is None else None
if resultado[2] is not None:
    pass
elif xlsx is not None:
    resultado, fonte = ler_glossario(xlsx.read_bytes()), xlsx.name
else:
    st.sidebar.info("Nenhum arquivo encontrado no repositório. "
                    "Envie a planilha (.xlsx) ou o CSV abaixo.")
    up = st.sidebar.file_uploader("Planilha do glossário",
                                  type=["xlsx", "csv"])
    if up is None:
        st.title("📘 Hub-i3")
        st.info("**Os dados do glossário ainda não foram carregados.**\n\n"
                "Envie a planilha `.xlsx` na barra lateral.\n\n"
                f"_Administração: para abrir já com os dados, inclua "
                f"`{XLSX_PADRAO}` na pasta `data/` do repositório._")
        st.stop()
    resultado = (ler_glossario(up.getvalue())
                 if up.name.lower().endswith("xlsx")
                 else ler_csv(up.getvalue()))
    fonte = up.name

TITULO, DESCRICAO, df = resultado
if df is None or df.empty:
    st.error("Não encontrei a aba do glossário (coluna "
             "“Termo controlado preferido”) na planilha enviada.")
    st.stop()

# ------------------------------------------------------------- barra lateral
st.sidebar.markdown("## 📘 Hub-i3")
with st.sidebar.expander("♿ Aparência e acessibilidade", expanded=False):
    modo = st.radio("Tema de cores",
                    ["Automático (dia/noite)", "Dia", "Noite"],
                    help="Automático segue a configuração do dispositivo.")
    fs = st.select_slider("Tamanho do texto", [90, 100, 115, 130, 150],
                          value=100, format_func=lambda v: f"{v}%")

st.sidebar.header("🔎 Filtros")


def limpar_filtros():
    for k in ("f_area", "f_tg", "f_pub"):
        st.session_state[k] = []
    st.session_state["f_busca"] = ""
    st.session_state["f_obs"] = False


areas = sorted(a for a in df["area"].unique() if a)
area_sel = st.sidebar.multiselect("Área temática", areas, key="f_area",
                                  placeholder="Todas as áreas")
base_tg = df[df["area"].isin(area_sel)] if area_sel else df
tgs = sorted(t for t in base_tg["tg"].unique() if t)
st.session_state["f_tg"] = [x for x in st.session_state.get("f_tg", [])
                            if x in tgs]
tg_sel = st.sidebar.multiselect("Subárea (Termo Geral)", tgs, key="f_tg",
                                placeholder="Todas as subáreas")
pubs = sorted({p for l in df["publicos"] for p in l})
pub_sel = st.sidebar.multiselect("Público-alvo (faceta)", pubs, key="f_pub",
                                 placeholder="Todos os públicos")
busca = st.sidebar.text_input("Buscar no glossário", key="f_busca",
                              placeholder="termo, definição, sinônimo…")
so_obs = st.sidebar.checkbox("Somente termos com observações/lacunas",
                             key="f_obs")
st.sidebar.button("Limpar filtros", on_click=limpar_filtros)

f = df.copy()
if area_sel:
    f = f[f["area"].isin(area_sel)]
if tg_sel:
    f = f[f["tg"].isin(tg_sel)]
if pub_sel:
    alvo_p = set(pub_sel)
    f = f[f["publicos"].map(lambda l: bool(alvo_p & set(l)))]
if so_obs:
    f = f[f["obs"] != ""]
if busca:
    alvo = norm(busca)
    campos = ["termo", "definicao", "sinonimos", "area", "tg", "publico"]
    f = f[f[campos].apply(lambda r: alvo in norm(" ".join(r)), axis=1)]
f = f.sort_values("termo", key=lambda s: s.map(norm)).reset_index(drop=True)

st.sidebar.caption(f"**{len(f)}** de {len(df)} termo(s) exibido(s)")
st.sidebar.caption(f"Fonte: {fonte}")

# ------------------------------------------------------------------------ CSS
def variaveis(d):
    return ";".join(f"{k}:{v}" for k, v in d.items())


if modo.startswith("Auto"):
    raiz = (":root{" + variaveis(DIA) + ";color-scheme:light dark}"
            "@media (prefers-color-scheme: dark){:root{" +
            variaveis(NOITE) + "}}")
elif modo == "Dia":
    raiz = ":root{" + variaveis(DIA) + ";color-scheme:light}"
else:
    raiz = ":root{" + variaveis(NOITE) + ";color-scheme:dark}"

CSS = """
<style>
%%RAIZ%%
html{font-size:%%FS%%%;}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stHeader"]{
  background:var(--bg)!important;color:var(--txt);}
.block-container{padding-top:1.6rem;max-width:1280px;}
[data-testid="stSidebar"],[data-testid="stSidebar"]>div:first-child{
  background:var(--side)!important;}
[data-testid="stSidebar"]{border-right:2px solid var(--bor);}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,[data-testid="stSidebar"] span,
[data-testid="stWidgetLabel"] *,[data-testid="stCaptionContainer"] *,
[data-testid="stRadio"] *,[data-testid="stCheckbox"] *,
[data-testid="stExpander"] summary *{color:var(--txt)!important;}
[data-testid="stCaptionContainer"] *{color:var(--mut)!important;}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,[data-testid="stSidebar"] h1 *,
[data-testid="stSidebar"] h2 *,[data-testid="stSidebar"] h3 *,
[data-testid="stSidebar"] label,[data-testid="stSidebar"] label *,
[data-testid="stSidebar"] [data-testid="stSlider"] *,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] *,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *,
[data-testid="stSidebar"] [data-testid="stCheckbox"] *,
[data-testid="stSidebar"] [data-testid="stRadio"] *,
[data-testid="stSidebar"] [data-testid="stExpander"] summary *,
[data-testid="stSidebar"] [data-testid="stExpander"] label *{color:#FFFFFF!important;}
[data-testid="stSidebar"] [data-testid="stExpander"]{background:transparent;
  border-color:#FFFFFF;}
[data-testid="stSidebar"] [data-testid="stExpander"] svg{fill:#FFFFFF!important;}
[data-testid="stSidebar"] .stButton button{background:#FFFFFF!important;
  border-color:#FFFFFF!important;}
[data-testid="stSidebar"] .stButton button *{color:#003B8E!important;}
[data-testid="stExpander"]{border:1.5px solid var(--bor);border-radius:10px;
  background:var(--card);}
[data-baseweb="input"],[data-baseweb="base-input"],[data-baseweb="select"],
[data-baseweb="select"] *,input,textarea{background:var(--card)!important;
  color:var(--txt)!important;}
[data-baseweb="input"],[data-baseweb="select"]>div{
  border:1.5px solid var(--bor)!important;border-radius:8px!important;}
[data-testid="stSelectbox"] div,[data-testid="stNumberInput"] div,
[data-testid="stMultiSelect"] div,[data-testid="stTextInput"] div,
[data-testid="stMultiSelect"] [data-baseweb="select"] div{
  background-color:var(--card)!important;}
.stApp [data-testid="stWidgetLabel"],.stApp [data-testid="stWidgetLabel"] *{
  background:transparent!important;background-color:transparent!important;}
[data-testid="stMultiSelect"]>div>div,[data-testid="stSelectbox"]>div>div,
[data-testid="stTextInput"]>div>div,[data-testid="stNumberInput"]>div>div{
  border:1.5px solid var(--bor)!important;border-radius:8px!important;}
[data-testid="stMultiSelect"] input,[data-testid="stSelectbox"] input,
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,
[data-testid="stMultiSelect"] [class*="placeholder"],
[data-testid="stSelectbox"] div[value]{color:var(--txt)!important;}
[data-testid="stMultiSelect"] svg,[data-testid="stSelectbox"] svg{
  fill:var(--txt)!important;color:var(--txt)!important;}
[data-testid="stMultiSelect"] [data-tag],[data-testid="stMultiSelect"] [data-tag] *{
  background-color:var(--a1)!important;color:var(--onacc)!important;}
[data-testid="stMultiSelect"] input:focus-visible,
[data-testid="stTextInput"] input:focus-visible{outline:none!important;}
[data-testid="stMultiSelect"]>div>div:focus-within,
[data-testid="stTextInput"]>div>div:focus-within{
  outline:3px solid var(--a2)!important;outline-offset:2px;}
[data-testid="stMultiSelect"] [data-baseweb="tag"],
[data-testid="stMultiSelect"] [data-baseweb="tag"] *{
  background-color:var(--a1)!important;color:var(--onacc)!important;}
[data-testid="stMultiSelect"] [data-baseweb="tag"] svg{
  fill:var(--onacc)!important;color:var(--onacc)!important;}
[data-testid="stNumberInput"] button{background:var(--surface)!important;}
[data-testid="stNumberInput"] button svg{fill:var(--txt)!important;}
span[data-baseweb="tag"],span[data-baseweb="tag"] *{
  background:var(--a1)!important;color:var(--onacc)!important;}
[data-baseweb="select"] svg,[data-testid="stSidebarCollapseButton"] svg,
[data-testid="stExpander"] svg{fill:var(--txt)!important;color:var(--txt)!important;}
[data-baseweb="popover"] *,[role="listbox"],[role="option"]{
  background:var(--card)!important;color:var(--txt)!important;}
[role="option"]:hover,[aria-selected="true"][role="option"]{
  background:var(--tint1)!important;}
span[data-baseweb="tag"]{background:var(--a1)!important;color:var(--onacc)!important;}
span[data-baseweb="tag"] *{color:var(--onacc)!important;}
.stButton button,.stDownloadButton button{background:var(--a1)!important;
  border:2px solid var(--a1)!important;border-radius:10px;font-weight:700;}
.stButton button *,.stDownloadButton button *{color:var(--onacc)!important;}
.stTabs [data-baseweb="tab-list"]{border-bottom:2px solid var(--bor);gap:.4rem;}
.stTabs [data-baseweb="tab"] p{color:var(--txt)!important;font-weight:600;}
.stTabs [aria-selected="true"] p{color:var(--a1)!important;font-weight:800;}
.stTabs [data-baseweb="tab-highlight"]{background:var(--a2)!important;height:4px;}
.stTabs [aria-selected="true"]{border-bottom:4px solid var(--a2)!important;}
:focus-visible{outline:3px solid var(--a2)!important;outline-offset:2px;}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);}
.stApp .hero{background:linear-gradient(120deg,#003B8E 0%,#7B2CBF 100%);
  border:2px solid var(--bor);border-radius:20px;padding:1.9rem 2.2rem;
  margin-bottom:1.2rem;position:relative;overflow:hidden;}
.hero:after{content:"";position:absolute;right:-70px;top:-70px;width:260px;
  height:260px;border-radius:50%;background:rgba(255,255,255,.12);}
.stApp .hero *{color:#FFFFFF!important;}
.hero .eyebrow{letter-spacing:.16em;text-transform:uppercase;font-size:.8rem;
  font-weight:700;margin:0 0 .3rem;}
.hero h1{font-size:2.6rem;line-height:1.1;margin:0 0 .4rem;padding:0;}
.hero p.sub{margin:0;font-size:1.1rem;max-width:68ch;}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(125px,1fr));
  gap:.8rem;margin:0 0 1.3rem;}
.kpi{background:var(--card);border:2px solid var(--bor);border-radius:14px;
  padding:.8rem 1.1rem;border-top:7px solid var(--c);}
.kpi .n{font-size:2.1rem;font-weight:800;color:var(--txt);line-height:1.1;}
.kpi .l{font-size:.9rem;color:var(--mut);font-weight:600;}
.panel{background:var(--card);border:2px solid var(--bor);border-radius:14px;
  padding:1rem 1.2rem;margin-bottom:1rem;}
.panel h3{font-size:1.1rem;margin:0 0 .6rem;padding:0;color:var(--txt);}
.panel p.nota{font-size:.85rem;color:var(--mut);margin:.5rem 0 0;}
.brow{display:grid;grid-template-columns:minmax(110px,40%) 1fr 4.6rem;gap:.6rem;
  align-items:center;padding:.35rem 0;border-bottom:1px solid var(--soft);}
.brow:last-child{border-bottom:0;}
.blab{font-size:.92rem;color:var(--txt);font-weight:600;overflow-wrap:anywhere;}
.btrk{height:18px;border:1.5px solid var(--bor);border-radius:6px;
  background:var(--surface);overflow:hidden;display:block;}
.bfill{display:block;height:100%;}
.bval{font-size:.9rem;font-weight:800;color:var(--txt);text-align:right;}
.sec{font-size:1.25rem;font-weight:800;color:var(--txt);margin:.4rem 0 .6rem;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));
  gap:.9rem;}
.card{background:var(--card);border:2px solid var(--bor);
  border-left:8px solid var(--c);border-radius:14px;padding:1rem 1.15rem;
  color:var(--txt);}
.card h3{font-size:1.15rem;margin:.1rem 0 .4rem;color:var(--txt);padding:0;}
.card .def{font-size:.95rem;margin:.5rem 0;color:var(--txt);line-height:1.5;}
.card .meta{font-size:.88rem;color:var(--mut);margin:.25rem 0;}
.card a,.twrap a{color:var(--link);font-weight:600;text-decoration:underline;
  margin-right:.7rem;font-size:.9rem;}
.chip{display:inline-block;border:1.5px solid var(--c);border-radius:99px;
  padding:.05rem .65rem;font-size:.8rem;font-weight:700;margin:.1rem .3rem
  .1rem 0;color:var(--txt);background:var(--tint1);}
.chip.id{background:var(--tint2);}
details{border-top:1.5px solid var(--soft);margin-top:.6rem;padding-top:.5rem;}
summary{cursor:pointer;font-weight:700;color:var(--link);font-size:.92rem;}
details dl{margin:.5rem 0 0;}
details dt{font-weight:700;font-size:.82rem;color:var(--mut);margin-top:.5rem;}
details dd{margin:.1rem 0 0;font-size:.92rem;color:var(--txt);}
.twrap{overflow:auto;border:2px solid var(--bor);border-radius:12px;
  max-height:560px;background:var(--card);}
.twrap table{border-collapse:collapse;width:100%;font-size:.88rem;}
.twrap th{position:sticky;top:0;background:var(--a1);color:var(--onacc);
  text-align:left;padding:.55rem .7rem;border:1px solid var(--bor);z-index:1;}
.twrap td{padding:.5rem .7rem;border:1px solid var(--bor);vertical-align:top;
  color:var(--txt);min-width:90px;}
.twrap tr:nth-child(even) td{background:var(--surface);}
.twrap td.larga{min-width:320px;}
@media (prefers-reduced-motion:no-preference){
  .card{transition:transform .15s,box-shadow .15s;}
  .card:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(0,0,0,.18);}
}
</style>
"""
st.markdown(CSS.replace("%%RAIZ%%", raiz).replace("%%FS%%", str(fs)),
            unsafe_allow_html=True)

# ----------------------------------------------------------------- componentes
def barras(contagem, cor, total=None):
    """Gráfico de barras em HTML (adapta-se ao tema; valores em texto)."""
    if contagem.empty:
        return '<p class="nota">Sem dados para os filtros atuais.</p>'
    mx = contagem.max()
    linhas = ""
    for nome, n in contagem.items():
        pct = f" · {100 * n / total:.0f}%" if total else ""
        linhas += (f'<div class="brow"><span class="blab">{esc(nome)}</span>'
                   f'<span class="btrk" aria-hidden="true"><span class="bfill" '
                   f'style="width:{100 * n / mx:.1f}%;background:var({cor})">'
                   f'</span></span><span class="bval">{n}{pct}</span></div>')
    return linhas


def tabela_html(cabecalhos, linhas, larga=()):
    th = "".join(f"<th scope='col'>{esc(c)}</th>" for c in cabecalhos)
    corpo = ""
    for r in linhas:
        corpo += "<tr>" + "".join(
            f"<td class='{'larga' if i in larga else ''}'>{c}</td>"
            for i, c in enumerate(r)) + "</tr>"
    return (f'<div class="twrap" tabindex="0" role="region" '
            f'aria-label="Tabela de dados">'
            f'<table><thead><tr>{th}</tr></thead><tbody>{corpo}</tbody>'
            f'</table></div>')


# ------------------------------------------------------------------------ hero
TITULO_LIMPO = re.sub(r"\s*[–-]\s*Hub-i3\s*$", "", TITULO)
sub = esc(DESCRICAO) if DESCRICAO else "Vocabulário controlado de inclusão social, acessibilidade e garantia de direitos."
n_areas = f["area"].replace("", pd.NA).nunique()
n_tg = f.loc[~f["tg"].isin(["", TOPO]), "tg"].nunique()
n_pub = len({p for l in f["publicos"] for p in l})
n_val = int((f["status"].map(norm) == "validado").sum())
n_obs = int((f["obs"] != "").sum())
revisao = f.loc[f["data"] != "", "data"]
kpis = [("Termos", len(f)), ("Áreas temáticas", n_areas),
        ("Subáreas (TG)", n_tg), ("Públicos-alvo", n_pub),
        ("Termos validados", n_val), ("Com observações/lacunas", n_obs)]
kpi_html = "".join(
    f'<div class="kpi" style="--c:var({"--a1" if i % 2 == 0 else "--a2"})">'
    f'<div class="n">{v}</div><div class="l">{esc(l)}</div></div>'
    for i, (l, v) in enumerate(kpis))
st.markdown(
    f'<header class="hero"><p class="eyebrow">IBICT · PD&amp;I</p>'
    f'<h1>Hub-i3</h1><p class="sub"><strong>{esc(TITULO_LIMPO)}</strong><br>{sub}</p>'
    f'</header><section class="kpis" aria-label="Indicadores gerais">'
    f'{kpi_html}</section>', unsafe_allow_html=True)

if f.empty:
    st.warning("Nenhum termo encontrado com os filtros atuais. "
               "Use “Limpar filtros” na barra lateral.")
    st.stop()

aba1, aba2, aba3, aba4 = st.tabs(
    ["🧭 Painel", "📖 Glossário", "📋 Tabela", "⬇️ Exportar"])

# ---------------------------------------------------------------------- painel
with aba1:
    total = len(f)
    c1, c2 = st.columns(2)
    por_area = f["area"].replace("", "(sem área)").value_counts()
    c1.markdown(
        f'<section class="panel" aria-label="Termos por área temática">'
        f'<h3>Termos por área temática</h3>{barras(por_area, "--a1", total)}'
        f'</section>', unsafe_allow_html=True)
    por_tg = f.loc[~f["tg"].isin(["", TOPO]), "tg"].value_counts().head(10)
    topo = int((f["tg"] == TOPO).sum())
    nota = (f'<p class="nota">Não inclui {topo} termo(s) de topo da '
            f'hierarquia.</p>' if topo else "")
    c2.markdown(
        f'<section class="panel" aria-label="Top 10 subáreas">'
        f'<h3>Top 10 subáreas (Termo Geral)</h3>{barras(por_tg, "--a2", total)}'
        f'{nota}</section>', unsafe_allow_html=True)

    c3, c4 = st.columns(2)
    por_pub = pd.Series([p for l in f["publicos"] for p in l]
                        ).value_counts().head(10)
    c3.markdown(
        f'<section class="panel" aria-label="Top 10 públicos-alvo">'
        f'<h3>Top 10 públicos-alvo (faceta)</h3>{barras(por_pub, "--a2", total)}'
        f'<p class="nota">Um termo pode atender a mais de um público.</p>'
        f'</section>', unsafe_allow_html=True)
    com_obs = int((f["obs"] != "").sum())
    c4.markdown(
        f'<section class="panel" aria-label="Situação da curadoria">'
        f'<h3>Situação da curadoria</h3>'
        f'{barras(f["status"].replace("", "(sem status)").value_counts(), "--a1", total)}'
        f'<p class="nota">{com_obs} termo(s) com observações/lacunas · '
        f'última revisão: {esc(revisao.iloc[-1]) if len(revisao) else "—"}.</p>'
        f'</section>', unsafe_allow_html=True)

    with st.expander("Ver quantitativo por área e subárea em tabela"):
        q = (f.assign(area=f["area"].replace("", "(sem área)"),
                      tg=f["tg"].replace("", "(sem subárea)"))
             .groupby(["area", "tg"]).size().reset_index(name="n")
             .sort_values(["area", "n"], ascending=[True, False]))
        st.markdown(tabela_html(
            ["Área temática", "Subárea (TG)", "Termos"],
            [[esc(r.area), esc(r.tg), str(r.n)] for r in q.itertuples()]),
            unsafe_allow_html=True)

# -------------------------------------------------------------------- glossário
with aba2:
    k1, k2 = st.columns(2)
    por_pag = k1.selectbox("Termos por página", [6, 12, 24, 48], index=1,
                           key="pp_cards")
    npag = max(1, -(-len(f) // por_pag))
    pag = k2.number_input(f"Página (de {npag})", 1, npag, 1, key="pg_cards")
    parte = f.iloc[(pag - 1) * por_pag: pag * por_pag]
    cor_de = {a: ("--a1" if i % 2 == 0 else "--a2")
              for i, a in enumerate(areas)}

    cards = ""
    for _, r in parte.iterrows():
        cv = cor_de.get(r["area"], "--a1")
        chips = (f'<span class="chip id" style="--c:var({cv})">{esc(r["id"])}</span>'
                 + "".join(f'<span class="chip" style="--c:var({cv})">{esc(x)}</span>'
                           for x in (r["area"], r["tg"]) if x))
        detalhes = ""
        for rot_, chave_ in [("Sinônimos, remissivas e relacionados", "sinonimos"),
                             ("Público-alvo", "publico"),
                             ("Fonte oficial do DF / evidência local", "fonte_df"),
                             ("Observações / lacunas", "obs"),
                             ("Revisão", "data")]:
            if r[chave_]:
                detalhes += f'<dt>{rot_}</dt><dd>{esc(r[chave_])}</dd>'
        lk = links_html(r["url_termo"], r["url_df"])
        if lk:
            detalhes += f'<dt>Fontes</dt><dd>{lk}</dd>'
        cards += (
            f'<article class="card" style="--c:var({cv})">{chips}'
            f'<h3>{esc(r["termo"])}</h3>'
            f'<p class="def">{esc(r["definicao"]) or "Sem definição registrada."}</p>'
            f'<details><summary>Mais informações</summary>'
            f'<dl>{detalhes}</dl></details></article>')
    st.markdown(f'<div class="grid">{cards}</div>', unsafe_allow_html=True)
    st.caption(f"Exibindo {len(parte)} de {len(f)} termos, em ordem alfabética.")

# ---------------------------------------------------------------------- tabela
with aba3:
    t1, t2 = st.columns(2)
    por_pt = t1.selectbox("Linhas por página", [10, 25, 50, 100], index=1,
                          key="pp_tab")
    npt = max(1, -(-len(f) // por_pt))
    pgt = t2.number_input(f"Página (de {npt})", 1, npt, 1, key="pg_tab")
    p = f.iloc[(pgt - 1) * por_pt: pgt * por_pt]
    linhas = [[esc(r.id), f"<strong>{esc(r.termo)}</strong>", esc(r.area),
               esc(r.tg), esc(r.publico), esc(r.definicao), esc(r.sinonimos),
               links_html(r.url_termo, r.url_df, maximo=3) or "—",
               esc(r.status), esc(r.data)] for r in p.itertuples()]
    st.markdown(tabela_html(
        ["ID", "Termo preferido", "Área temática", "Subárea (TG)",
         "Público-alvo", "Definição", "Sinônimos/remissivas", "Fontes",
         "Status", "Revisão"], linhas, larga=(5,)), unsafe_allow_html=True)
    st.caption(f"Linhas {(pgt - 1) * por_pt + 1}–"
               f"{min(pgt * por_pt, len(f))} de {len(f)}.")

# -------------------------------------------------------------------- exportar
with aba4:
    st.caption(f"Exporta os {len(f)} termo(s) exibidos com os filtros atuais.")
    out = f.drop(columns=["publicos", "qtd_urls"]).rename(columns=COLS)
    buf = io.BytesIO()
    out.to_excel(buf, index=False, sheet_name="Glossário Hub-i3")
    d1, d2, d3 = st.columns(3)
    d1.download_button("Baixar CSV", out.to_csv(index=False, sep=";")
                       .encode("utf-8-sig"), file_name="hub-i3_glossario.csv",
                       mime="text/csv")
    d2.download_button("Baixar Excel", buf.getvalue(),
                       file_name="hub-i3_glossario.xlsx",
                       mime="application/vnd.openxmlformats-officedocument"
                            ".spreadsheetml.sheet")
    d3.download_button("Baixar JSON",
                       out.to_json(orient="records", force_ascii=False,
                                   indent=2),
                       file_name="hub-i3_glossario.json",
                       mime="application/json")

st.caption("Hub-i3 · IBICT · Projeto PD&I")