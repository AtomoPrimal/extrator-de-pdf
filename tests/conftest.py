import os
import sys

# Os testes automatizados rodam sem a tela de login (ver tests/test_auth.py para o login).
os.environ.setdefault("AUTH_DISABLED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
