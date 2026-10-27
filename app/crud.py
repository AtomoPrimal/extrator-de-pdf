"""
Operações de banco de dados (CRUD) para as entidades da Etapa 2.

Regra de negócio aplicada em todo o módulo: nenhum registro é excluído
fisicamente. "Excluir" = marcar status = INATIVO. "Reativar" = voltar para ATIVO.
"""
import re
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, aliased

from app import models


def _only_digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _termos(busca: Optional[str]) -> list[str]:
    """Busca por mais de um elemento: separa por espaço, vírgula ou ponto-e-vírgula.
    Cada termo deve casar com ao menos uma coluna (AND entre termos)."""
    return [t for t in re.split(r"[\s,;]+", (busca or "").strip()) if t]


# --------------------------------------------------------------------------
# PESSOAS (Fornecedor / Cliente / Faturado)
# --------------------------------------------------------------------------

def buscar_pessoa_por_documento(db: Session, documento: str, tipo: Optional[str] = None) -> Optional[models.Pessoa]:
    doc = _only_digits(documento)
    if not doc:
        return None
    query = db.query(models.Pessoa).filter(models.Pessoa.documento == doc)
    if tipo:
        query = query.filter(models.Pessoa.tipo == tipo)
    return query.first()


def criar_pessoa(db: Session, dados: dict) -> models.Pessoa:
    dados = dict(dados)
    if dados.get("documento"):
        dados["documento"] = _only_digits(dados["documento"])
    dados["status"] = models.STATUS_ATIVO
    pessoa = models.Pessoa(**dados)
    db.add(pessoa)
    db.commit()
    db.refresh(pessoa)
    return pessoa


def listar_pessoas(
    db: Session, tipo: Optional[str] = None, termo: Optional[str] = None, apenas_ativos: bool = False
):
    query = db.query(models.Pessoa)
    if tipo:
        query = query.filter(models.Pessoa.tipo == tipo)
    if apenas_ativos:
        query = query.filter(models.Pessoa.status == models.STATUS_ATIVO)
    for t in _termos(termo):
        termo_doc = _only_digits(t)
        filtros = [
            models.Pessoa.razao_social.ilike(f"%{t}%"),
            models.Pessoa.nome_fantasia.ilike(f"%{t}%"),
            models.Pessoa.email.ilike(f"%{t}%"),
            models.Pessoa.telefone.ilike(f"%{t}%"),
        ]
        if termo_doc:
            filtros.append(models.Pessoa.documento.ilike(f"%{termo_doc}%"))
        query = query.filter(or_(*filtros))
    return query.order_by(models.Pessoa.razao_social).all()


def obter_pessoa(db: Session, pessoa_id: int) -> Optional[models.Pessoa]:
    return db.query(models.Pessoa).filter(models.Pessoa.id == pessoa_id).first()


def atualizar_pessoa(db: Session, pessoa_id: int, dados: dict) -> Optional[models.Pessoa]:
    pessoa = obter_pessoa(db, pessoa_id)
    if not pessoa:
        return None
    dados = dict(dados)
    dados.pop("status", None)  # status não é editável via update comum (recomendação de layout)
    if dados.get("documento"):
        dados["documento"] = _only_digits(dados["documento"])
    for campo, valor in dados.items():
        if valor is not None:
            setattr(pessoa, campo, valor)
    db.commit()
    db.refresh(pessoa)
    return pessoa


def inativar_pessoa(db: Session, pessoa_id: int) -> Optional[models.Pessoa]:
    pessoa = obter_pessoa(db, pessoa_id)
    if not pessoa:
        return None
    pessoa.status = models.STATUS_INATIVO
    db.commit()
    db.refresh(pessoa)
    return pessoa


def reativar_pessoa(db: Session, pessoa_id: int) -> Optional[models.Pessoa]:
    pessoa = obter_pessoa(db, pessoa_id)
    if not pessoa:
        return None
    pessoa.status = models.STATUS_ATIVO
    db.commit()
    db.refresh(pessoa)
    return pessoa


# --------------------------------------------------------------------------
# CLASSIFICAÇÃO (Tipo de Despesa / Tipo de Receita)
# --------------------------------------------------------------------------

def buscar_classificacao_por_descricao(db: Session, descricao: str, tipo: Optional[str] = None):
    if not descricao:
        return None
    query = db.query(models.Classificacao).filter(models.Classificacao.descricao.ilike(descricao.strip()))
    if tipo:
        query = query.filter(models.Classificacao.tipo == tipo)
    return query.first()


def criar_classificacao(db: Session, dados: dict) -> models.Classificacao:
    dados = dict(dados)
    dados["status"] = models.STATUS_ATIVO
    classificacao = models.Classificacao(**dados)
    db.add(classificacao)
    db.commit()
    db.refresh(classificacao)
    return classificacao


def listar_classificacoes(
    db: Session, tipo: Optional[str] = None, termo: Optional[str] = None, apenas_ativos: bool = False
):
    query = db.query(models.Classificacao)
    if tipo:
        query = query.filter(models.Classificacao.tipo == tipo)
    if apenas_ativos:
        query = query.filter(models.Classificacao.status == models.STATUS_ATIVO)
    for t in _termos(termo):
        query = query.filter(models.Classificacao.descricao.ilike(f"%{t}%"))
    return query.order_by(models.Classificacao.descricao).all()


def obter_classificacao(db: Session, classificacao_id: int):
    return db.query(models.Classificacao).filter(models.Classificacao.id == classificacao_id).first()


def atualizar_classificacao(db: Session, classificacao_id: int, dados: dict):
    classificacao = obter_classificacao(db, classificacao_id)
    if not classificacao:
        return None
    dados = dict(dados)
    dados.pop("status", None)
    for campo, valor in dados.items():
        if valor is not None:
            setattr(classificacao, campo, valor)
    db.commit()
    db.refresh(classificacao)
    return classificacao


def inativar_classificacao(db: Session, classificacao_id: int):
    classificacao = obter_classificacao(db, classificacao_id)
    if not classificacao:
        return None
    classificacao.status = models.STATUS_INATIVO
    db.commit()
    db.refresh(classificacao)
    return classificacao


def reativar_classificacao(db: Session, classificacao_id: int):
    classificacao = obter_classificacao(db, classificacao_id)
    if not classificacao:
        return None
    classificacao.status = models.STATUS_ATIVO
    db.commit()
    db.refresh(classificacao)
    return classificacao


# --------------------------------------------------------------------------
# MOVIMENTO DE CONTAS (Contas a Pagar / Contas a Receber) + PARCELAS
# --------------------------------------------------------------------------

def criar_movimento(
    db: Session,
    tipo: str,
    fornecedor_id: Optional[int],
    faturado_id: Optional[int],
    numero_nota: Optional[str],
    data_emissao: Optional[str],
    descricao_produtos: Optional[str],
    valor_total: float,
    classificacao_ids: list[int],
    parcelas: list[dict],
) -> models.MovimentoContas:
    movimento = models.MovimentoContas(
        tipo=tipo,
        fornecedor_id=fornecedor_id,
        faturado_id=faturado_id,
        numero_nota=numero_nota,
        data_emissao=data_emissao,
        descricao_produtos=descricao_produtos,
        valor_total=valor_total,
        status=models.STATUS_ATIVO,
    )
    if classificacao_ids:
        movimento.classificacoes = (
            db.query(models.Classificacao).filter(models.Classificacao.id.in_(classificacao_ids)).all()
        )
    db.add(movimento)
    db.flush()  # garante movimento.id antes de criar as parcelas

    for idx, parcela in enumerate(parcelas or [], start=1):
        identificacao = f"MOV{movimento.id}-P{parcela.get('numero', idx)}"
        db.add(
            models.ParcelaContas(
                movimento_id=movimento.id,
                numero=parcela.get("numero", idx),
                identificacao=identificacao,
                data_vencimento=parcela.get("data_vencimento"),
                valor=parcela.get("valor", 0.0),
                status=models.STATUS_ATIVO,
            )
        )

    db.commit()
    db.refresh(movimento)
    return movimento


def listar_movimentos(
    db: Session, tipo: Optional[str] = None, termo: Optional[str] = None, apenas_ativos: bool = False
):
    query = db.query(models.MovimentoContas)
    if tipo:
        query = query.filter(models.MovimentoContas.tipo == tipo)
    if apenas_ativos:
        query = query.filter(models.MovimentoContas.status == models.STATUS_ATIVO)
    termos = _termos(termo)
    if termos:
        Fornecedor = aliased(models.Pessoa)
        Faturado = aliased(models.Pessoa)
        query = (
            query.outerjoin(Fornecedor, models.MovimentoContas.fornecedor_id == Fornecedor.id)
            .outerjoin(Faturado, models.MovimentoContas.faturado_id == Faturado.id)
        )
        for t in termos:
            termo_doc = _only_digits(t)
            filtros = [
                models.MovimentoContas.numero_nota.ilike(f"%{t}%"),
                models.MovimentoContas.descricao_produtos.ilike(f"%{t}%"),
                Fornecedor.razao_social.ilike(f"%{t}%"),
                Faturado.razao_social.ilike(f"%{t}%"),
            ]
            if termo_doc:
                filtros.append(Fornecedor.documento.ilike(f"%{termo_doc}%"))
                filtros.append(Faturado.documento.ilike(f"%{termo_doc}%"))
            query = query.filter(or_(*filtros))
    return query.order_by(models.MovimentoContas.id.desc()).all()


def obter_movimento(db: Session, movimento_id: int):
    return db.query(models.MovimentoContas).filter(models.MovimentoContas.id == movimento_id).first()


def atualizar_movimento(
    db: Session,
    movimento_id: int,
    dados: dict,
    classificacao_ids: Optional[list[int]] = None,
    parcelas: Optional[list[dict]] = None,
):
    """Atualiza um lançamento. Parcelas removidas são INATIVADAS (nunca excluídas)."""
    movimento = obter_movimento(db, movimento_id)
    if not movimento:
        return None
    dados = dict(dados)
    dados.pop("status", None)
    for campo, valor in dados.items():
        if valor is not None:
            setattr(movimento, campo, valor)

    if classificacao_ids is not None:
        movimento.classificacoes = (
            db.query(models.Classificacao).filter(models.Classificacao.id.in_(classificacao_ids)).all()
        )

    if parcelas is not None:
        existentes = {p.numero: p for p in movimento.parcelas}
        recebidos = set()
        for idx, parcela in enumerate(parcelas, start=1):
            numero = parcela.get("numero") or idx
            recebidos.add(numero)
            if numero in existentes:
                p = existentes[numero]
                p.data_vencimento = parcela.get("data_vencimento")
                p.valor = parcela.get("valor", 0.0)
                p.status = models.STATUS_ATIVO
            else:
                db.add(models.ParcelaContas(
                    movimento_id=movimento.id,
                    numero=numero,
                    identificacao=f"MOV{movimento.id}-P{numero}",
                    data_vencimento=parcela.get("data_vencimento"),
                    valor=parcela.get("valor", 0.0),
                    status=models.STATUS_ATIVO,
                ))
        for numero, p in existentes.items():
            if numero not in recebidos:
                p.status = models.STATUS_INATIVO

    db.commit()
    db.refresh(movimento)
    return movimento


def inativar_movimento(db: Session, movimento_id: int):
    movimento = obter_movimento(db, movimento_id)
    if not movimento:
        return None
    movimento.status = models.STATUS_INATIVO
    for parcela in movimento.parcelas:
        parcela.status = models.STATUS_INATIVO
    db.commit()
    db.refresh(movimento)
    return movimento


def reativar_movimento(db: Session, movimento_id: int):
    movimento = obter_movimento(db, movimento_id)
    if not movimento:
        return None
    movimento.status = models.STATUS_ATIVO
    for parcela in movimento.parcelas:
        parcela.status = models.STATUS_ATIVO
    db.commit()
    db.refresh(movimento)
    return movimento
