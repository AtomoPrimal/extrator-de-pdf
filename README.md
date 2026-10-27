# Extrator de Dados de Nota Fiscal com LLM

Aplicação Web em Python para extração de dados de notas fiscais (DANFE em PDF) e classificação automática de despesas utilizando IA (Google Gemini e Groq Cloud).

Desenvolvido para a **Avaliação N2** (UniRV - Universidade de Rio Verde), nas etapas 1 (extração via IA) e 2 (persistência em banco de dados, cadastros e lançamento automático de contas).

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

### Etapa 2 — Persistência e Cadastros

- **Banco de Dados:** SQLite, acessado via SQLAlchemy (arquivo `contas.db`, criado automaticamente).
- **Consulta de Cadastros:** Após a extração, o sistema consulta automaticamente se o FORNECEDOR (por CNPJ), o FATURADO (por CPF) e a DESPESA (por descrição) já existem no banco, mostrando o resultado na tela (existe/não existe, com ID quando existir).
- **Lançamento Automático:** Ao confirmar o lançamento, o sistema cria os cadastros que ainda não existirem (Fornecedor, Faturado, Classificação) e registra o `MOVIMENTOCONTAS` com sua(s) `PARCELACONTAS`, como Conta a Pagar ou Conta a Receber.
- **Manter Pessoas:** CRUD de Fornecedor/Cliente e Faturado, com busca por nome/documento/e-mail, listagem "Todos" (apenas ativos) ou por busca, ordenação de colunas, e inativação/reativação lógica (sem exclusão física).
- **Manter Classificação:** CRUD de Tipo de Despesa e Tipo de Receita, com as mesmas regras de busca/inativação/reativação.
- **Registrar Contas:** Listagem de todos os lançamentos (Contas a Pagar / Contas a Receber), com fornecedor, faturado, classificações e parcelas, e inativação/reativação lógica.
- **Regra de negócio:** nenhum cadastro ou lançamento é excluído fisicamente — toda remoção marca o registro como `INATIVO`, sempre reversível para `ATIVO`.

---

## 🛠️ Tecnologias

- **Backend:** Python, FastAPI, Uvicorn
- **IA / LLM:** Google GenAI (Gemini), Groq Cloud (Llama 3.3)
- **Processamento & Schemas:** pypdf, Pydantic v2
- **Banco de Dados:** SQLite + SQLAlchemy
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
