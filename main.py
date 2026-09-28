"""
Ponto de entrada para execução local e deploy no Render.
Comando no Render: uvicorn main:app --host 0.0.0.0 --port $PORT
"""
import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
