import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.extractor import extract_invoice_data
from app.schemas import NotaFiscalExtracao

app = FastAPI(
    title="Extrator de Dados de Nota Fiscal com Gemini",
    description="Aplicação para extração e categorização de notas fiscais usando LLM",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

@app.get("/health")
async def health_check():
    """Endpoint de verificação de integridade para o Render."""
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Renderiza a interface gráfica web minimalista."""
    html_file = TEMPLATES_DIR / "index.html"
    if not html_file.exists():
        raise HTTPException(status_code=500, detail="Template index.html não encontrado.")
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))

from typing import Annotated


@app.post("/api/extrair", response_model=NotaFiscalExtracao)
async def extrair_nota(
    file: Annotated[UploadFile, File(description="Arquivo PDF da Nota Fiscal")],
    api_key: Annotated[str | None, Form(description="Chave de API Gemini opcional")] = None,
):
    """
    Recebe um arquivo PDF de nota fiscal e extrai os dados estruturados usando Gemini.
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
