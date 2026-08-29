"""FastAPI Smoke Tests for Render Production Deployment.

Verifies:
1. GET /health -> 200 {"status": "ok"}
2. GET /api/health -> 200 {"status": "ok"}
3. GET /openapi.json -> 200
4. GET /docs -> 200
5. GET /api/posts?limit=5&offset=0 -> 200
6. GET /api/posts/stats -> 200
7. GET /posts?limit=5&offset=0 -> 200
8. GET /posts/stats -> 200
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_api_health_endpoint() -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_openapi_json_endpoint() -> None:
    res = client.get("/openapi.json")
    assert res.status_code == 200
    data = res.json()
    assert "openapi" in data
    assert "paths" in data
    assert "/health" in data["paths"]
    assert "/api/posts" in data["paths"] or "/posts" in data["paths"]


def test_docs_endpoint() -> None:
    res = client.get("/docs")
    assert res.status_code == 200
    assert "Swagger UI" in res.text or "swagger-ui" in res.text


def test_api_posts_pagination_endpoint() -> None:
    res = client.get("/api/posts?limit=5&offset=0")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "pagination" in data
    assert data["pagination"]["limit"] == 5
    assert data["pagination"]["offset"] == 0
    assert isinstance(data["items"], list)
    assert len(data["items"]) <= 5


def test_api_posts_stats_endpoint() -> None:
    res = client.get("/api/posts/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_posts" in data
    assert "posts_by_mood" in data
    assert "posts_by_category" in data
    assert isinstance(data["total_posts"], int)


def test_posts_direct_endpoints() -> None:
    res = client.get("/posts?limit=5&offset=0")
    assert res.status_code == 200
    assert "items" in res.json()

    res_stats = client.get("/posts/stats")
    assert res_stats.status_code == 200
    assert "total_posts" in res_stats.json()
