"""Tests for correlation ID header on all responses."""


def test_correlation_id_on_success(client):
    """Test that correlation ID is included on successful responses."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    assert len(response.headers["X-Correlation-ID"]) == 8  # 4 bytes as hex


def test_correlation_id_on_404_error(client):
    """Test that correlation ID is included on 404 error responses (HTTPException)."""
    response = client.get("/api/v1/secrets/retrieve", headers={"Authorization": "Bearer " + "a" * 64})
    assert response.status_code == 404
    assert "X-Correlation-ID" in response.headers
    assert len(response.headers["X-Correlation-ID"]) == 8


def test_correlation_id_on_validation_error(client):
    """Test that correlation ID is included on validation error (422) responses."""
    response = client.post(
        "/api/v1/challenges",
        json={"payload_hash": "tooshort", "ciphertext_size": 100},
    )
    assert response.status_code == 422
    assert "X-Correlation-ID" in response.headers
    assert len(response.headers["X-Correlation-ID"]) == 8


def test_correlation_id_on_unauthorized_error(client):
    """Test that correlation ID is included on 401 error responses (HTTPException)."""
    response = client.get("/api/v1/secrets/retrieve", headers={"Authorization": "InvalidFormat"})
    assert response.status_code == 401
    assert "X-Correlation-ID" in response.headers
    assert len(response.headers["X-Correlation-ID"]) == 8


def test_correlation_ids_unique_across_requests(client):
    """Test that each request gets a unique correlation ID."""
    response1 = client.get("/health")
    response2 = client.get("/health")
    
    corr_id_1 = response1.headers.get("X-Correlation-ID")
    corr_id_2 = response2.headers.get("X-Correlation-ID")
    
    assert corr_id_1 != corr_id_2, "Correlation IDs should be unique across requests"
