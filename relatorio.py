# -*- coding: utf-8 -*-
"""
Gera relatório de avaliação da curadoria (saida/RELATORIO.md)
e imprime sumário no console.
Tolera abas vazias ou ausentes sem quebrar.
"""

from pathlib import Path
from datetime import datetime
import json
import pandas as pd

PASTA = Path("saida")


def carregar():
    """Carrega cada CSV; retorna DataFrame vazio se ausente ou vazio."""
    def ler(nome):
        p = PASTA / f"{nome}.csv"
        if not p.exists() or p.stat().st_size == 0:
            return pd.DataFrame()
        try:
            df = pd.read_csv(p, sep=";", dtype=str, encoding="utf-8-sig")
            return df.fillna("")
        except pd.errors.EmptyDataError:
            return pd.DataFrame()

    return {
        "recursos":    ler("catalogo_recursos"),
        "vocabulario": ler("vocabulario_controlado"),
        "novos":       ler("novos_termos"),
        "relacoes":    ler("relacoes"),
        "fontes":      ler("fontes"),
        "avaliacoes":  ler("avaliacoes"),
    }


def pct(n, total):
    return f"{100 * n / total:.0f}%" if total else "—"


def completude(df, campos):
    linhas = ["| Campo | Preenchido | Vazio | Completude |",
              "|-------|-----------|-------|------------|"]
    for c in campos:
        if c in df.columns:
            n = int((df[c] != "").sum())
            v = len(df) - n
            linhas.append(f"| {c} | {n} | {v} | {pct(n, len(df))} |")
    return linhas


def gerar():
    d = carregar()
    rec, voc, novos, rel = d["recursos"], d["vocabulario"], d["novos"], d["relacoes"]
    font, aval = d["fontes"], d["avaliacoes"]

    L = []
    L.append("# Relatório de Curadoria — Transformação Digital Inclusiva\n")
    L.append(f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")

    # 1. Sumário
    L.append("## 1. Sumário executivo\n")
    L.append("| Aba | Registros |")
    L.append("|-----|-----------|")
    for nome, df in [("Catálogo de recursos", rec),
                     ("Vocabulário controlado", voc),
                     ("Novos termos propostos", novos),
                     ("Relações recurso-termo", rel),
                     ("Fontes oficiais", font),
                     ("Avaliações críticas", aval)]:
        L.append(f"| {nome} | {len(df)} |")
    L.append("")

    # 2. Catálogo
    L.append("## 2. Catálogo de recursos\n")
    if not rec.empty:
        if "Status da curadoria" in rec.columns:
            L.append("### Distribuição por status\n")
            for k, v in rec["Status da curadoria"].value_counts().items():
                L.append(f"- **{k}**: {v} ({pct(v, len(rec))})")
            L.append("")

        if "Eixo principal" in rec.columns:
            L.append("### Distribuição por eixo principal\n")
            for k, v in rec["Eixo principal"].value_counts().items():
                L.append(f"- {k}: {v}")
            L.append("")

        if "Tipo de recurso" in rec.columns:
            L.append("### Distribuição por tipo de recurso\n")
            for k, v in rec["Tipo de recurso"].value_counts().items():
                L.append(f"- {k}: {v}")
            L.append("")

        L.append("### Completude dos metadados\n")
        campos = ["Título do recurso", "URL oficial", "Descrição/finalidade",
                  "Instituição responsável", "Eixo principal", "Tipo de recurso",
                  "Público-alvo", "Termos controlados associados (IDs)",
                  "Evidência de acessibilidade", "Status da curadoria"]
        L.extend(completude(rec, campos))
        L.append("")

        sem_url    = (rec["URL oficial"] == "").sum() if "URL oficial" in rec else 0
        sem_termos = ((rec["Termos controlados associados (IDs)"] == "").sum()
                      if "Termos controlados associados (IDs)" in rec else 0)
        sem_evid   = ((rec["Evidência de acessibilidade"] == "").sum()
                      if "Evidência de acessibilidade" in rec else 0)

        L.append("### Lacunas identificadas\n")
        L.append(f"- Recursos **sem URL oficial**: {int(sem_url)}")
        L.append(f"- Recursos **sem termos controlados**: {int(sem_termos)}")
        L.append(f"- Recursos **sem evidência de acessibilidade**: {int(sem_evid)}")
        L.append("")
    else:
        L.append("⚠️ **Catálogo de recursos vazio.**\n")

    # 3. Vocabulário
    L.append("## 3. Vocabulário controlado\n")
    if not voc.empty:
        if "Área" in voc.columns:
            L.append("### Distribuição por área\n")
            for k, v in voc["Área"].value_counts().items():
                L.append(f"- {k}: {v}")
            L.append("")

        if "Status do termo" in voc.columns:
            L.append("### Status dos termos\n")
            for k, v in voc["Status do termo"].value_counts().items():
                L.append(f"- **{k}**: {v}")
            L.append("")

        if "Fonte terminológica/autoridade" in voc.columns:
            n = (voc["Fonte terminológica/autoridade"] != "").sum()
            L.append(f"- Termos com fonte terminológica: {n}/{len(voc)} ({pct(n, len(voc))})")
        if "URL da fonte terminológica" in voc.columns:
            n = (voc["URL da fonte terminológica"] != "").sum()
            L.append(f"- Termos com URL de fonte: {n}/{len(voc)} ({pct(n, len(voc))})")
        L.append("")
    else:
        L.append("⚠️ **Vocabulário controlado vazio.**\n")

    # 4. Relações
    L.append("## 4. Relações recurso-termo\n")
    if not rel.empty and "ID_recurso" in rel.columns and "ID_termo" in rel.columns:
        L.append(f"- Recursos com pelo menos uma relação: "
                 f"{rel['ID_recurso'].nunique()}/{len(rec)}")
        L.append(f"- Termos com pelo menos uma relação: "
                 f"{rel['ID_termo'].nunique()}/{len(voc)}")
        if "ID_recurso" in rec.columns:
            orfaos = sorted(set(rec["ID_recurso"]) - set(rel["ID_recurso"]))
            if orfaos:
                L.append(f"- **Recursos órfãos:** {', '.join(orfaos)}")
        L.append("")
    else:
        L.append("⚠️ **Nenhuma relação registrada.**\n")

    # 5. Novos termos
    L.append("## 5. Novos termos propostos\n")
    if not novos.empty:
        L.append(f"- Total de novos termos propostos: {len(novos)}")
        if "Status/observação" in novos.columns:
            for k, v in novos["Status/observação"].value_counts().head(5).items():
                L.append(f"  - {k[:60]}… ({v})")
        L.append("")
    else:
        L.append("⚠️ **Nenhum novo termo proposto.**\n")

    # 6. Avaliações
    L.append("## 6. Avaliações críticas\n")
    if aval.empty:
        L.append("⚠️ **Nenhuma avaliação crítica registrada.** "
                 "O template existe, mas o preenchimento está pendente.")
    else:
        L.append(f"- {len(aval)} avaliações registradas")
    L.append("")

    # 7. Preservação digital
    L.append("## 7. Preservação digital\n")

    manifest = PASTA / "manifest_sha256.json"
    if manifest.exists():
        m = json.loads(manifest.read_text(encoding="utf-8"))
        L.append(f"- **Manifesto gerado em:** {m['gerado_em']}")
        L.append(f"- **Algoritmo:** {m['algoritmo'].upper()}")
        L.append(f"- **Versão do pipeline:** {m['versao_pipeline']}")
        L.append(f"- **Arquivos rastreados:** {len(m['arquivos'])}")
        total_mb = sum(a["tamanho_bytes"] for a in m["arquivos"]) / 1024 / 1024
        L.append(f"- **Tamanho total:** {total_mb:.2f} MB")
        L.append("")
        L.append("| Arquivo | Tamanho | SHA-256 (12 primeiros) |")
        L.append("|---------|---------|------------------------|")
        for a in m["arquivos"]:
            kb = a["tamanho_bytes"] / 1024
            L.append(f"| {a['nome']} | {kb:.1f} KB | `{a['sha256'][:12]}…` |")
        L.append("")
    else:
        L.append("⚠️ **Nenhum manifesto de checksums encontrado.** "
                 "Rode `python preservacao.py checksum`.\n")

    hist = PASTA / "historico"
    if hist.exists():
        snaps = sorted(d for d in hist.iterdir() if d.is_dir())
        L.append(f"- **Snapshots históricos:** {len(snaps)}")
        if snaps:
            L.append(f"- **Último snapshot:** `{snaps[-1].name}`")
            L.append(f"- **Primeiro snapshot:** `{snaps[0].name}`")
        L.append("")
    else:
        L.append("- Nenhum snapshot histórico. "
                 "Rode `python preservacao.py snapshot` antes da próxima geração.\n")

    dc_files = list(PASTA.glob("dublin_core_*.xml"))
    if dc_files:
        L.append(f"- **XMLs com PREMIS:** {len(dc_files)} "
                 f"({', '.join(f.name for f in dc_files)})")
    L.append("")

    # 8. Qualidade
    L.append("## 8. Qualidade dos dados\n")
    if not rec.empty:
        celulas_vazias = (rec == "").sum().sum()
        L.append(f"- Células vazias no catálogo: {int(celulas_vazias)}")
        completos = (rec != "").all(axis=1).sum()
        L.append(f"- Recursos totalmente preenchidos: {int(completos)}/{len(rec)}")
    else:
        L.append("- Sem dados para avaliar.")
    L.append("")

    # 9. Recomendações
    L.append("## 9. Recomendações priorizadas\n")
    L.append("1. **Validar termos provisórios** — priorizar status "
             "'A revisar' e 'Completar e revisar'.")
    L.append("2. **Preencher avaliações críticas** — usar a aba "
             "`Avaliacao_Critica` para cada recurso catalogado.")
    L.append("3. **Auditar acessibilidade** — aplicar WCAG 2.2 / eMAG aos "
             "recursos marcados como 'Identificado'.")
    L.append("4. **Validar culturalmente** — consultar comunidades "
             "representadas (garantia cultural).")
    L.append("5. **Reduzir recursos órfãos** — conectar todos os recursos "
             "a pelo menos um termo controlado.")
    L.append("6. **Rodar `preservacao.py verificar` periodicamente** — "
             "detectar alterações não registradas nos arquivos de saída.")
    L.append("7. **Instalar repositório (DSpace/Dataverse)** — importar os "
             "XMLs gerados e ativar OAI-PMH.")
    L.append("8. **Documentar política de retenção e migração** — prazos, "
             "formatos-alvo, responsáveis.")

    md = "\n".join(L)
    (PASTA / "RELATORIO.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"\n✔ Relatório salvo em: {PASTA / 'RELATORIO.md'}")


if __name__ == "__main__":
    gerar()