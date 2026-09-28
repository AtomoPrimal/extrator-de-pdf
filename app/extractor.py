import concurrent.futures
import io
import json
import os
import re
import time
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
import httpx
from pypdf import PdfReader

from app.schemas import CATEGORIAS_DESPESA_VALIDAS, NotaFiscalExtracao

# Carrega variáveis do arquivo .env
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

MODELS_TO_TRY = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.8-flash",
    "gemini-flash-latest",
]


def _call_gemini(client: genai.Client, candidate_model: str, request_contents: list, timeout_seconds: float = 15.0) -> NotaFiscalExtracao:
    """Executa a chamada ao Gemini com timeout rígido em thread separada."""
    def _do_call():
        return client.models.generate_content(
            model=candidate_model,
            contents=request_contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=NotaFiscalExtracao,
                temperature=0.1,
            ),
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_do_call)
        response = future.result(timeout=timeout_seconds)

    raw_text = response.text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)

    data_dict = json.loads(raw_text)
    return NotaFiscalExtracao(**data_dict)


def _call_groq(groq_key: str, text: str, timeout_seconds: float = 15.0) -> NotaFiscalExtracao:
    """Executa a extração via Groq Cloud (Llama 3.3 70B gratuito) com timeout rígido."""
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": f"{PROMPT_SISTEMA_EXTRACAO}\n\nIMPORTANTE: Retorne ESTRITAMENTE um objeto JSON válido correspondente ao schema solicitado.",
            },
            {
                "role": "user",
                "content": f"DADOS DA NOTA FISCAL (DANFE):\n{text}",
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
    }

    with httpx.Client(timeout=timeout_seconds) as http_client:
        resp = http_client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        res_json = resp.json()
        raw_text = res_json["choices"][0]["message"]["content"].strip()
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text)
        return NotaFiscalExtracao.model_validate_json(raw_text)


def extract_invoice_data(
    pdf_bytes: bytes,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    timeout_per_api: float = 15.0,
    max_rounds: int = 2,
) -> NotaFiscalExtracao:
    """
    Extrai dados da nota fiscal com redundância e failover entre:
    1) Gemini Chave 1 (Conta Principal)
    2) Gemini Chave 2 (Segunda Conta Google)
    3) Groq Cloud (Llama 3.3 70B Gratuito)
    Se qualquer provedor demorar mais que 15 segundos ou falhar, alterna automaticamente para o próximo.
    """
    # 1. Recupera Chaves do Gemini (Conta 1 e Conta 2)
    gemini_keys = []
    if api_key and api_key.strip():
        gemini_keys.append(api_key.strip().strip('"').strip("'"))
    else:
        for var_name in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_KEY", "API_KEY", "gemini_api_key"]:
            val = os.getenv(var_name)
            if val and val.strip():
                gemini_keys.append(val.strip().strip('"').strip("'"))
                break

    for var_name in ["GEMINI_API_KEY_2", "GEMINI_API_KEY_SECONDARY", "GEMINI_KEY_2", "GOOGLE_API_KEY_2"]:
        val = os.getenv(var_name)
        if val and val.strip():
            cleaned = val.strip().strip('"').strip("'")
            if cleaned not in gemini_keys:
                gemini_keys.append(cleaned)
            break

    # 2. Recupera Chave da Groq Cloud (Gratuita)
    groq_key = None
    for var_name in ["GROQ_API_KEY", "GROQ_KEY"]:
        val = os.getenv(var_name)
        if val and val.strip():
            groq_key = val.strip().strip('"').strip("'")
            break

    if not gemini_keys and not groq_key:
        raise ValueError(
            "Nenhuma chave de API configurada. Defina GEMINI_API_KEY, GEMINI_API_KEY_2 ou GROQ_API_KEY no arquivo .env."
        )

    # 3. Extração de texto do PDF via pypdf (instantânea e leve)
    extracted_text = ""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        extracted_text = "\n".join([page.extract_text() or "" for page in reader.pages]).strip()
    except Exception:
        extracted_text = ""

    if extracted_text:
        request_contents = [
            f"{PROMPT_SISTEMA_EXTRACAO}\n\n--- DADOS DA NOTA FISCAL (DANFE) ---\n{extracted_text}"
        ]
    else:
        request_contents = [
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            PROMPT_SISTEMA_EXTRACAO,
        ]

    models_sequence = [model_name] if model_name else MODELS_TO_TRY
    errors_log = []

    # 4. Looping de Redundância e Failover com Timeout de 15 segundos
    for round_num in range(1, max_rounds + 1):
        # A) Testa chaves do Gemini (Chave 1 e Chave 2)
        for idx, g_key in enumerate(gemini_keys, start=1):
            client = genai.Client(api_key=g_key)
            for candidate_model in models_sequence:
                try:
                    return _call_gemini(client, candidate_model, request_contents, timeout_seconds=timeout_per_api)
                except Exception as e:
                    errors_log.append(f"R{round_num} [Gemini Conta {idx} - {candidate_model}]: {e}")
                    # Se falhar ou timeout (>15s), tenta o próximo modelo/chave
                    continue

        # B) Alterna para Groq Cloud (Llama 3.3 70B gratuito)
        if groq_key and extracted_text:
            try:
                return _call_groq(groq_key, extracted_text, timeout_seconds=timeout_per_api)
            except Exception as e:
                errors_log.append(f"R{round_num} [Groq Llama 3.3]: {e}")

        # Intervalo breve entre ciclos de redundância
        if round_num < max_rounds:
            time.sleep(1.5)

    missing_hints = []
    if len(gemini_keys) < 2:
        missing_hints.append("adicione GEMINI_API_KEY_2 (segunda conta Google)")
    if not groq_key:
        missing_hints.append("adicione GROQ_API_KEY (chave gratuita em console.groq.com/keys)")

    dica_str = f" [Dica de contingência: {'; '.join(missing_hints)}]" if missing_hints else ""

    raise RuntimeError(
        f"Todas as tentativas de redundância falharam (Gemini e Groq).{dica_str} Detalhes dos erros: "
        + " | ".join(errors_log[-2:])
    )
