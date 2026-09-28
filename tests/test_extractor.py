import pytest
from unittest.mock import MagicMock, patch
from app.schemas import NotaFiscalExtracao

def test_extract_invoice_data_raises_without_api_key():
    from app.extractor import extract_invoice_data
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            extract_invoice_data(b"%PDF-1.4 mock content", api_key=None)

def test_extract_invoice_data_success_mock():
    from app.extractor import extract_invoice_data

    mock_json = """
    {
        "fornecedor": {
            "razao_social": "IGUACU MAQUINAS AGRICOLAS LTDA",
            "nome_fantasia": "IGUACU MAQUINAS",
            "cnpj": "33.656.729/0023-85"
        },
        "faturado": {
            "nome_completo": "CICLANO DA SILVA",
            "cpf": "999.999.999-99"
        },
        "numero_nota": "000.084.682",
        "data_emissao": "19/09/2025",
        "descricao_produtos": "Graxa, retentor, rolamentos",
        "quantidade_parcelas": 1,
        "data_vencimento": "17/10/2025",
        "valor_total": 3086.75,
        "classificacao_despesa": "MANUTENÇÃO E OPERAÇÃO",
        "justificativa_classificacao": "Peças e graxas agrícolas",
        "parcelas": [
            {
                "numero": 1,
                "data_vencimento": "17/10/2025",
                "valor": 3086.75
            }
        ]
    }
    """

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = mock_json
    mock_client.models.generate_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client):
        result = extract_invoice_data(b"%PDF-1.4 test", api_key="test-api-key")
        assert isinstance(result, NotaFiscalExtracao)
        assert result.fornecedor.cnpj == "33.656.729/0023-85"
        assert result.classificacao_despesa == "MANUTENÇÃO E OPERAÇÃO"
        assert result.valor_total == 3086.75
