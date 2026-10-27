
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
    nome_fantasia: str | None = Field(default=None, description="Nome Fantasia do Fornecedor")
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
    justificativa_classificacao: str | None = Field(
        default=None,
        description="Breve justificativa do motivo pelo qual a LLM atribuiu essa classificação de despesa"
    )
    parcelas: list[Parcela] = Field(
        default_factory=list,
        description="Lista de parcelas com seus respectivos vencimentos e valores"
    )


# ==========================================================================
# ETAPA 2 — Schemas de persistência (PESSOAS, CLASSIFICAÇÃO, CONTAS)
# ==========================================================================

TIPO_PESSOA_CLIENTE_FORNECEDOR = "CLIENTE_FORNECEDOR"
TIPO_PESSOA_FATURADO = "FATURADO"
TIPOS_PESSOA_VALIDOS = [TIPO_PESSOA_CLIENTE_FORNECEDOR, TIPO_PESSOA_FATURADO]

TIPO_CLASSIFICACAO_DESPESA = "DESPESA"
TIPO_CLASSIFICACAO_RECEITA = "RECEITA"
TIPOS_CLASSIFICACAO_VALIDOS = [TIPO_CLASSIFICACAO_DESPESA, TIPO_CLASSIFICACAO_RECEITA]

TIPO_MOVIMENTO_A_PAGAR = "A_PAGAR"
TIPO_MOVIMENTO_A_RECEBER = "A_RECEBER"
TIPOS_MOVIMENTO_VALIDOS = [TIPO_MOVIMENTO_A_PAGAR, TIPO_MOVIMENTO_A_RECEBER]


class PessoaBase(BaseModel):
    tipo: str = Field(description="CLIENTE_FORNECEDOR (Fornecedor/Cliente) ou FATURADO")
    razao_social: str = Field(description="Razão Social (PJ) ou Nome Completo (PF)")
    nome_fantasia: str | None = Field(default=None, description="Nome Fantasia (quando aplicável)")
    documento: str = Field(description="CNPJ ou CPF (somente dígitos ou formatado)")
    tipo_documento: str = Field(default="CNPJ", description="CNPJ ou CPF")
    email: str | None = None
    telefone: str | None = None


class PessoaCreate(PessoaBase):
    pass


class PessoaUpdate(BaseModel):
    razao_social: str | None = None
    nome_fantasia: str | None = None
    documento: str | None = None
    tipo_documento: str | None = None
    email: str | None = None
    telefone: str | None = None


class PessoaOut(PessoaBase):
    id: int
    status: str

    model_config = {"from_attributes": True}


class ClassificacaoBase(BaseModel):
    tipo: str = Field(description="DESPESA ou RECEITA")
    descricao: str = Field(description="Descrição da classificação. Ex: MANUTENÇÃO E OPERAÇÃO")


class ClassificacaoCreate(ClassificacaoBase):
    pass


class ClassificacaoUpdate(BaseModel):
    descricao: str | None = None


class ClassificacaoOut(ClassificacaoBase):
    id: int
    status: str

    model_config = {"from_attributes": True}


class ParcelaOut(BaseModel):
    id: int
    numero: int
    identificacao: str
    data_vencimento: str | None = None
    valor: float
    status: str

    model_config = {"from_attributes": True}


class MovimentoOut(BaseModel):
    id: int
    tipo: str
    numero_nota: str | None = None
    data_emissao: str | None = None
    descricao_produtos: str | None = None
    valor_total: float
    status: str
    fornecedor: PessoaOut | None = None
    faturado: PessoaOut | None = None
    classificacoes: list[ClassificacaoOut] = Field(default_factory=list)
    parcelas: list[ParcelaOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ParcelaIn(BaseModel):
    numero: int | None = None
    data_vencimento: str | None = None
    valor: float = 0.0


class MovimentoCreate(BaseModel):
    """Registro manual de Conta a Pagar / Conta a Receber."""
    tipo: str = Field(description="A_PAGAR ou A_RECEBER")
    fornecedor_id: int | None = Field(default=None, description="Fornecedor (a pagar) ou Cliente (a receber)")
    faturado_id: int | None = None
    numero_nota: str | None = None
    data_emissao: str | None = None
    descricao_produtos: str | None = None
    valor_total: float = 0.0
    classificacao_ids: list[int] = Field(default_factory=list, description="Uma ou mais classificações")
    parcelas: list[ParcelaIn] = Field(default_factory=list, description="Uma ou mais parcelas")


class MovimentoUpdate(BaseModel):
    fornecedor_id: int | None = None
    faturado_id: int | None = None
    numero_nota: str | None = None
    data_emissao: str | None = None
    descricao_produtos: str | None = None
    valor_total: float | None = None
    classificacao_ids: list[int] | None = None
    parcelas: list[ParcelaIn] | None = None


class ConsultaItemResultado(BaseModel):
    """Resultado da consulta de existência de uma entidade no banco (tela de confirmação)."""
    entidade: str  # FORNECEDOR | FATURADO | DESPESA
    identificador: str
    documento: str | None = None
    existe: bool
    id: int | None = None


class ConsultaResultado(BaseModel):
    fornecedor: ConsultaItemResultado
    faturado: ConsultaItemResultado
    despesa: ConsultaItemResultado


class LancarContaRequest(BaseModel):
    """Corpo enviado ao confirmar o lançamento após a extração + consulta."""
    nota: NotaFiscalExtracao
    tipo_movimento: str = Field(
        default=TIPO_MOVIMENTO_A_PAGAR,
        description="A_PAGAR ou A_RECEBER"
    )


class LancarContaResponse(BaseModel):
    mensagem: str
    fornecedor_criado: bool
    faturado_criado: bool
    despesa_criada: bool
    movimento: MovimentoOut
