import requests

#pylint:disable=missing-timeout

from utils import PROTO, HOST


def test_session_cookie_default_flags():
    # 默认（HTTP 本地部署）契约：会话 cookie 带 HttpOnly 与 SameSite=Lax
    # （CTFd 3.6.0 config.ini 默认），不带 Secure（由生产 .env 的
    # SESSION_COOKIE_SECURE=true 开启，见 docs/deployment.md）。
    response = requests.get(f"{PROTO}://{HOST}/login")
    response.raise_for_status()

    cookie = response.headers.get("Set-Cookie", "")
    assert cookie, "登录页应下发会话 cookie（CSRF nonce 存于会话）"
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie

    attributes = {part.strip().lower() for part in cookie.split(";") if "=" not in part}
    assert "secure" not in attributes, "默认部署不应携带 Secure 标志，否则 HTTP 测试环境无法登录"
