# -*- coding: utf-8 -*-
"""
Processamento dos metadados:
  - leitura do Excel
  - limpeza
  - normalização da coluna Area
  - extração de URLs da Garantia Literaria
  - exportação CSV / JSON / Excel
"""

from pathlib import Path
import json
import re
import pandas as pd

ARQUIVO_ENTRADA = "Controle_Vocabulario.xlsx"
PASTA_SAIDA = Path("saida")

COLUNAS = [
    "Area", "Subarea", "Tema_Escopo",
    "Area_Termo", "Subarea_Termo",
    "Garantia_Literaria", "Remissivas",
]

# ----------------------------------------------------------------------
# MAPA DE NORMALIZAÇÃO DA COLUNA ÁREA
# ----------------------------------------------------------------------
MAPA_AREA = {
    "saude": "Saúde",
    "assistencia social": "Assistência Social",
    "assistencia": "Assistência Social",
    "educacao": "Educação",
    "trabalho": "Trabalho",
    "seguranca": "Segurança",
    "direitos humanos": "Direitos Humanos",
    "pcd": "Pessoa com Deficiência",
    "pessoa com deficiencia": "Pessoa com Deficiência",
    "pessoas com deficiencia": "Pessoa com Deficiência",
}


def normalizar_area(valor: str) -> str:
    """Padroniza nomes da coluna Area."""
    if not valor:
        return ""
    chave = valor.strip().lower()
    return MAPA_AREA.get(chave, valor.strip())


# ----------------------------------------------------------------------
# EXTRAÇÃO DE URLs
# ----------------------------------------------------------------------
PADRAO_URL = re.compile(r"https?://[^\s\)\]\>,;\"']+")


def extrair_urls(texto: str) -> list[str]:
    """Retorna lista de URLs encontradas em um texto."""
    if not texto:
        return []
    return PADRAO_URL.findall(texto)


# ----------------------------------------------------------------------
# LEITURA E LIMPEZA
# ----------------------------------------------------------------------
def ler_excel(caminho=ARQUIVO_ENTRADA) -> pd.DataFrame:
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"'{caminho}' não encontrado.")

    df = pd.read_excel(caminho, dtype=str)
    df.columns = (df.columns.str.strip()
                            .str.replace(" ", "_")
                            .str.replace("/", "_"))
    print(f"✔ Planilha lida: {len(df)} linhas | colunas: {list(df.columns)}")
    return df


def limpar(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(how="all").fillna("")
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    # Normaliza a coluna Area
    if "Area" in df.columns:
        df["Area"] = df["Area"].apply(normalizar_area)

    # Extrai URLs da garantia literária
    if "Garantia_Literaria" in df.columns:
        df["URLs"] = df["Garantia_Literaria"].apply(
            lambda t: "; ".join(extrair_urls(t))
        )
        df["Qtd_URLs"] = df["URLs"].apply(
            lambda s: 0 if not s else len(s.split(";"))
        )

    antes = len(df)
    df = df.drop_duplicates()
    if antes != len(df):
        print(f"  ⚠ {antes - len(df)} duplicada(s) removida(s)")

    print(f"✔ Limpeza concluída: {len(df)} linhas")
    return df


def exportar(df: pd.DataFrame, pasta=PASTA_SAIDA) -> None:
    pasta = Path(pasta)
    pasta.mkdir(exist_ok=True)

    df.to_csv(pasta / "metadados_limpos.csv",
              index=False, encoding="utf-8-sig", sep=";")
    df.to_excel(pasta / "metadados_limpos.xlsx",
                index=False, engine="openpyxl")
    with open(pasta / "metadados_limpos.json", "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f,
                  ensure_ascii=False, indent=2)

    print(f"✔ Arquivos salvos em: {pasta.resolve()}")


def resumo(df: pd.DataFrame) -> None:
    print("\n--- Resumo ---")
    if "Area" in df.columns:
        print("\nLinhas por Área (normalizada):")
        print(df["Area"].value_counts().to_string())
    if "Qtd_URLs" in df.columns:
        print(f"\nTotal de URLs extraídas: {df['Qtd_URLs'].sum()}")
        print(f"Linhas com pelo menos 1 URL: {(df['Qtd_URLs'] > 0).sum()}")


if __name__ == "__main__":
    df = limpar(ler_excel())
    exportar(df)
    resumo(df)