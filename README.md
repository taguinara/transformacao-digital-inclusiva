# 📚 Curadoria de Metadados — Transformação Digital Inclusiva

Sistema de curadoria, normalização e publicação de metadados para o projeto **Transformação Digital Inclusiva: cidadania, acessibilidade e ensino**.

Pipeline simples para transformar um vocabulário controlado em Word em dados estruturados (Excel, CSV, JSON, Dublin Core) e visualizá-los num dashboard interativo.

## 📂 Estrutura

transformacao-digital-inclusiva/
├── ler_docx.py # Word → Excel
├── metadados.py # Excel → CSV/JSON/Excel (normalizado)
├── dublin_core.py # CSV → Dublin Core XML
├── app.py # Dashboard Streamlit
├── requirements.txt
├── Controle_Vocabulario.docx # entrada (você edita aqui)
└── saida/ # criada automaticamente

---

## ⚙️ Instalação

```bash
pip install -r requirements.txt

🚀 Como usar
Rode na ordem:

bash
python ler_docx.py       # 1. Word → Excel
python metadados.py      # 2. Normaliza Área + extrai URLs
python dublin_core.py    # 3. Gera dublin_core.xml
streamlit run app.py     # 4. Abre o dashboard
Dashboard em http://localhost:8501.

🧩 O que cada script faz
Script	Entrada	Saída	O que faz
ler_docx.py	.docx	.xlsx	Lê a tabela do Word, resolve células mescladas e propaga Área/Subárea
metadados.py	.xlsx	.csv, .json, .xlsx	Normaliza a coluna Área e extrai URLs da garantia literária
dublin_core.py	.csv	.xml	Converte cada registro em Dublin Core
app.py	.csv	—	Dashboard com filtros, gráficos e download

📋 Formato do Excel
7 colunas obrigatórias:

text
Area | Subarea | Tema_Escopo | Area_Termo | Subarea_Termo | Garantia_Literaria | Remissivas
Use _ em vez de / nos nomes das colunas.


📤 Saídas geradas
saida/metadados_limpos.xlsx
saida/metadados_limpos.csv
saida/metadados_limpos.json
saida/dublin_core.xml

📈 Dashboard
Métricas: registros, áreas, subáreas, URLs
Filtros por Área / Subárea / busca livre
Gráficos de barras
Tabela interativa + detalhe de cada registro
Download em CSV ou JSON
