import os, json, unittest
from urllib import request, error
from base64 import b64encode

API_BASE_URL = os.getenv("API_BASE_URL", "http://34.244.73.51:3000")
GRAFANA_USER = os.getenv("admin")
GRAFANA_PASS = os.getenv("admin")

class TestGrafanaHealthAPI(unittest.TestCase):
    def test_health_endpoint(self):
        url = f"{API_BASE_URL}/api/health"
        try:
            body = _fetch_json(url, timeout=3)
        except (error.URLError, error.HTTPError) as e:
            self.fail(f"Health check failed: {e}")
        self.assertIn("database", body, f"Unexpected payload: {body}")
        self.assertEqual(body.get("database"), "ok", f"DB not ok: {body}")


def _fetch_json(url, timeout=3):
    headers = {"Accept": "application/json"}
    if GRAFANA_USER and GRAFANA_PASS:
        token = b64encode(f"{GRAFANA_USER}:{GRAFANA_PASS}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    req = request.Request(url, headers=headers)
    with request.urlopen(req, timeout=timeout) as resp:
        if resp.getcode() != 200:
            raise error.HTTPError(url, resp.getcode(), "non-200", resp.headers, None)
        return json.loads((resp.read() or b"{}").decode())


if __name__ == "__main__":
    unittest.main()
