"""
Autenticação simples (login/senha) para acesso ao sistema hospedado.

Credenciais configuradas por variáveis de ambiente:
- APP_USUARIO   (padrão: admin)
- APP_SENHA     (padrão: admin123)
- SECRET_KEY    (chave para assinar o cookie de sessão)
- AUTH_DISABLED=1 desativa o login (usado nos testes automatizados)
"""
import hashlib
import hmac
import os

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

COOKIE_NAME = "sessao_financeiro"
ROTAS_PUBLICAS = {"/login", "/logout", "/health", "/favicon.ico"}


def _usuario() -> str:
    return os.getenv("APP_USUARIO", "admin")


def _senha() -> str:
    return os.getenv("APP_SENHA", "admin123")


def _secret() -> bytes:
    return os.getenv("SECRET_KEY", "troque-esta-chave-em-producao").encode()


def auth_desativada() -> bool:
    return os.getenv("AUTH_DISABLED", "").strip() in ("1", "true", "True")


def validar_credenciais(usuario: str, senha: str) -> bool:
    return hmac.compare_digest(usuario or "", _usuario()) and hmac.compare_digest(senha or "", _senha())


def gerar_token(usuario: str) -> str:
    assinatura = hmac.new(_secret(), usuario.encode(), hashlib.sha256).hexdigest()
    return f"{usuario}:{assinatura}"


def usuario_do_token(token: str | None) -> str | None:
    if not token or ":" not in token:
        return None
    usuario, assinatura = token.rsplit(":", 1)
    esperado = hmac.new(_secret(), usuario.encode(), hashlib.sha256).hexdigest()
    return usuario if hmac.compare_digest(assinatura, esperado) else None


class LoginObrigatorioMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if auth_desativada() or request.url.path in ROTAS_PUBLICAS:
            return await call_next(request)

        if usuario_do_token(request.cookies.get(COOKIE_NAME)):
            return await call_next(request)

        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": "Não autenticado. Faça login."}, status_code=401)
        return RedirectResponse(url="/login", status_code=303)
