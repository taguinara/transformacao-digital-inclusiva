# 📚 Glossário de Vocabulário Controlado — Curadoria, Normalização e Dashboard

Pipeline de **curadoria, normalização e publicação do glossário de termos revisados** do vocabulário controlado, com painel em Streamlit, leitura automatizada da planilha no Google Sheets e atualização contínua do dashboard.

Lê a planilha de glossário, normaliza os campos, gera visões analíticas e indicadores de qualidade, mantém a fonte versionada no GitHub e oferece um dashboard em português acessível e atualizado automaticamente.

🔗 **Dashboard online:** `https://transformacao-digital-inclusiva.streamlit.app/`

## Fluxo

```text
planilha Google Sheets
  -> st-gsheets-connection    leitura da fonte com cache controlado (ttl)
  -> app.py                   normalização, filtros e indicadores
  -> @st.fragment             atualização periódica em tela (run_every)
  -> git push                 redeploy automático no Streamlit Cloud
  -> dashboard atualizado     sem novo commit para novos termos
```

## Início rápido

```bash
git clone URL-DO-REPOSITORIO
cd glossario-dashboard
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Configure o segredo local antes de rodar
# Substitua pelo link real da sua planilha
cat > .streamlit/secrets.toml <<EOF
[connections.gsheets]
spreadsheet = "https://docs.google.com/spreadsheets/d/SEU_ID_AQUI/edit?usp=sharing"
EOF

streamlit run app.py
```

Requer Python 3.10 ou superior.

## Licença e citação

GLOSSÁRIO. *Curadoria de Vocabulário Controlado — Dashboard e Automação*. Brasília, 2026.
