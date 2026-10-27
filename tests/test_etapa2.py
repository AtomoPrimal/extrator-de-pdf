"""
Testes da Etapa 2: consulta de existência, lançamento automático,
cadastros (Pessoas/Classificação) e regra de inativação/reativação lógica.
"""
import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app  # noqa: E402

client = TestClient(app)

NOTA_EXEMPLO = {
    "fornecedor": {"razao_social": "IGUAÇU MAQUINAS LTDA", "nome_fantasia": None, "cnpj": "11.111.111/0001-00"},
    "faturado": {"nome_completo": "BELTRANO DA SILVA", "cpf": "999.999.999-99"},
    "numero_nota": "9999",
    "data_emissao": "01/10/2026",
    "descricao_produtos": "Graxas, filtros e rolamentos",
    "quantidade_parcelas": 1,
    "data_vencimento": "01/11/2026",
    "valor_total": 2000.0,
    "classificacao_despesa": "MANUTENÇÃO E OPERAÇÃO",
    "justificativa_classificacao": "Peças de manutenção de maquinário",
    "parcelas": [{"numero": 1, "data_vencimento": "01/11/2026", "valor": 2000.0}],
}


def test_consultar_nao_existe_antes_do_lancamento():
    r = client.post("/api/consultar", json=NOTA_EXEMPLO)
    assert r.status_code == 200
    body = r.json()
    assert body["fornecedor"]["existe"] is False
    assert body["faturado"]["existe"] is False
    assert body["despesa"]["existe"] is False


def test_lancar_cria_pessoas_classificacao_e_movimento():
    r = client.post("/api/lancar", json={"nota": NOTA_EXEMPLO, "tipo_movimento": "A_PAGAR"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fornecedor_criado"] is True
    assert body["faturado_criado"] is True
    assert body["despesa_criada"] is True
    assert body["movimento"]["tipo"] == "A_PAGAR"
    assert len(body["movimento"]["parcelas"]) == 1
    assert body["movimento"]["status"] == "ATIVO"


def test_consultar_apos_lancamento_encontra_registros_existentes():
    r = client.post("/api/consultar", json=NOTA_EXEMPLO)
    body = r.json()
    assert body["fornecedor"]["existe"] is True
    assert body["faturado"]["existe"] is True
    assert body["despesa"]["existe"] is True


def test_segundo_lancamento_nao_duplica_cadastros():
    r = client.post("/api/lancar", json={"nota": NOTA_EXEMPLO, "tipo_movimento": "A_PAGAR"})
    body = r.json()
    assert body["fornecedor_criado"] is False
    assert body["faturado_criado"] is False
    assert body["despesa_criada"] is False

    pessoas = client.get("/api/pessoas").json()
    fornecedores = [p for p in pessoas if p["tipo"] == "CLIENTE_FORNECEDOR"]
    assert len(fornecedores) == 1  # não duplicou


def test_nenhum_endpoint_exclui_fisicamente_apenas_inativa_e_reativa():
    pessoas = client.get("/api/pessoas").json()
    pessoa_id = pessoas[0]["id"]

    r = client.post(f"/api/pessoas/{pessoa_id}/inativar")
    assert r.json()["status"] == "INATIVO"

    # "todos" (ATIVO) não deve trazer o registro inativado
    ativos = client.get("/api/pessoas", params={"todos": True}).json()
    assert pessoa_id not in [p["id"] for p in ativos]

    # mas continua existindo (não foi excluído)
    todos_sem_filtro = client.get("/api/pessoas").json()
    assert pessoa_id in [p["id"] for p in todos_sem_filtro]

    r = client.post(f"/api/pessoas/{pessoa_id}/reativar")
    assert r.json()["status"] == "ATIVO"


def test_crud_classificacao_basico():
    r = client.post("/api/classificacoes", json={"tipo": "RECEITA", "descricao": "VENDA DE SAFRA"})
    assert r.status_code == 200
    classificacao = r.json()

    r = client.put(f"/api/classificacoes/{classificacao['id']}", json={"descricao": "VENDA DE SAFRA - SOJA"})
    assert r.json()["descricao"] == "VENDA DE SAFRA - SOJA"

    r = client.post(f"/api/classificacoes/{classificacao['id']}/inativar")
    assert r.json()["status"] == "INATIVO"

    r = client.post(f"/api/classificacoes/{classificacao['id']}/reativar")
    assert r.json()["status"] == "ATIVO"


def test_registrar_conta_manual_com_varias_classificacoes_e_parcelas():
    c1 = client.post("/api/classificacoes", json={"tipo": "RECEITA", "descricao": "VENDA DE SOJA"}).json()
    c2 = client.post("/api/classificacoes", json={"tipo": "RECEITA", "descricao": "VENDA DE MILHO"}).json()
    cliente = client.post("/api/pessoas", json={
        "tipo": "CLIENTE_FORNECEDOR", "razao_social": "CEREALISTA XYZ LTDA",
        "documento": "22.222.222/0001-22", "tipo_documento": "CNPJ"}).json()
    payload = {
        "tipo": "A_RECEBER", "fornecedor_id": cliente["id"], "numero_nota": "CT-01",
        "valor_total": 45000.0, "classificacao_ids": [c1["id"], c2["id"]],
        "parcelas": [
            {"numero": 1, "data_vencimento": "10/03/2026", "valor": 15000.0},
            {"numero": 2, "data_vencimento": "10/09/2026", "valor": 15000.0},
            {"numero": 3, "data_vencimento": "10/03/2027", "valor": 15000.0},
        ],
    }
    r = client.post("/api/contas", json=payload)
    assert r.status_code == 200, r.text
    conta = r.json()
    assert len(conta["classificacoes"]) == 2
    assert [p["data_vencimento"] for p in conta["parcelas"]] == ["10/03/2026", "10/09/2026", "10/03/2027"]

    # edição: remove a 3ª parcela -> ela é INATIVADA, nunca excluída
    r = client.put(f"/api/contas/{conta['id']}", json={"parcelas": payload["parcelas"][:2]})
    parcelas = r.json()["parcelas"]
    assert len(parcelas) == 3
    assert [p["status"] for p in parcelas] == ["ATIVO", "ATIVO", "INATIVO"]


def test_busca_por_mais_de_um_elemento():
    r = client.get("/api/pessoas", params={"busca": "CEREALISTA 22222222"})
    assert [p["razao_social"] for p in r.json()] == ["CEREALISTA XYZ LTDA"]
    r = client.get("/api/pessoas", params={"busca": "CEREALISTA INEXISTENTE"})
    assert r.json() == []
