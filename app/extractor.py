import os
import json
import re
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from app.schemas import NotaFiscalExtracao, CATEGORIAS_DESPESA_VALIDAS

# Load .env file if present
load_dotenv()

PROMPT_SISTEMA_EXTRACAO = f"""
Você é um especialista em análise e extração de dados fiscais de documentos rurais e comerciais (DANFE / Notas Fiscais Eletrônicas).

Sua tarefa é analisar o arquivo PDF da nota fiscal fornecido e extrair com rigor e precisão as informações solicitadas no formato estruturado especificado.

REGRAS DE EXTRAÇÃO:
1. FORNECEDOR (EMITENTE):
   - razao_social: Razão social / Nome empresarial do emitente da nota fiscal.
   - nome_fantasia: Nome fantasia (se não houver, use a Razão Social ou deixe null).
   - cnpj: CNPJ formatado ou apenas dígitos.

2. FATURADO (DESTINATÁRIO):
   - nome_completo: Nome completo da pessoa física ou destinatário na nota (geralmente o produtor rural ou um dos filhos: Beltrano, Fulano ou Ciclano).
   - cpf: CPF do faturado.

3. DADOS DA NOTA:
   - numero_nota: Número da Nota Fiscal (NF-e).
   - data_emissao: Data de emissão no formato DD/MM/AAAA.
   - descricao_produtos: Resumo consolidado ou lista dos produtos/serviços faturados (ex: 'Graxa, retentores, apoios, buchas e rolamentos').
   - quantidade_parcelas: Número total de parcelas (duplicatas/faturas). Se houver 1 parcela, coloque 1.
   - data_vencimento: Data de vencimento principal ou da 1ª parcela no formato DD/MM/AAAA.
   - valor_total: Valor total da nota fiscal (número decimal em Reais).
   - parcelas: Lista de todas as parcelas encontradas no campo Fatura/Duplicatas, contendo 'numero' (1, 2...), 'data_vencimento' (DD/MM/AAAA) e 'valor'. Se não houver detalhamento de duplicatas, crie uma parcela única com o valor total da nota.

4. CLASSIFICAÇÃO DA DESPESA (INFERÊNCIA OBRIGATÓRIA VIA IA):
   - ATENÇÃO: O campo 'classificacao_despesa' NÃO é um campo literal na nota fiscal!
   - Você DEVE interpretar os produtos comprados e classificar o registro OBRIGATORIAMENTE em UMA das seguintes categorias:
{json.dumps(CATEGORIAS_DESPESA_VALIDAS, indent=2, ensure_ascii=False)}

   Guia de categorização:
   - MANUTENÇÃO E OPERAÇÃO: Graxas, lubrificantes, combustíveis, peças, parafusos, rolamentos, ferramentas, reparos, filtros, correias.
   - INSUMOS AGRÍCOLAS: Sementes, fertilizantes, adubos, defensivos agrícolas, defensivos químicos, calcário.
   - INFRAESTRUTURA E UTILIDADES: Materiais elétricos, hidráulicos, materiais de construção civil, reformas.
   - SERVIÇOS OPERACIONAIS: Frete, colheita, transporte, secagem, armazenagem, pulverização.
   - ADMINISTRATIVAS: Honorários, contabilidade, taxas bancárias.
   - INVESTIMENTOS: Aquisição de tratores, implementos de grande porte, veículos, terras.

   - Forneça também uma breve 'justificativa_classificacao' explicando por que essa categoria foi atribuída.
"""

def extract_invoice_data(
    pdf_bytes: bytes,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.5-flash"
) -> NotaFiscalExtracao:
    """
    Extrai os dados de uma nota fiscal em PDF utilizando o Google Gemini.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError(
            "GEMINI_API_KEY não configurada. Defina a variável de ambiente GEMINI_API_KEY ou informe-a na interface."
        )

    client = genai.Client(api_key=key)

    response = client.models.generate_content(
        model=model_name,
        contents=[
            types.Part.from_bytes(
                data=pdf_bytes,
                mime_type="application/pdf"
            ),
            PROMPT_SISTEMA_EXTRACAO
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=NotaFiscalExtracao,
            temperature=0.1
        )
    )

    raw_text = response.text.strip()

    # Caso a resposta venha envolvida em markdown block ```json ... ```
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)

    data_dict = json.loads(raw_text)
    return NotaFiscalExtracao(**data_dict)
