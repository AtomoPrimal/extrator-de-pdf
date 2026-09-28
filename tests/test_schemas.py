import pytest
from pydantic import ValidationError

def test_nota_fiscal_extracao_schema():
    from app.schemas import NotaFiscalExtracao, Fornecedor, Faturado, Parcela

    sample_data = {
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
        "descricao_produtos": "Graxa de poliureia, anel o, kit da bucha, apoio, rolamentos, estopa, pano para limpeza, limpador premium",
        "quantidade_parcelas": 1,
        "data_vencimento": "17/10/2025",
        "valor_total": 3086.75,
        "classificacao_despesa": "MANUTENÇÃO E OPERAÇÃO",
        "justificativa_classificacao": "Itens são peças de reposição e lubrificantes agrícolas",
        "parcelas": [
            {
                "numero": 1,
                "data_vencimento": "17/10/2025",
                "valor": 3086.75
            }
        ]
    }

    nota = NotaFiscalExtracao(**sample_data)
    assert nota.fornecedor.razao_social == "IGUACU MAQUINAS AGRICOLAS LTDA"
    assert nota.faturado.cpf == "999.999.999-99"
    assert nota.classificacao_despesa == "MANUTENÇÃO E OPERAÇÃO"
    assert len(nota.parcelas) == 1
    assert nota.valor_total == 3086.75
