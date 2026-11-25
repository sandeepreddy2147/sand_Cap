"""Smoke tests for read-only pages. POST routes are not exercised so the real database is not changed."""
import pytest

import app as webapp


@pytest.fixture()
def client():
    if not webapp.DB_PATH.is_file():
        pytest.skip("database not found")
    webapp.app.config.update(TESTING=True)
    return webapp.app.test_client()


@pytest.mark.parametrize("path", ["/", "/crimes", "/communities", "/charts", "/insights", "/insights?days=30",
                                  "/crimes?year=2016", "/crimes?arrest=1"])
def test_pages_return_200(client, path):
    assert client.get(path).status_code == 200


def test_insights_page_has_recommendations(client):
    html = client.get("/insights").get_data(as_text=True)
    assert "Recommendations" in html and "Near-term alerts" in html


def test_post_without_csrf_token_is_rejected(client):
    assert client.post("/crimes/1/delete", data={}).status_code == 400


def test_unknown_crime_returns_404(client):
    assert client.get("/crimes/999999999").status_code == 404
