from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health_returns_ok() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


async def test_tenants_me_without_header_falls_back_to_a_tenant() -> None:
    # Tenant enforcement is temporarily disabled (see
    # app/dependencies.py::get_current_tenant) — without a header this
    # auto-picks any active tenant instead of 400ing. Update this test
    # back to asserting 400 once enforcement is restored.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/tenants/me")

    assert response.status_code in (200, 404)
