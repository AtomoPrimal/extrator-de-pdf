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
    "gemini-flash-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.8-flash",
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


def _call_deepseek(deepseek_key: str, text: str, timeout_seconds: float = 15.0) -> NotaFiscalExtracao:
    """Executa a extração via DeepSeek (failover redundante) com timeout rígido."""
    headers = {
        "Authorization": f"Bearer {deepseek_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
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
        resp = http_client.post("https://api.deepseek.com/chat/completions", headers=headers, json=payload)
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
    Extrai dados da nota fiscal com redundância e failover entre Gemini e DeepSeek.
    Se uma API demorar mais que 15 segundos ou falhar, alterna imediatamente para a outra.
    """
    # 1. Recupera chaves de ambiente
    gemini_key = None
    if api_key and api_key.strip():
        gemini_key = api_key.strip().strip('"').strip("'")
    else:
        for var_name in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_KEY", "API_KEY", "gemini_api_key"]:
            val = os.getenv(var_name)
            if val and val.strip():
                gemini_key = val.strip().strip('"').strip("'")
                break

    deepseek_key = None
    for var_name in ["DEEP_SEEK_API_KEY", "DEEPSEEK_API_KEY", "DEEPSEEK_KEY"]:
        val = os.getenv(var_name)
        if val and val.strip():
            deepseek_key = val.strip().strip('"').strip("'")
            break

    if not gemini_key and not deepseek_key:
        raise ValueError(
            "Nenhuma chave de API encontrada. Defina GEMINI_API_KEY ou DEEP_SEEK_API_KEY no arquivo .env."
        )

    # 2. Extrai texto local do PDF para agilidade máxima
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

    # 3. Looping de Redundância e Failover com Timeout de 15 segundos
    for round_num in range(1, max_rounds + 1):
        # A) Tenta Gemini (com limite de 15 segundos por modelo)
        if gemini_key:
            client = genai.Client(api_key=gemini_key)
            for candidate_model in models_sequence:
                try:
                    return _call_gemini(client, candidate_model, request_contents, timeout_seconds=timeout_per_api)
                except Exception as e:
                    errors_log.append(f"Tentativa {round_num} [Gemini - {candidate_model}]: {e}")
                    # Se o erro for de timeout ou 503, tenta o próximo modelo Gemini
                    continue

        # B) Alterna para DeepSeek (com limite de 15 segundos)
        if deepseek_key and extracted_text:
            try:
                return _call_deepseek(deepseek_key, extracted_text, timeout_seconds=timeout_per_api)
            except httpx.HTTPStatusError as hse:
                if hse.response.status_code == 402:
                    errors_log.append("Tentativa " + str(round_num) + " [DeepSeek]: Saldo insuficiente na conta (402 Payment Required). Recarregue creditos na plataforma da DeepSeek.")
                else:
                    errors_log.append(f"Tentativa {round_num} [DeepSeek]: {hse}")
            except Exception as e:
                errors_log.append(f"Tentativa {round_num} [DeepSeek]: {e}")

        # Intervalo breve entre ciclos de failover
        if round_num < max_rounds:
            time.sleep(2.0)

    raise RuntimeError(
        "Todas as tentativas de redundância falharam (Gemini e DeepSeek). Detalhes dos erros: "
        + " | ".join(errors_log[-2:])
    )
