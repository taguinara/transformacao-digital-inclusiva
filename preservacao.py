# -*- coding: utf-8 -*-
"""
Módulo de preservação digital:
  - checksum SHA-256 dos arquivos gerados
  - snapshot versionado em saida/historico/<timestamp>/
  - metadados PREMIS para uso no dublin_core.py
"""

from __future__ import annotations
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd

PASTA = Path("saida")
VERSAO_PIPELINE = "1.0.0"
PREMIS_NS = "http://www.loc.gov/premis/v3"

_CACHE_CHECKSUM: dict = {}


# ----------------------------------------------------------------------
# CHECKSUM
# ----------------------------------------------------------------------
def checksum_arquivo(path: Path, algoritmo: str = "sha256") -> str:
    """SHA-256 em blocos, com cache por (path, mtime)."""
    st = path.stat()
    key = (str(path), st.st_mtime)
    if key in _CACHE_CHECKSUM:
        return _CACHE_CHECKSUM[key]
    h = hashlib.new(algoritmo)
    with open(path, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    _CACHE_CHECKSUM[key] = h.hexdigest()
    return _CACHE_CHECKSUM[key]


def gerar_manifest(pasta: Path = PASTA) -> dict:
    """Manifesto com SHA-256, tamanho e data de cada arquivo em saida/."""
    manifest = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "algoritmo": "sha256",
        "versao_pipeline": VERSAO_PIPELINE,
        "arquivos": [],
    }
    for f in sorted(pasta.glob("*.*")):
        if f.is_file() and not f.name.startswith("manifest"):
            st = f.stat()
            manifest["arquivos"].append({
                "nome": f.name,
                "sha256": checksum_arquivo(f),
                "tamanho_bytes": st.st_size,
                "modificado_em": datetime.fromtimestamp(
                    st.st_mtime).isoformat(timespec="seconds"),
            })
    return manifest


def salvar_manifest(manifest: dict, pasta: Path = PASTA) -> None:
    (pasta / "manifest_sha256.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(manifest["arquivos"]).to_csv(
        pasta / "manifest_sha256.csv",
        index=False, sep=";", encoding="utf-8-sig")
    print(f"✔ Manifesto salvo: {len(manifest['arquivos'])} arquivos")


# ----------------------------------------------------------------------
# VERSIONAMENTO
# ----------------------------------------------------------------------
def snapshot(pasta: Path = PASTA) -> Path | None:
    """Copia o estado atual de saida/ para saida/historico/<timestamp>/."""
    if not pasta.exists() or not any(pasta.glob("*.*")):
        print("  (snapshot ignorado — pasta vazia)")
        return None
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    destino = pasta / "historico" / ts
    destino.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in pasta.glob("*.*"):
        if f.is_file():
            shutil.copy2(f, destino / f.name)
            n += 1
    print(f"✔ Snapshot: {n} arquivos → {destino.relative_to(pasta.parent)}")
    return destino


# ----------------------------------------------------------------------
# VERIFICAÇÃO
# ----------------------------------------------------------------------
def verificar(pasta: Path = PASTA) -> None:
    """Compara checksums atuais com o manifesto salvo."""
    m = pasta / "manifest_sha256.json"
    if not m.exists():
        print("  ⚠ Nenhum manifesto encontrado. Rode: preservacao.py checksum")
        return
    manifest = json.loads(m.read_text(encoding="utf-8"))
    ok = alterados = ausentes = 0
    for item in manifest["arquivos"]:
        p = pasta / item["nome"]
        if not p.exists():
            print(f"  ✗ AUSENTE: {item['nome']}"); ausentes += 1
        elif checksum_arquivo(p) != item["sha256"]:
            print(f"  ⚠ ALTERADO: {item['nome']}"); alterados += 1
        else:
            ok += 1
    print(f"✔ Inalterados: {ok} | Alterados: {alterados} | Ausentes: {ausentes}")


# ----------------------------------------------------------------------
# PREMIS (usado por dublin_core.py)
# ----------------------------------------------------------------------
def info_premis(arquivo: Path, identificador: str | None = None) -> dict:
    """Metadados PREMIS de um arquivo (object + event + agent + rights)."""
    if not arquivo.exists():
        return {}
    st = arquivo.stat()
    return {
        "object_identifier":   identificador or arquivo.stem,
        "object_size":         st.st_size,
        "object_format":       (arquivo.suffix.lstrip(".").upper() or "UNKNOWN"),
        "object_checksum":     checksum_arquivo(arquivo),
        "object_checksum_alg": "SHA-256",
        "event_type":          "ingest",
        "event_datetime":      datetime.now().isoformat(timespec="seconds"),
        "agent_name":          "pipeline-curadoria-tdi",
        "agent_version":       VERSAO_PIPELINE,
        "rights_statement":    "CC BY 4.0",
    }


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("snapshot", "all"):
        snapshot()
    if cmd in ("checksum", "all"):
        salvar_manifest(gerar_manifest())
    if cmd == "verificar":
        verificar()
    if cmd not in ("snapshot", "checksum", "verificar", "all"):
        print("Uso: python preservacao.py [snapshot|checksum|verificar|all]")