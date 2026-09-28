# Regras Iniciais do Projeto (Até 29/09/2026)

Este documento consolida as diretrizes, restrições arquiteturais e escopo de entrega para a **1ª Etapa da Avaliação N2** do Projeto Administrativo-Financeiro (UniRV).

---

## 1. Objetivo Principal da 1ª Etapa
Desenvolver uma **aplicação Web em Python** capaz de:
1. Receber o upload de um arquivo PDF de Nota Fiscal (DANFE - Contas a Pagar).
2. Processar o documento utilizando **LLM (Gemini)** através do acionamento de um botão.
3. Extrair os campos estruturados obrigatórios e inferir/classificar a despesa.
4. Exibir o resultado diretamente na tela em formato **JSON** (com abas de visualização e botão de copiar).

---

## 2. Restrições e Definições Técnicas Estritas

| Item | Diretriz Definida |
| :--- | :--- |
| **Linguagem & Backend** | **100% Python** (Aplicação Web simples, rápida e direta). |
| **Banco de Dados** | **Nenhum** neste primeiro momento (sem PostgreSQL, Supabase ou ORM). O processamento é sob demanda/em memória. |
| **Interface Visual (UI)** | **Fundo branco e minimalista**. Sem identidade visual rebuscada, sem temas complexos. Apenas os botões e áreas estritamente necessários para executar a tarefa solicitada. |
| **Hospedagem / Deploy** | **Render** (plataforma de deploy em nuvem). |
| **Versionamento (Git/GitHub)** | Uso do **GitHub** focado no essencial (commit, push e merge para alimentar o deploy no Render). Sem preocupação com stacks complexas, badges ou perfumarias visuais no repositório neste momento. |
| **Fluxo com Agentes** | Adoção do ecossistema de **skills do ask-matt** (localizadas na pasta `.agents/skills/`) para suportar a evolução orientada a especificações, TDD e arquitetura nas próximas fases. |

---

## 3. Campos Obrigatórios para Extração (Saída JSON)

A LLM deve processar a nota fiscal e retornar obrigatoriamente a seguinte estrutura de dados:

1. **Fornecedor (Emitente):**
   - Razão Social
   - Nome Fantasia
   - CNPJ
2. **Faturado (Destinatário):**
   - Nome Completo
   - CPF (pertencente ao produtor rural ou a um dos filhos: Beltrano, Fulano ou Ciclano)
3. **Número da Nota Fiscal**
4. **Data de Emissão**
5. **Descrição dos Produtos:**
   - Lista / descrição sucinta dos itens faturados (sem necessidade de modelagem de entidade Produtos).
6. **Financeiro e Parcelas:**
   - Quantidade de Parcelas
   - Data de Vencimento
   - Valor Total da Nota
   - *Nota de arquitetura:* Estrutura preparada em array/lista de parcelas para expansão futura.
7. **Classificação da DESPESA (Inferência via IA):**
   - O campo **não existe de forma literal** na nota fiscal.
   - Deve ser **interpretado e classificado pelo Gemini** analisando os produtos da nota (ex.: graxas, óleos, filtros e rolamentos $\rightarrow$ `MANUTENÇÃO E OPERAÇÃO`).
   - Categorias base: *Insumos Agrícolas, Manutenção e Operação, Recursos Humanos, Serviços Operacionais, Infraestrutura e Utilidades, Administrativas, Seguros e Proteção, Impostos e Taxas, Investimentos*.

---

## 4. Elementos da Interface Gráfica Web

A página Web deve conter exclusivamente:
- **Título simples:** "Extração de Dados de Nota Fiscal"
- **Área de Upload:** Seletor de arquivo `.pdf`.
- **Botão de Ação:** `EXTRAIR DADOS` (aciona o processamento via Gemini).
- **Área de Resultado:**
  - Exibição dos dados retornados.
  - Abas: "Visualização Formatada" e "JSON".
  - Botão `Copiar JSON`.

---

## 5. Próximos Passos (Após Entrega de 29/09)
*Os itens abaixo fazem parte da 2ª Etapa (28/10/2026) e **não** devem ser implementados agora:*
- Persistência em banco de dados relacional.
- Módulos de manutenção (CRUD) de Fornecedor, Cliente, Faturado, Tipos de Receita e Tipos de Despesa.
- Regra de negócio de inativação e reativação de cadastros (sem exclusão física).
- Módulo completo de Contas a Receber e rateio multicategorias.
