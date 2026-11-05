# -*- coding: utf-8 -*-
"""
Normaliza a coluna Área e extrai URLs de todas as colunas que contenham 'URL'.
Processa cada CSV gerado por ler_excel.py.
Arquivos vazios (apenas cabeçalho ou 0 bytes) são ignorados sem erro.
"""

from pathlib import Path
import re
import unicodedata
import pandas as pd

PASTA = Path("saida")

MAPA_AREA = {
    "saude": "Saúde",
    "assistencia social": "Assistência Social",
    "educacao": "Educação",
    "trabalho": "Trabalho",
    "seguranca": "Segurança",
    "direitos humanos": "Direitos Humanos",
    "pcd": "Pessoa com Deficiência",
    "pcd/acessibilidade": "Pessoa com Deficiência",
    "infancia e adolescencia": "Infância e Adolescência",
    "servicos/programas": "Serviços/Programas",
    "dados abertos": "Dados Abertos",
}

PADRAO_URL = re.compile(r"https?://[^\s\)\]\>,;\"']+")

ABAS = (
    "catalogo_recursos",
    "vocabulario_controlado",
    "novos_termos",
    "relacoes",
    "fontes",
    "avaliacoes",
)


def normalizar(s):
    if not s:
        return ""
    t = unicodedata.normalize("NFKD", str(s).lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def normalizar_area(v):
    k = normalizar(v)
    return MAPA_AREA.get(k, str(v).strip())


def extrair_urls(t):
    if not t:
        return []
    return PADRAO_URL.findall(str(t))


def processar(df):
    df = df.fillna("").astype(str)
    df = df.apply(lambda c: c.str.strip())

    for col in ("Área", "Area"):
        if col in df.columns:
            df[col] = df[col].apply(normalizar_area)

    cols_url = [c for c in df.columns if "URL" in c.upper()]
    if cols_url:
        df["_urls"] = df[cols_url].apply(
            lambda r: list(dict.fromkeys(
                u for v in r for u in extrair_urls(v)
            )),
            axis=1,
        )
        df["Qtd_URLs"] = df["_urls"].apply(len)
    return df


def processar_aba(base):
    arq = PASTA / f"{base}.csv"

    if not arq.exists():
        print(f"  ⚠ {base}: CSV ausente — ignorado")
        return

    if arq.stat().st_size == 0:
        print(f"  ⚠ {base}: arquivo vazio (0 bytes) — ignorado")
        return

    try:
        df = pd.read_csv(arq, sep=";", dtype=str, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        print(f"  ⚠ {base}: sem dados (apenas cabeçalho) — ignorado")
        return

    if df.empty:
        print(f"  ⚠ {base}: 0 linhas — ignorado")
        return

    df = processar(df)
    df_out = df.drop(columns=["_urls"], errors="ignore")

    df_out.to_csv(arq, index=False, sep=";", encoding="utf-8-sig")
    df_out.to_json(PASTA / f"{base}.json",
                   orient="records", force_ascii=False, indent=2)

    n_urls = int(df["Qtd_URLs"].sum()) if "Qtd_URLs" in df.columns else 0
    print(f"✔ {base}: {len(df)} linhas, {n_urls} URLs")


def main():
    for base in ABAS:
        processar_aba(base)


if __name__ == "__main__":
    main()