# -*- coding: utf-8 -*-
"""
Exporta os metadados para Dublin Core (XML).
Referência: https://www.dublincore.org/specifications/dublin-core/dces/
"""

from pathlib import Path
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import pandas as pd


NAMESPACE = "http://purl.org/dc/elements/1.1/"
ET.register_namespace("dc", NAMESPACE)


def _sub(parent, tag, texto):
    """Cria subelemento dc:<tag> se o texto não estiver vazio."""
    if texto and str(texto).strip():
        el = ET.SubElement(parent, f"{{{NAMESPACE}}}{tag}")
        el.text = str(texto).strip()


def linha_para_dc(linha: pd.Series) -> ET.Element:
    """Converte uma linha do DataFrame em um registro Dublin Core."""
    rec = ET.Element("record")

    # Título = Tema/Escopo
    _sub(rec, "title", linha.get("Tema_Escopo"))

    # Assunto = Área, Subárea e termo controlado (múltiplos <dc:subject>)
    _sub(rec, "subject", linha.get("Area"))
    _sub(rec, "subject", linha.get("Subarea"))
    _sub(rec, "subject", linha.get("Subarea_Termo"))

    # Descrição = Garantia literária + remissivas
    descricao = " | ".join(filter(None, [
        linha.get("Garantia_Literaria", ""),
        linha.get("Remissivas", ""),
    ]))
    _sub(rec, "description", descricao)

    # Fonte = URLs extraídas
    for url in str(linha.get("URLs", "")).split(";"):
        _sub(rec, "source", url.strip())

    # Cobertura = Área / Subárea (contexto temático)
    cobertura = " / ".join(filter(None, [
        linha.get("Area", ""), linha.get("Subarea", ""),
    ]))
    _sub(rec, "coverage", cobertura)

    # Tipo, formato, idioma fixos para o projeto
    _sub(rec, "type", "Termo controlado")
    _sub(rec, "format", "text/html")
    _sub(rec, "language", "pt-BR")

    # Direitos = licença padrão do projeto
    _sub(rec, "rights", "CC BY 4.0")

    return rec


def exportar_dublin_core(df: pd.DataFrame,
                         caminho: str = "saida/dublin_core.xml") -> None:
    raiz = ET.Element("dublinCore")

    for _, linha in df.iterrows():
        raiz.append(linha_para_dc(linha))

    xml_str = ET.tostring(raiz, encoding="unicode")
    bonito = minidom.parseString(xml_str).toprettyxml(indent="  ")

    # Remove linhas em branco extras do pretty print
    bonito = "\n".join(l for l in bonito.splitlines() if l.strip())

    Path(caminho).parent.mkdir(exist_ok=True)
    Path(caminho).write_text(bonito, encoding="utf-8")
    print(f"✔ Dublin Core exportado:{caminho} "
          f"({len(df)} registros)")


if __name__ == "__main__":
    df = pd.read_csv("saida/metadados_limpos.csv", sep=";", dtype=str).fillna("")
    exportar_dublin_core(df)