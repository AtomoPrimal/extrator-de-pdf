from unittest.mock import patch

from fastapi.testclient import TestClient

from app.schemas import NotaFiscalExtracao


def test_api_health():
    from app.main import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_api_home_page():
    from app.main import app
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Extração de Dados de Nota Fiscal" in response.text
    assert "EXTRAIR DADOS" in response.text

def test_api_extract_rejects_non_pdf():
    from app.main import app
    client = TestClient(app)
    response = client.post(
        "/api/extrair",
        files={"file": ("test.txt", b"Texto qualquer", "text/plain")}
    )
    assert response.status_code == 400
    assert "apenas arquivos pdf" in response.json()["detail"].lower()

def test_api_extract_success_mock():
    from app.main import app
    client = TestClient(app)

    mock_nota = NotaFiscalExtracao(
        fornecedor={
            "razao_social": "IGUACU MAQUINAS AGRICOLAS LTDA",
            "nome_fantasia": "IGUACU",
            "cnpj": "33.656.729/0023-85"
        },
        faturado={
            "nome_completo": "CICLANO DA SILVA",
            "cpf": "999.999.999-99"
        },
        numero_nota="000.084.682",
        data_emissao="19/09/2025",
        descricao_produtos="Peças e graxa",
        quantidade_parcelas=1,
        data_vencimento="17/10/2025",
        valor_total=3086.75,
        classificacao_despesa="MANUTENÇÃO E OPERAÇÃO",
        justificativa_classificacao="Lubrificantes e peças agrícolas",
        parcelas=[{"numero": 1, "data_vencimento": "17/10/2025", "valor": 3086.75}]
    )

    with patch("app.main.extract_invoice_data", return_value=mock_nota):
        response = client.post(
            "/api/extrair",
            files={"file": ("danfe.pdf", b"%PDF-1.4 dummy", "application/pdf")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["fornecedor"]["razao_social"] == "IGUACU MAQUINAS AGRICOLAS LTDA"
        assert data["classificacao_despesa"] == "MANUTENÇÃO E OPERAÇÃO"
        assert data["valor_total"] == 3086.75
