import os
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import crud, models
from app.auth import (
    COOKIE_NAME,
    LoginObrigatorioMiddleware,
    gerar_token,
    usuario_do_token,
    validar_credenciais,
)
from app.database import get_db, init_db
from app.versao import obter_versao
from app.extractor import extract_invoice_data
from app.schemas import (
    ClassificacaoCreate,
    ClassificacaoOut,
    ClassificacaoUpdate,
    ConsultaItemResultado,
    ConsultaResultado,
    LancarContaRequest,
    LancarContaResponse,
    MovimentoCreate,
    MovimentoOut,
    MovimentoUpdate,
    NotaFiscalExtracao,
    PessoaCreate,
    PessoaOut,
    PessoaUpdate,
    TIPO_CLASSIFICACAO_DESPESA,
    TIPO_MOVIMENTO_A_PAGAR,
    TIPO_PESSOA_CLIENTE_FORNECEDOR,
    TIPO_PESSOA_FATURADO,
)

app = FastAPI(
    title="Projeto Administrativo-Financeiro — Extrator de Notas com LLM",
    description="Extração de dados de notas fiscais via IA + cadastros e lançamentos financeiros (Etapa 2)",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoginObrigatorioMiddleware)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


# Garante a criação das tabelas assim que o app é importado (deploy, testes, etc.).
init_db()


@app.get("/health")
async def health_check():
    """Endpoint de verificação de integridade para o Render."""
    return {"status": "ok"}


@app.get("/login", response_class=HTMLResponse)
async def tela_login(erro: int = 0):
    html = (TEMPLATES_DIR / "login.html").read_text(encoding="utf-8")
    versao = obter_versao()
    html = html.replace("{{ERRO}}", "Usuário ou senha inválidos." if erro else "")
    html = html.replace("{{COMMIT}}", versao["commit_curto"])
    return HTMLResponse(content=html)


@app.post("/login")
async def efetuar_login(
    usuario: Annotated[str, Form()],
    senha: Annotated[str, Form()],
):
    if not validar_credenciais(usuario, senha):
        return RedirectResponse(url="/login?erro=1", status_code=303)
    resposta = RedirectResponse(url="/", status_code=303)
    resposta.set_cookie(COOKIE_NAME, gerar_token(usuario), httponly=True, samesite="lax", max_age=60 * 60 * 12)
    return resposta


@app.get("/logout")
async def efetuar_logout():
    resposta = RedirectResponse(url="/login", status_code=303)
    resposta.delete_cookie(COOKIE_NAME)
    return resposta


@app.get("/api/versao")
async def api_versao(request: Request):
    """Código (hash do commit) da última atualização no GitHub — exibido na tela principal."""
    dados = obter_versao()
    dados["usuario"] = usuario_do_token(request.cookies.get(COOKIE_NAME))
    return dados


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Renderiza a interface gráfica web."""
    html_file = TEMPLATES_DIR / "index.html"
    if not html_file.exists():
        raise HTTPException(status_code=500, detail="Template index.html não encontrado.")
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@app.post("/api/extrair", response_model=NotaFiscalExtracao)
async def extrair_nota(
    file: Annotated[UploadFile, File(description="Arquivo PDF da Nota Fiscal")],
    api_key: Annotated[str | None, Form(description="Chave de API Gemini opcional")] = None,
):
    """
    Recebe um arquivo PDF de nota fiscal e extrai os dados estruturados usando Gemini.
    (1ª Etapa — apenas extração, sem persistência.)
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Arquivo inválido. Por favor, envie apenas arquivos PDF (.pdf)."
        )

    try:
        pdf_bytes = await file.read()
        if not pdf_bytes or len(pdf_bytes) == 0:
            raise HTTPException(status_code=400, detail="O arquivo PDF enviado está vazio.")

        resultado = extract_invoice_data(pdf_bytes, api_key=api_key)
        return resultado
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao processar documento com Gemini: {e!s}"
        )


# ==========================================================================
# ETAPA 2 — Consulta de existência + Lançamento automático
# ==========================================================================

@app.post("/api/consultar", response_model=ConsultaResultado)
async def consultar_existencia(nota: NotaFiscalExtracao, db: Session = Depends(get_db)):
    """
    Após a extração, consulta no banco se FORNECEDOR, FATURADO e DESPESA já existem.
    """
    fornecedor_db = crud.buscar_pessoa_por_documento(
        db, nota.fornecedor.cnpj, tipo=TIPO_PESSOA_CLIENTE_FORNECEDOR
    )
    faturado_db = crud.buscar_pessoa_por_documento(
        db, nota.faturado.cpf, tipo=TIPO_PESSOA_FATURADO
    )
    despesa_db = crud.buscar_classificacao_por_descricao(
        db, nota.classificacao_despesa, tipo=TIPO_CLASSIFICACAO_DESPESA
    )

    return ConsultaResultado(
        fornecedor=ConsultaItemResultado(
            entidade="FORNECEDOR",
            identificador=nota.fornecedor.razao_social,
            documento=nota.fornecedor.cnpj,
            existe=fornecedor_db is not None,
            id=fornecedor_db.id if fornecedor_db else None,
        ),
        faturado=ConsultaItemResultado(
            entidade="FATURADO",
            identificador=nota.faturado.nome_completo,
            documento=nota.faturado.cpf,
            existe=faturado_db is not None,
            id=faturado_db.id if faturado_db else None,
        ),
        despesa=ConsultaItemResultado(
            entidade="DESPESA",
            identificador=nota.classificacao_despesa,
            documento=None,
            existe=despesa_db is not None,
            id=despesa_db.id if despesa_db else None,
        ),
    )


@app.post("/api/lancar", response_model=LancarContaResponse)
async def lancar_conta(payload: LancarContaRequest, db: Session = Depends(get_db)):
    """
    Cria os registros que ainda não existirem (Fornecedor, Faturado, Despesa),
    e cria o lançamento (MOVIMENTOCONTAS) com suas PARCELAS.
    """
    nota = payload.nota
    tipo_movimento = payload.tipo_movimento or TIPO_MOVIMENTO_A_PAGAR

    fornecedor = crud.buscar_pessoa_por_documento(
        db, nota.fornecedor.cnpj, tipo=TIPO_PESSOA_CLIENTE_FORNECEDOR
    )
    fornecedor_criado = False
    if not fornecedor:
        fornecedor = crud.criar_pessoa(
            db,
            {
                "tipo": TIPO_PESSOA_CLIENTE_FORNECEDOR,
                "razao_social": nota.fornecedor.razao_social,
                "nome_fantasia": nota.fornecedor.nome_fantasia,
                "documento": nota.fornecedor.cnpj,
                "tipo_documento": "CNPJ",
            },
        )
        fornecedor_criado = True

    faturado = crud.buscar_pessoa_por_documento(db, nota.faturado.cpf, tipo=TIPO_PESSOA_FATURADO)
    faturado_criado = False
    if not faturado:
        faturado = crud.criar_pessoa(
            db,
            {
                "tipo": TIPO_PESSOA_FATURADO,
                "razao_social": nota.faturado.nome_completo,
                "documento": nota.faturado.cpf,
                "tipo_documento": "CPF",
            },
        )
        faturado_criado = True

    tipo_classificacao = (
        TIPO_CLASSIFICACAO_DESPESA if tipo_movimento == TIPO_MOVIMENTO_A_PAGAR else "RECEITA"
    )
    despesa = crud.buscar_classificacao_por_descricao(
        db, nota.classificacao_despesa, tipo=tipo_classificacao
    )
    despesa_criada = False
    if not despesa:
        despesa = crud.criar_classificacao(
            db, {"tipo": tipo_classificacao, "descricao": nota.classificacao_despesa}
        )
        despesa_criada = True

    parcelas = [p.model_dump() for p in nota.parcelas] or [
        {"numero": 1, "data_vencimento": nota.data_vencimento, "valor": nota.valor_total}
    ]

    movimento = crud.criar_movimento(
        db,
        tipo=tipo_movimento,
        fornecedor_id=fornecedor.id,
        faturado_id=faturado.id,
        numero_nota=nota.numero_nota,
        data_emissao=nota.data_emissao,
        descricao_produtos=nota.descricao_produtos,
        valor_total=nota.valor_total,
        classificacao_ids=[despesa.id],
        parcelas=parcelas,
    )

    return LancarContaResponse(
        mensagem="Registro lançado com sucesso.",
        fornecedor_criado=fornecedor_criado,
        faturado_criado=faturado_criado,
        despesa_criada=despesa_criada,
        movimento=movimento,
    )


# ==========================================================================
# ETAPA 2 — MANTER PESSOAS (Fornecedor / Cliente / Faturado)
# ==========================================================================

@app.get("/api/pessoas", response_model=list[PessoaOut])
async def api_listar_pessoas(
    tipo: str | None = None,
    busca: str | None = None,
    todos: bool = False,
    db: Session = Depends(get_db),
):
    """`todos=true` traz apenas status ATIVO (conforme recomendação de layout)."""
    apenas_ativos = todos and not busca
    return crud.listar_pessoas(db, tipo=tipo, termo=busca, apenas_ativos=apenas_ativos)


@app.post("/api/pessoas", response_model=PessoaOut)
async def api_criar_pessoa(pessoa: PessoaCreate, db: Session = Depends(get_db)):
    if pessoa.tipo not in (TIPO_PESSOA_CLIENTE_FORNECEDOR, TIPO_PESSOA_FATURADO):
        raise HTTPException(status_code=400, detail="tipo inválido. Use CLIENTE_FORNECEDOR ou FATURADO.")
    return crud.criar_pessoa(db, pessoa.model_dump())


@app.put("/api/pessoas/{pessoa_id}", response_model=PessoaOut)
async def api_atualizar_pessoa(pessoa_id: int, pessoa: PessoaUpdate, db: Session = Depends(get_db)):
    atualizado = crud.atualizar_pessoa(db, pessoa_id, pessoa.model_dump(exclude_unset=True))
    if not atualizado:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada.")
    return atualizado


@app.post("/api/pessoas/{pessoa_id}/inativar", response_model=PessoaOut)
async def api_inativar_pessoa(pessoa_id: int, db: Session = Depends(get_db)):
    pessoa = crud.inativar_pessoa(db, pessoa_id)
    if not pessoa:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada.")
    return pessoa


@app.post("/api/pessoas/{pessoa_id}/reativar", response_model=PessoaOut)
async def api_reativar_pessoa(pessoa_id: int, db: Session = Depends(get_db)):
    pessoa = crud.reativar_pessoa(db, pessoa_id)
    if not pessoa:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada.")
    return pessoa


# ==========================================================================
# ETAPA 2 — MANTER CLASSIFICAÇÃO (Tipo de Despesa / Tipo de Receita)
# ==========================================================================

@app.get("/api/classificacoes", response_model=list[ClassificacaoOut])
async def api_listar_classificacoes(
    tipo: str | None = None,
    busca: str | None = None,
    todos: bool = False,
    db: Session = Depends(get_db),
):
    apenas_ativos = todos and not busca
    return crud.listar_classificacoes(db, tipo=tipo, termo=busca, apenas_ativos=apenas_ativos)


@app.post("/api/classificacoes", response_model=ClassificacaoOut)
async def api_criar_classificacao(classificacao: ClassificacaoCreate, db: Session = Depends(get_db)):
    if classificacao.tipo not in ("DESPESA", "RECEITA"):
        raise HTTPException(status_code=400, detail="tipo inválido. Use DESPESA ou RECEITA.")
    return crud.criar_classificacao(db, classificacao.model_dump())


@app.put("/api/classificacoes/{classificacao_id}", response_model=ClassificacaoOut)
async def api_atualizar_classificacao(
    classificacao_id: int, classificacao: ClassificacaoUpdate, db: Session = Depends(get_db)
):
    atualizado = crud.atualizar_classificacao(db, classificacao_id, classificacao.model_dump(exclude_unset=True))
    if not atualizado:
        raise HTTPException(status_code=404, detail="Classificação não encontrada.")
    return atualizado


@app.post("/api/classificacoes/{classificacao_id}/inativar", response_model=ClassificacaoOut)
async def api_inativar_classificacao(classificacao_id: int, db: Session = Depends(get_db)):
    classificacao = crud.inativar_classificacao(db, classificacao_id)
    if not classificacao:
        raise HTTPException(status_code=404, detail="Classificação não encontrada.")
    return classificacao


@app.post("/api/classificacoes/{classificacao_id}/reativar", response_model=ClassificacaoOut)
async def api_reativar_classificacao(classificacao_id: int, db: Session = Depends(get_db)):
    classificacao = crud.reativar_classificacao(db, classificacao_id)
    if not classificacao:
        raise HTTPException(status_code=404, detail="Classificação não encontrada.")
    return classificacao


# ==========================================================================
# ETAPA 2 — REGISTRAR CONTAS (a Pagar / a Receber)
# ==========================================================================

@app.get("/api/contas", response_model=list[MovimentoOut])
async def api_listar_contas(
    tipo: str | None = None,
    busca: str | None = None,
    todos: bool = False,
    db: Session = Depends(get_db),
):
    apenas_ativos = todos and not busca
    return crud.listar_movimentos(db, tipo=tipo, termo=busca, apenas_ativos=apenas_ativos)


@app.get("/api/contas/{movimento_id}", response_model=MovimentoOut)
async def api_obter_conta(movimento_id: int, db: Session = Depends(get_db)):
    movimento = crud.obter_movimento(db, movimento_id)
    if not movimento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")
    return movimento


@app.post("/api/contas", response_model=MovimentoOut)
async def api_criar_conta(conta: MovimentoCreate, db: Session = Depends(get_db)):
    """Registrar Conta a Pagar / Conta a Receber manualmente (com 1+ classificações e 1+ parcelas)."""
    if conta.tipo not in ("A_PAGAR", "A_RECEBER"):
        raise HTTPException(status_code=400, detail="tipo inválido. Use A_PAGAR ou A_RECEBER.")
    if not conta.classificacao_ids:
        raise HTTPException(status_code=400, detail="Informe ao menos uma classificação.")
    parcelas = [p.model_dump() for p in conta.parcelas] or [
        {"numero": 1, "data_vencimento": None, "valor": conta.valor_total}
    ]
    return crud.criar_movimento(
        db,
        tipo=conta.tipo,
        fornecedor_id=conta.fornecedor_id,
        faturado_id=conta.faturado_id,
        numero_nota=conta.numero_nota,
        data_emissao=conta.data_emissao,
        descricao_produtos=conta.descricao_produtos,
        valor_total=conta.valor_total,
        classificacao_ids=conta.classificacao_ids,
        parcelas=parcelas,
    )


@app.put("/api/contas/{movimento_id}", response_model=MovimentoOut)
async def api_atualizar_conta(movimento_id: int, conta: MovimentoUpdate, db: Session = Depends(get_db)):
    dados = conta.model_dump(exclude_unset=True)
    classificacao_ids = dados.pop("classificacao_ids", None)
    parcelas = dados.pop("parcelas", None)
    movimento = crud.atualizar_movimento(db, movimento_id, dados, classificacao_ids, parcelas)
    if not movimento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")
    return movimento


@app.post("/api/contas/{movimento_id}/inativar", response_model=MovimentoOut)
async def api_inativar_conta(movimento_id: int, db: Session = Depends(get_db)):
    movimento = crud.inativar_movimento(db, movimento_id)
    if not movimento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")
    return movimento


@app.post("/api/contas/{movimento_id}/reativar", response_model=MovimentoOut)
async def api_reativar_conta(movimento_id: int, db: Session = Depends(get_db)):
    movimento = crud.reativar_movimento(db, movimento_id)
    if not movimento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")
    return movimento


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
