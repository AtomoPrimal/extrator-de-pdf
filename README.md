# Extrator de Dados de Nota Fiscal com LLM

Aplicação Web em Python para extração de dados de notas fiscais (DANFE em PDF) e classificação automática de despesas utilizando IA (Google Gemini e Groq Cloud).

Desenvolvido para a **Avaliação N2 - Etapa 1** (UniRV - Universidade de Rio Verde).

---

## 🔗 Links

- **Aplicação no Render:** [https://extrator-de-pdf-7onu.onrender.com](https://extrator-de-pdf-7onu.onrender.com)
- **Repositório GitHub:** [https://github.com/AtomoPrimal/extrator-de-pdf](https://github.com/AtomoPrimal/extrator-de-pdf)

---

## 🚀 Funcionalidades

- **Upload de PDF:** Processamento rápido e direto de arquivos DANFE.
- **Extração Estruturada:** Fornecedor (Razão Social, Nome Fantasia, CNPJ), Faturado (Nome, CPF), número da nota, datas, valores e parcelas.
- **Classificação de Despesa via IA:** Inferência automática da categoria de despesa (ex.: Manutenção e Operação, Insumos Agrícolas) com base nos produtos faturados.
- **Visualização & Exportação:** Aba com visualização formatada, aba com JSON bruto, botão para copiar e botão para baixar o arquivo JSON.
- **Redundância:** Suporte a múltiplas chaves e failover automático (Gemini e Groq Cloud).

---

## 🛠️ Tecnologias

- **Backend:** Python, FastAPI, Uvicorn
- **IA / LLM:** Google GenAI (Gemini), Groq Cloud (Llama 3.3)
- **Processamento & Schemas:** pypdf, Pydantic v2
- **Frontend:** HTML, CSS e JavaScript nativo (sem frameworks pesados)

---

## 💻 Como Executar Localmente

```bash
# 1. Clonar o repositório
git clone https://github.com/AtomoPrimal/extrator-de-pdf.git
cd extrator-de-pdf

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar chave no arquivo .env
# GEMINI_API_KEY=sua_chave_aqui

# 4. Iniciar a aplicação
python main.py
```
Acesse no navegador: `http://localhost:8000`

---

## 🧪 Testes

```bash
pytest
```
