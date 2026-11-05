# -*- coding: utf-8 -*-
"""
Gera dois arquivos Dublin Core + PREMIS:
  - dublin_core_recursos.xml
  - dublin_core_vocabulario.xml
"""

from pathlib import Path
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import pandas as pd

from preservacao import info_premis, PREMIS_NS

PASTA = Path("saida")
ARQUIVO_MESTRE = Path("curadoria_metadados_vocabulario_controlado_out_2026.xlsx")
NS = "http://purl.org/dc/elements/1.1/"
ET.register_namespace("dc", NS)
ET.register_namespace("premis", PREMIS_NS)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _add(parent, ns, tag, txt):
    if txt is not None and str(txt).strip():
        el = ET.SubElement(parent, f"{{{ns}}}{tag}")
        el.text = str(txt)


def _sub(parent, tag, txt):
    _add(parent, NS, tag, txt)


def _add_premis(rec, identificador: str):
    """Adiciona bloco PREMIS ao registro."""
    info = info_premis(ARQUIVO_MESTRE, identificador=identificador)
    if not info:
        return
    obj = ET.SubElement(rec, f"{{{PREMIS_NS}}}object")
    _add(obj, PREMIS_NS, "objectIdentifier", info["object_identifier"])
    _add(obj, PREMIS_NS, "objectSize", info["object_size"])
    _add(obj, PREMIS_NS, "objectFormat", info["object_format"])
    _add(obj, PREMIS_NS, "objectChecksum", info["object_checksum"])
    _add(obj, PREMIS_NS, "objectChecksumAlgorithm", info["object_checksum_alg"])

    evt = ET.SubElement(rec, f"{{{PREMIS_NS}}}event")
    _add(evt, PREMIS_NS, "eventType", info["event_type"])
    _add(evt, PREMIS_NS, "eventDateTime", info["event_datetime"])

    ag = ET.SubElement(rec, f"{{{PREMIS_NS}}}agent")
    _add(ag, PREMIS_NS, "agentName", info["agent_name"])
    _add(ag, PREMIS_NS, "agentVersion", info["agent_version"])

    rg = ET.SubElement(rec, f"{{{PREMIS_NS}}}rights")
    _add(rg, PREMIS_NS, "rightsStatement", info["rights_statement"])


# ----------------------------------------------------------------------
# Conversores
# ----------------------------------------------------------------------
def dc_recurso(r):
    rec = ET.Element("record")
    _sub(rec, "identifier",  r.get("ID_recurso", ""))
    _sub(rec, "title",       r.get("Título do recurso", ""))
    _sub(rec, "creator",     r.get("Instituição responsável", ""))
    _sub(rec, "contributor", r.get("Instituição mantenedora/parceiros", ""))
    for campo in ("Eixo principal", "Eixos secundários",
                  "Termos controlados associados (IDs)"):
        _sub(rec, "subject", r.get(campo, ""))
    _sub(rec, "description", r.get("Descrição/finalidade", ""))
    _sub(rec, "type",        r.get("Tipo de recurso", ""))
    _sub(rec, "format",      r.get("Formato/tecnologia", ""))
    _sub(rec, "source",      r.get("URL oficial", ""))
    _sub(rec, "source",      r.get("URL de acesso/download/API", ""))
    _sub(rec, "language",    r.get("Idioma(s)", ""))
    _sub(rec, "coverage",    r.get("Território de abrangência", ""))
    _sub(rec, "audience",    r.get("Público-alvo", ""))
    _sub(rec, "rights",      r.get("Licença/termos de uso", ""))
    _sub(rec, "date",        r.get("Data da verificação", ""))
    _add_premis(rec, r.get("ID_recurso", ""))
    return rec


def dc_termo(r):
    rec = ET.Element("record")
    _sub(rec, "identifier",  r.get("ID_termo", ""))
    _sub(rec, "title",       r.get("Termo controlado preferido / proposta", ""))
    _sub(rec, "alternative", r.get("Termo atribuído no levantamento original", ""))
    _sub(rec, "subject",     r.get("Área", ""))
    _sub(rec, "subject",     r.get("Subárea", ""))
    _sub(rec, "coverage",    r.get("Tema/escopo", ""))
    _sub(rec, "description", r.get("Garantia literária / evidência", ""))
    _sub(rec, "source",      r.get("URL da fonte terminológica", ""))
    _sub(rec, "source",      r.get("URL oficial do DF", ""))
    _sub(rec, "type",        "Termo controlado")
    _sub(rec, "language",    "pt-BR")
    _sub(rec, "rights",      "CC BY 4.0")
    _add_premis(rec, r.get("ID_termo", ""))
    return rec


# ----------------------------------------------------------------------
# Exportação
# ----------------------------------------------------------------------
def exportar(df, caminho, construtor):
    raiz = ET.Element("dublinCore")
    for _, linha in df.iterrows():
        raiz.append(construtor(linha))
    xml = minidom.parseString(
        ET.tostring(raiz, encoding="unicode")).toprettyxml(indent="  ")
    xml = "\n".join(l for l in xml.splitlines() if l.strip())
    Path(caminho).write_text(xml, encoding="utf-8")
    print(f"✔ {caminho} ({len(df)} registros)")


def main():
    rec = pd.read_csv(PASTA / "catalogo_recursos.csv",
                      sep=";", dtype=str).fillna("")
    voc = pd.read_csv(PASTA / "vocabulario_controlado.csv",
                      sep=";", dtype=str).fillna("")
    exportar(rec, PASTA / "dublin_core_recursos.xml", dc_recurso)
    exportar(voc, PASTA / "dublin_core_vocabulario.xml", dc_termo)


if __name__ == "__main__":
    main()