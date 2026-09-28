from typing import List, Optional
from pydantic import BaseModel, Field

CATEGORIAS_DESPESA_VALIDAS = [
    "INSUMOS AGRÍCOLAS",
    "MANUTENÇÃO E OPERAÇÃO",
    "RECURSOS HUMANOS",
    "SERVIÇOS OPERACIONAIS",
    "INFRAESTRUTURA E UTILIDADES",
    "ADMINISTRATIVAS",
    "SEGUROS E PROTEÇÃO",
    "IMPOSTOS E TAXAS",
    "INVESTIMENTOS"
]

class Fornecedor(BaseModel):
    razao_social: str = Field(description="Razão Social do Fornecedor/Emitente")
    nome_fantasia: Optional[str] = Field(default=None, description="Nome Fantasia do Fornecedor")
    cnpj: str = Field(description="CNPJ do Fornecedor")

class Faturado(BaseModel):
    nome_completo: str = Field(description="Nome Completo do Faturado/Destinatário")
    cpf: str = Field(description="CPF do Faturado")

class Parcela(BaseModel):
    numero: int = Field(default=1, description="Número da parcela")
    data_vencimento: str = Field(description="Data de vencimento da parcela (DD/MM/AAAA)")
    valor: float = Field(description="Valor da parcela em Reais (R$)")

class NotaFiscalExtracao(BaseModel):
    fornecedor: Fornecedor
    faturado: Faturado
    numero_nota: str = Field(description="Número da Nota Fiscal")
    data_emissao: str = Field(description="Data de emissão da Nota Fiscal (DD/MM/AAAA)")
    descricao_produtos: str = Field(description="Descrição resumida ou lista consolidada dos produtos da nota fiscal")
    quantidade_parcelas: int = Field(default=1, description="Quantidade total de parcelas")
    data_vencimento: str = Field(description="Data de vencimento principal ou da primeira parcela (DD/MM/AAAA)")
    valor_total: float = Field(description="Valor total da nota fiscal em Reais (R$)")
    classificacao_despesa: str = Field(
        description="Classificação da despesa inferida via IA com base nos produtos. Ex: MANUTENÇÃO E OPERAÇÃO, INSUMOS AGRÍCOLAS, etc."
    )
    justificativa_classificacao: Optional[str] = Field(
        default=None,
        description="Breve justificativa do motivo pelo qual a LLM atribuiu essa classificação de despesa"
    )
    parcelas: List[Parcela] = Field(
        default_factory=list,
        description="Lista de parcelas com seus respectivos vencimentos e valores"
    )
