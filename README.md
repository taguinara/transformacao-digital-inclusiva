# 📚 Curadoria Digital dos Metadados — Transformação Digital Inclusiva

![Python](https://img.shields.io/badge/python-3.10%2B-0072B2?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/dashboard-Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Integridade](https://img.shields.io/badge/integridade-SHA--256-56B4E9)

Pipeline de **curadoria, normalização e publicação de metadados** do projeto
**Transformação Digital Inclusiva: cidadania, acessibilidade e ensino**
(IBICT - PD&I).
 
Lê a planilha de curadoria, normaliza os campos, gera CSV, JSON e Dublin Core
XML com PREMIS, garante a integridade com SHA-256 e snapshots versionados, e
oferece um dashboard acessível em Streamlit.

🔗 **Dashboard online:** `https://transformacao-digital-inclusiva.streamlit.app`

## Fluxo
 
```text
planilha .xlsx
  -> python ler_excel.py      CSVs por aba em saida/
  -> python metadados.py      metadados_limpos.csv e JSON
  -> python dublin_core.py    Dublin Core XML + PREMIS
  -> python preservacao.py    SHA-256 + snapshots em saida/historico/
  -> python relatorio.py      saida/RELATORIO.md
  -> streamlit run app.py     dashboard
```
 
## Início rápido
 
```bash
git clone URL-DO-REPOSITORIO
cd transformacao-digital-inclusiva
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
 
python ler_excel.py
python metadados.py
streamlit run app.py
```
 
Requer Python 3.10 ou superior.
 
## Conteúdo da planilha
 
| Aba | Registros |
|-----|-----------|
| Catálogo de recursos | 13 |
| Vocabulário controlado | 113 |
| Novos termos propostos | 25 |
| Relações recurso-termo | 27 |
| Fontes oficiais | 14 |
| Avaliações críticas | 0 |
 
## Dashboard e acessibilidade
 
- Painel com quantitativo por aba, áreas e subáreas, cartões de registros,
  tabela e exportação em CSV e JSON.
- Busca sem acentos e filtros por área e subárea.
- Texto ajustável (90% a 150%), alto contraste, redução de animações e foco
  visível para teclado.
- Paleta segura para daltonismo e tabela alternativa para cada gráfico.
- Se não houver CSV em `saida/`, aceita upload na barra lateral.

## Publicação no Streamlit Cloud
 
1. Faça commit de `app.py`, `requirements.txt`, `.streamlit/config.toml` e da
   pasta `saida/` no GitHub.
2. Em https://share.streamlit.io, clique em **Create app**, escolha o
   repositório, a branch e `app.py`, e clique em **Deploy**.
3. Para atualizar os dados, gere os CSVs de novo e faça commit.

## Preservação
 
- SHA-256 de todos os arquivos em `saida/manifest_sha256.json` e `.csv`.
- Snapshots em `saida/historico/<timestamp>/`.
- Dublin Core + PREMIS em `saida/dublin_core_*.xml`.

## Problemas comuns
 
| Problema | Solução |
|----------|---------|
| Arquivo não encontrado | Rode `ler_excel.py` e `metadados.py` |
| Acentos quebrados | Importe como UTF-8, separador `;` |
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| Dashboard vazio na nuvem | Inclua `saida/` no commit |
 
## Licença e citação
 
IBICT. *Curadoria de Metadados - Transformação Digital Inclusiva*. Brasília, 2026.
