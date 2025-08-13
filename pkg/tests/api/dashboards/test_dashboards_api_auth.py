
import os, time, uuid, pytest, requests

BASE_URL = os.getenv("API_BASE_URL", "http://54.154.221.226:3000")
AUTH = (os.getenv("GRAFANA_USER", "admin"), os.getenv("GRAFANA_PASS", "admin"))
def test_auth_required_for_save_dashboard_no_auth():
    """POST /api/dashboards/db without credentials should be denied (401/403)."""
    sess = requests.Session()  # no auth
    payload = {"dashboard": {"title": f"unauth save {uuid.uuid4().hex[:6]}"}}
    r = sess.post(f"{BASE_URL}/api/dashboards/db", json=payload)
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}: {r.text}"

def test_auth_required_for_delete_dashboard_no_auth(s):
    """DELETE /api/dashboards/uid/:uid without credentials should be denied (401/403)."""
    # Create with auth
    create = save_dashboard(s, title=f"del-unauth {uuid.uuid4().hex[:6]}")
    assert create.status_code == 200, create.text
    uid = create.json()["uid"]

    # Try delete without auth
    sess = requests.Session()  # no auth
    d = sess.delete(f"{BASE_URL}/api/dashboards/uid/{uid}")
    assert d.status_code in (401, 403), f"Expected 401/403, got {d.status_code}: {d.text}"

    # Cleanup with auth
    cleanup = delete_dashboard_by_uid(s, uid)
    assert cleanup.status_code == 200, cleanup.text

def test_auth_with_bad_credentials_denied():
    """Using wrong basic auth should be denied (401/403) on save."""
    sess = requests.Session()
    sess.auth = ("wrong", "creds")
    payload = {"dashboard": {"title": f"bad-auth {uuid.uuid4().hex[:6]}"}}
    r = sess.post(f"{BASE_URL}/api/dashboards/db", json=payload)
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}: {r.text}"

# _______________

def save_dashboard(sess, *, title=None, uid=None, id_=None, folder_uid=None, version=None, overwrite=True):
    dash = {}
    if title is not None: dash["title"] = title
    if uid   is not None: dash["uid"]   = uid
    if id_   is not None: dash["id"]    = id_
    if version is not None: dash["version"] = version
    payload = {"dashboard": dash, "overwrite": overwrite}
    if folder_uid is not None:
        payload["folderUid"] = folder_uid
    r = sess.post(f"{BASE_URL}/api/dashboards/db", json=payload)
    return r

def delete_dashboard_by_uid(sess, uid):
    return sess.delete(f"{BASE_URL}/api/dashboards/uid/{uid}")

@pytest.fixture(scope="session")
def s():
    """Authenticated requests.Session for Grafana API."""
    sess = requests.Session()
    token = os.getenv("GRAFANA_API_TOKEN")
    if token:
        sess.headers.update({"Authorization": f"Bearer {token}"})
    else:
        user = os.getenv("GRAFANA_USER", "admin")
        pwd  = os.getenv("GRAFANA_PASS", "admin")
        sess.auth = (user, pwd)
    sess.headers.update({"Content-Type": "application/json"})
    yield sess
    sess.close()
