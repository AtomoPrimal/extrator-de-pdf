"""
Modelos ORM (SQLAlchemy) — Etapa 2 do Projeto Administrativo-Financeiro.

Entidades (conforme "Documentação entrega 2.pdf"):
- PESSOAS            -> tipo: CLIENTE_FORNECEDOR | FATURADO   (Manter Fornecedor / Manter Cliente / Manter Faturado)
- CLASSIFICACAO      -> tipo: DESPESA | RECEITA               (Manter Tipo de Despesa / Manter Tipo de Receita)
- MOVIMENTOCONTAS    -> tipo: A_PAGAR | A_RECEBER              (Registrar Contas a Pagar / Registrar Contas a Receber)
- PARCELACONTAS      -> parcelas de um MOVIMENTOCONTAS, com vencimento e valor próprios

Regra de negócio: nenhum registro é excluído fisicamente. Toda remoção é uma
inativação lógica (status = INATIVO), sempre reversível (status = ATIVO).
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Integer, String, Table, Text,
)
from sqlalchemy.orm import relationship

from app.database import Base

STATUS_ATIVO = "ATIVO"
STATUS_INATIVO = "INATIVO"

TIPO_PESSOA_CLIENTE_FORNECEDOR = "CLIENTE_FORNECEDOR"
TIPO_PESSOA_FATURADO = "FATURADO"

TIPO_CLASSIFICACAO_DESPESA = "DESPESA"
TIPO_CLASSIFICACAO_RECEITA = "RECEITA"

TIPO_MOVIMENTO_A_PAGAR = "A_PAGAR"
TIPO_MOVIMENTO_A_RECEBER = "A_RECEBER"


# Tabela associativa: um lançamento pode ter uma ou mais classificações
# (uma ou mais DESPESAS para contas a pagar, uma ou mais RECEITAS para contas a receber).
movimento_classificacao = Table(
    "movimento_classificacao",
    Base.metadata,
    Column("movimento_id", Integer, ForeignKey("movimento_contas.id"), primary_key=True),
    Column("classificacao_id", Integer, ForeignKey("classificacao.id"), primary_key=True),
)


class Pessoa(Base):
    __tablename__ = "pessoas"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(30), nullable=False, index=True)  # CLIENTE_FORNECEDOR | FATURADO
    razao_social = Column(String(255), nullable=False)
    nome_fantasia = Column(String(255), nullable=True)
    documento = Column(String(20), nullable=False, index=True)  # CNPJ (fornecedor/cliente) ou CPF (faturado)
    tipo_documento = Column(String(4), nullable=False, default="CNPJ")  # CNPJ | CPF
    email = Column(String(255), nullable=True)
    telefone = Column(String(30), nullable=True)
    status = Column(String(10), nullable=False, default=STATUS_ATIVO, index=True)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    atualizado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    movimentos_fornecedor = relationship(
        "MovimentoContas", back_populates="fornecedor", foreign_keys="MovimentoContas.fornecedor_id"
    )
    movimentos_faturado = relationship(
        "MovimentoContas", back_populates="faturado", foreign_keys="MovimentoContas.faturado_id"
    )


class Classificacao(Base):
    __tablename__ = "classificacao"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(10), nullable=False, index=True)  # DESPESA | RECEITA
    descricao = Column(String(255), nullable=False, index=True)
    status = Column(String(10), nullable=False, default=STATUS_ATIVO, index=True)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    atualizado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    movimentos = relationship(
        "MovimentoContas", secondary=movimento_classificacao, back_populates="classificacoes"
    )


class MovimentoContas(Base):
    __tablename__ = "movimento_contas"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(12), nullable=False, index=True)  # A_PAGAR | A_RECEBER

    fornecedor_id = Column(Integer, ForeignKey("pessoas.id"), nullable=True)
    faturado_id = Column(Integer, ForeignKey("pessoas.id"), nullable=True)

    numero_nota = Column(String(50), nullable=True)
    data_emissao = Column(String(10), nullable=True)  # DD/MM/AAAA
    descricao_produtos = Column(Text, nullable=True)
    valor_total = Column(Float, nullable=False, default=0.0)

    status = Column(String(10), nullable=False, default=STATUS_ATIVO, index=True)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    atualizado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    fornecedor = relationship("Pessoa", back_populates="movimentos_fornecedor", foreign_keys=[fornecedor_id])
    faturado = relationship("Pessoa", back_populates="movimentos_faturado", foreign_keys=[faturado_id])
    classificacoes = relationship(
        "Classificacao", secondary=movimento_classificacao, back_populates="movimentos"
    )
    parcelas = relationship(
        "ParcelaContas", back_populates="movimento", cascade="all, delete-orphan", order_by="ParcelaContas.numero"
    )


class ParcelaContas(Base):
    __tablename__ = "parcela_contas"

    id = Column(Integer, primary_key=True, index=True)
    movimento_id = Column(Integer, ForeignKey("movimento_contas.id"), nullable=False)
    numero = Column(Integer, nullable=False, default=1)
    identificacao = Column(String(60), nullable=False, unique=True, index=True)  # identificação única da parcela
    data_vencimento = Column(String(10), nullable=True)  # DD/MM/AAAA
    valor = Column(Float, nullable=False, default=0.0)
    status = Column(String(10), nullable=False, default=STATUS_ATIVO, index=True)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    movimento = relationship("MovimentoContas", back_populates="parcelas")
