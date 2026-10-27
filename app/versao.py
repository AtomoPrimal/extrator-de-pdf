"""
Identifica o código (hash do commit) da última atualização no GitHub,
exibido na tela principal do sistema.

Ordem de busca:
1. RENDER_GIT_COMMIT  — definido automaticamente pelo Render em cada deploy
2. GIT_COMMIT         — variável manual (outros provedores de hospedagem)
3. Pasta .git local   — execução local a partir do repositório clonado
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _commit_do_git_local() -> str | None:
    git_dir = BASE_DIR / ".git"
    head = git_dir / "HEAD"
    try:
        conteudo = head.read_text().strip()
        if conteudo.startswith("ref:"):
            ref = conteudo.split(" ", 1)[1].strip()
            ref_file = git_dir / ref
            if ref_file.exists():
                return ref_file.read_text().strip()
            packed = git_dir / "packed-refs"
            if packed.exists():
                for linha in packed.read_text().splitlines():
                    if linha.endswith(ref):
                        return linha.split(" ", 1)[0]
            return None
        return conteudo
    except OSError:
        return None


def obter_versao() -> dict:
    commit = os.getenv("RENDER_GIT_COMMIT") or os.getenv("GIT_COMMIT") or _commit_do_git_local()
    branch = os.getenv("RENDER_GIT_BRANCH") or os.getenv("GIT_BRANCH")
    repo = os.getenv("RENDER_GIT_REPO_SLUG")
    return {
        "commit": commit or "desconhecido",
        "commit_curto": commit[:7] if commit else "desconhecido",
        "branch": branch,
        "repositorio": repo,
    }
