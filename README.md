# Extrator de Dados de Nota Fiscal com LLM

Aplicação Web em Python para extração estruturada de dados de Notas Fiscais Eletrônicas (DANFE / Contas a Pagar) em formato PDF e classificação inteligente de despesas com inferência via Inteligência Artificial (LLMs).

Projeto desenvolvido para a **1ª Etapa da Avaliação N2** do Projeto Administrativo-Financeiro (UniRV - Universidade de Rio Verde).

---

## 🔗 Links de Acesso

* **Aplicação em Produção (Render):** [https://extrator-de-pdf-7onu.onrender.com](https://extrator-de-pdf-7onu.onrender.com)
* **Repositório no GitHub:** [https://github.com/AtomoPrimal/extrator-de-pdf](https://github.com/AtomoPrimal/extrator-de-pdf)

---

## 🎯 Funcionalidades Principais

1. **Upload de Documento PDF (DANFE):**
   - Suporte a arrastar e soltar (drag & drop) ou seleção manual de arquivos `.pdf`.
   - Extração local instantânea do texto via `pypdf`, evitando gargalos de processamento de imagem e latência.

2. **Extração Estruturada dos Dados Obrigatórios:**
   - **Fornecedor (Emitente):** Razão Social, Nome Fantasia e CNPJ.
   - **Faturado (Destinatário):** Nome Completo e CPF (produtor rural ou filhos: Beltrano, Fulano ou Ciclano).
   - **Dados da Nota:** Número da NF-e, Data de Emissão, Data de Vencimento e Valor Total.
   - **Itens e Parcelas:** Descrição consolidada dos produtos e detalhamento do array de duplicatas/parcelas.

3. **Classificação Automática de Despesas (Inferência via IA):**
   - O tipo da despesa não existe de forma literal na nota fiscal; a LLM analisa o conjunto de itens adquiridos e categoriza a despesa de acordo com o plano de contas:
     - `MANUTENÇÃO E OPERAÇÃO` (Peças, lubrificantes, filtros, rolamentos, reparos, combustíveis)
     - `INSUMOS AGRÍCOLAS` (Sementes, adubos, defensivos agrícolas, fertilizantes)
     - `SERVIÇOS OPERACIONAIS` (Fretes, colheita terceirizada, secagem, armazenagem)
     - `INFRAESTRUTURA E UTILIDADES` (Materiais elétricos, hidráulicos, reformas)
     - `ADMINISTRATIVAS`, `RECURSOS HUMANOS`, `SEGUROS E PROTEÇÃO`, `IMPOSTOS E TAXAS`, `INVESTIMENTOS`.

4. **Interface Gráfica e Exportação:**
   - Design minimalista e limpo, sem elementos visuais supérfluos.
   - Alternância entre abas: **Visualização Formatada** e **JSON Bruto**.
   - Botões utilitários: **Copiar JSON** para a área de transferência e **Baixar JSON** (.json) diretamente no navegador.
   - Painel de resultados com scroll interno dedicado.

5. **Arquitetura Resiliente com Redundância e Failover:**
   - Suporte a múltiplas chaves Google Gemini (`GEMINI_API_KEY`, `GEMINI_API_KEY_2`).
   - Contingência automática com **Groq Cloud (Llama 3.3 70B)** para tolerância a falhas caso haja picos de tráfego (503) ou esgotamento de cotas do Google (429).
   - Timeout de segurança com alternância em loop de redundância.

---

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python 3.11+
* **Backend Web:** [FastAPI](https://fastapi.tiangolo.com/) & [Uvicorn](https://www.uvicorn.org/)
* **Validação de Schemas:** [Pydantic v2](https://docs.pydantic.dev/)
* **Processamento de PDF:** [pypdf](https://pypdf.readthedocs.io/)
* **Modelos de Linguagem:**
  * [Google GenAI SDK](https://github.com/google/google-genai-python) (Gemini Flash)
  * [Groq Cloud API](https://console.groq.com/) (Llama 3.3 70B Versatile)
* **Frontend:** HTML5, Vanilla CSS responsivo e JavaScript nativo (sem dependências pesadas).
* **Testes Automatizados:** [pytest](https://docs.pytest.org/) e `pytest-asyncio`.

---

## 📁 Estrutura de Pastas

```text
├── app/
│   ├── extractor.py         # Motor de extração via LLM e loop de redundância
│   ├── main.py              # Endpoints da API FastAPI (/api/extrair, /health)
│   ├── schemas.py           # Modelos Pydantic (Fornecedor, Faturado, Parcela, NotaFiscalExtracao)
│   └── templates/
│       └── index.html       # Interface Web minimalista com upload, tabs e download JSON
├── instruções do projeto/  # Documentação de requisitos do cliente e DANFE de exemplo
├── tests/                   # Suíte de testes unitários e de integração
│   ├── test_api.py
│   ├── test_extractor.py
│   └── test_schemas.py
├── .env.example             # Modelo de configuração de variáveis de ambiente
├── main.py                  # Ponto de entrada para inicialização do servidor
├── README.md                # Documentação técnica do projeto
└── requirements.txt         # Dependências do projeto
```

---

## 🚀 Como Executar Localmente

### 1. Clonar o Repositório
```bash
git clone https://github.com/AtomoPrimal/extrator-de-pdf.git
cd extrator-de-pdf
```

### 2. Criar e Ativar o Ambiente Virtual
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar as Variáveis de Ambiente
Copie o arquivo `.env.example` para `.env`:
```bash
cp .env.example .env
```
Edite o arquivo `.env` inserindo sua chave de API:
```env
# Chave 1 do Google Gemini (Conta Principal)
GEMINI_API_KEY=sua_chave_gemini_aqui

# Chave 2 do Google Gemini (Opcional - Failover)
GEMINI_API_KEY_2=

# Chave da Groq Cloud (Opcional - Redundância gratuita com Llama 3.3)
GROQ_API_KEY=

PORT=8000
```

### 5. Iniciar o Servidor
```bash
python main.py
```
Acesse a aplicação no navegador em: `http://localhost:8000`

---

## 🧪 Executando os Testes

Para rodar a suíte completa de testes unitários e de integração:
```bash
pytest -v
```

---

## 👥 Autores & Contexto Acadêmico

* **Instituição:** UniRV - Universidade de Rio Verde
* **Projeto:** Sistema Administrativo-Financeiro (Gestão Rural)
* **Etapa:** Avaliação N2 - Etapa 1
