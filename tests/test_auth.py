from fastapi.testclient import TestClient

from app.main import app


def test_sem_login_redireciona_e_api_retorna_401(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "0")
    client = TestClient(app)
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert client.get("/api/pessoas").status_code == 401
    assert client.get("/health").status_code == 200


def test_login_valido_libera_acesso(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "0")
    monkeypatch.setenv("APP_USUARIO", "professor")
    monkeypatch.setenv("APP_SENHA", "segredo")
    client = TestClient(app)
    r = client.post("/login", data={"usuario": "professor", "senha": "errada"}, follow_redirects=False)
    assert r.headers["location"] == "/login?erro=1"
    r = client.post("/login", data={"usuario": "professor", "senha": "segredo"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert client.get("/").status_code == 200
    assert client.get("/api/versao").json()["usuario"] == "professor"


def test_versao_exibe_commit_do_render(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abcdef1234567890")
    client = TestClient(app)
    dados = client.get("/api/versao").json()
    assert dados["commit_curto"] == "abcdef1"
    assert "versaoCommit" in client.get("/").text
