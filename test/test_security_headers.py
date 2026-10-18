import requests

#pylint:disable=missing-timeout

from utils import PROTO, HOST

BASE = f"{PROTO}://{HOST}"

CSP_ESSENTIALS = [
    # CSP 的关键收紧项：默认同源加载，禁插件，锁定 base/form/frame 目标。
    # script/style 允许 unsafe-inline 是主题现状（大量内联脚本/样式），
    # 后续若做 nonce 化可再收紧。
    "default-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'self'",
    # 模块页面的课程资源嵌入（module.html 的视频与 slides iframe）
    "frame-src 'self' https://player.bilibili.com https://mudongliang.github.io",
]


def test_platform_pages_carry_security_headers():
    response = requests.get(f"{BASE}/login")
    response.raise_for_status()

    assert response.headers.get("X-Content-Type-Options", "").lower() == "nosniff"
    assert response.headers.get("X-Frame-Options", "").upper() == "SAMEORIGIN"
    assert response.headers.get("Referrer-Policy", "").lower() == "strict-origin-when-cross-origin"
    assert "max-age=" in response.headers.get("Strict-Transport-Security", "")

    csp = response.headers.get("Content-Security-Policy", "")
    for fragment in CSP_ESSENTIALS:
        assert fragment in csp, f"CSP 缺少 {fragment}: {csp}"


def test_error_responses_keep_security_headers():
    # add_header 必须带 always 标志：错误页同样要带安全头，
    # 否则错误页会被嗅探/嵌入。
    response = requests.get(f"{BASE}/definitely-not-a-page-404")
    assert response.status_code == 404

    assert response.headers.get("X-Content-Type-Options", "").lower() == "nosniff"
    assert response.headers.get("X-Frame-Options", "").upper() == "SAMEORIGIN"
    assert "max-age=" in response.headers.get("Strict-Transport-Security", "")


def test_workspace_internal_exempt_from_csp():
    # /internal/ 经 X-Accel-Redirect 代理 workspace 内容（code-server、
    # noVNC、挑战页面）。平台 CSP 会拦截 code-server 依赖的 blob: Web
    # Worker，因此该 location 显式豁免；本测试守住这个豁免不被回归：
    # 一旦 CSP 出现在 /internal/ 响应上，VS Code 工作区就会被打破。
    response = requests.get(f"{BASE}/internal/anything")
    assert response.status_code == 404, "internal 路径外部直访应返回 404"

    assert response.headers.get("X-Frame-Options", "").upper() == "SAMEORIGIN"
    assert "Content-Security-Policy" not in response.headers
    assert "Strict-Transport-Security" not in response.headers


def test_monitoring_exempt_from_platform_csp():
    # Grafana 的资源加载策略由其自身管理；无论其是否在运行（502/200），
    # 响应都不应带平台 CSP。豁免头 nosniff 仍应存在。
    response = requests.get(f"{BASE}/monitoring/", allow_redirects=True)
    assert response.status_code in (200, 502)

    assert "Content-Security-Policy" not in response.headers
    assert response.headers.get("X-Content-Type-Options", "").lower() == "nosniff"
