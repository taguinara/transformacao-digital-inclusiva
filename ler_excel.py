# -*- coding: utf-8 -*-
"""
Lê a planilha de curadoria e extrai cada aba operacional em CSV.
Descobre automaticamente o .xlsx na raiz (ignora temporários do Excel).
Abas vazias (só cabeçalho) não geram CSV e removem versões antigas.
"""

from pathlib import Path
import sys
import pandas as pd

PASTA = Path("saida")

CANDIDATOS = [
    "curadoria_metadados_vocabulario_controlado_out_2026.xlsx",
    "curadoria_digital_vocabulario_controlado_out_2026.xlsx",
    "curadoria.xlsx",
]

ABAS = {
    "Catalogo_Recursos":       "catalogo_recursos",
    "Vocabulario_Controlado":  "vocabulario_controlado",
    "Novos_Termos_Propostos":  "novos_termos",
    "Relacao_Recurso_Termo":   "relacoes",
    "Fontes_Oficiais_DF":      "fontes",
    "Avaliacao_Critica":       "avaliacoes",
    "Dicionario_Campos":       "dicionario",
    "Plano_Validacao":         "plano",
}


def achar_planilha() -> Path:
    """Retorna o caminho da planilha de entrada."""
    for nome in CANDIDATOS:
        p = Path(nome)
        if p.exists():
            return p

    encontrados = [
        f for f in Path(".").glob("*.xlsx")
        if not f.name.startswith("~$") and not f.name.startswith(".")
    ]
    if len(encontrados) == 1:
        return encontrados[0]
    if len(encontrados) > 1:
        print("⚠ Múltiplos .xlsx encontrados:")
        for i, f in enumerate(encontrados, 1):
            print(f"  {i}. {f.name}")
        print("\nInforme o nome desejado em CANDIDATOS ou remova os excedentes.")
        sys.exit(1)

    raise SystemExit(
        "Nenhum .xlsx encontrado na pasta. "
        "Coloque a planilha de curadoria na raiz do projeto."
    )


def achar_header(df_raw):
    """Retorna o índice da 1ª linha cujo campo A começa com 'id_'."""
    for i in range(min(20, len(df_raw))):
        v = df_raw.iloc[i, 0]
        if pd.notna(v) and str(v).strip().lower().startswith("id_"):
            return i
    return None


def extrair_aba(xls, aba_real):
    """Extrai uma aba como DataFrame. Retorna None se não houver cabeçalho."""
    df_raw = pd.read_excel(xls, sheet_name=aba_real, header=None)
    idx = achar_header(df_raw)
    if idx is None:
        print(f"  ⚠ {aba_real}: cabeçalho não encontrado — ignorada")
        return None

    colunas = [str(c).strip() for c in df_raw.iloc[idx]]
    df = df_raw.iloc[idx + 1:].copy()
    df.columns = colunas
    df = df.dropna(how="all").fillna("")
    df = df[df.apply(lambda r: any(str(x).strip() for x in r), axis=1)]

    if df.empty:
        return None
    return df.reset_index(drop=True)


def main():
    PASTA.mkdir(exist_ok=True)

    caminho = achar_planilha()
    print(f"✔ Planilha encontrada: {caminho.name}\n")

    xls = pd.ExcelFile(caminho)
    print(f"Abas disponíveis: {xls.sheet_names}\n")

    for aba_real, base in ABAS.items():
        if aba_real not in xls.sheet_names:
            print(f"  ⚠ {aba_real} ausente na planilha")
            continue

        df = extrair_aba(xls, aba_real)
        destino = PASTA / f"{base}.csv"

        if df is None or df.empty:
            print(f"  ⚠ {aba_real}: sem dados — CSV não gerado")
            if destino.exists():
                destino.unlink()
                print(f"     (removido CSV antigo: {destino.name})")
            continue

        df.to_csv(destino, index=False, sep=";", encoding="utf-8-sig")
        print(f"✔ {aba_real}: {len(df)} linhas → {destino.name}")


if __name__ == "__main__":
    main()