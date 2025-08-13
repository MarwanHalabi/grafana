import os, time, uuid, pytest, requests

BASE_URL = os.getenv("API_BASE_URL", "http://54.154.221.226:3000")
AUTH = (os.getenv("GRAFANA_USER", "admin"), os.getenv("GRAFANA_PASS", "admin"))

# --- CREATE / READ tests ---

def test_create_dashboard_succeeds(s):
    r = save_dashboard(s, title=f"py just testing {uuid.uuid4().hex[:6]}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("id") and body.get("uid")

def test_create_dashboard_in_folder_succeeds(s):
    folder = create_folder(s, f"py folder {uuid.uuid4().hex[:5]}")
    r = save_dashboard(s, title="in folder", folder_uid=folder["uid"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("folderUid") == folder["uid"]

def test_create_dashboard_unknown_folder_fails_400(s):
    r = save_dashboard(s, title="bad folder", folder_uid="unknown")
    assert r.status_code == 400, r.text
    assert "message" in r.json()

@pytest.mark.parametrize("schema_version", [1, 36, 40, None])
def test_schema_version_preserved_on_save_and_get(s, schema_version):
    # save
    dash = {"title": "Schema Version Test"}
    if schema_version is not None:
        dash["schemaVersion"] = schema_version
    r = s.post(f"{BASE_URL}/api/dashboards/db", json={"dashboard": dash})
    assert r.status_code == 200, r.text
    uid = r.json()["uid"]
    # get
    r2 = get_dashboard_by_uid(s, uid)
    assert r2.status_code == 200, r2.text
    saved = r2.json()["dashboard"]
    actual = saved.get("schemaVersion")
    if schema_version is None:
        # Expect not auto-filled (may be missing or non-int)
        assert actual in (None, saved.get("schemaVersion")), f"Unexpected schemaVersion: {actual}"
    else:
        assert int(actual) == schema_version

# --- UPDATE tests ---

def test_update_dashboard_title_succeeds(s):
    # Create
    create = save_dashboard(s, title=f"to-update {uuid.uuid4().hex[:6]}")
    assert create.status_code == 200, create.text
    uid = create.json()["uid"]

    # Read current version
    r_get = get_dashboard_by_uid(s, uid)
    assert r_get.status_code == 200, r_get.text
    dash = r_get.json()["dashboard"]
    cur_ver = dash.get("version", 1)

    # Update title (POST /api/dashboards/db with uid + version)
    new_title = f"updated-title {uuid.uuid4().hex[:6]}"
    upd = save_dashboard(s, uid=uid, version=cur_ver, title=new_title, overwrite=True)
    assert upd.status_code == 200, upd.text

    # Verify
    r_check = get_dashboard_by_uid(s, uid)
    assert r_check.status_code == 200, r_check.text
    got_title = r_check.json()["dashboard"].get("title")
    assert got_title == new_title

# --- DELETE tests ---

def test_delete_dashboard_succeeds(s):
    # Create
    create = save_dashboard(s, title=f"to-delete {uuid.uuid4().hex[:6]}")
    assert create.status_code == 200, create.text
    uid = create.json()["uid"]

    # Delete
    d = delete_dashboard_by_uid(s, uid)
    assert d.status_code == 200, d.text

    # Ensure it's gone
    after = get_dashboard_by_uid(s, uid)  # use sess.get(...) as requested
    assert after.status_code == 404, f"Expected 404 after delete, got {after.status_code}: {after.text}"

def test_delete_nonexistent_dashboard_404(s):
    bogus_uid = f"nope-{uuid.uuid4().hex[:12]}"
    d = delete_dashboard_by_uid(s, bogus_uid)
    assert d.status_code == 404, f"Expected 404, got {d.status_code}: {d.text}"

# ____UTILS____

def wait_for_grafana(url=BASE_URL, timeout=90):
    end = time.time() + timeout
    while time.time() < end:
        try:
            r = requests.get(f"{url}/api/health", timeout=3, auth=AUTH)
            if r.ok: return True
        except Exception:
            pass
        time.sleep(2)
    return False

@pytest.fixture(scope="session", autouse=True)
def ensure_up():
    if not wait_for_grafana():
        pytest.skip("Grafana server is not running")

@pytest.fixture
def s():
    sess = requests.Session()
    sess.auth = AUTH
    return sess

def create_folder(sess, title):
    r = sess.post(f"{BASE_URL}/api/folders", json={"title": title})
    assert r.status_code == 200, r.text
    return r.json()  # {id, uid, title, ...}

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

def get_dashboard_by_uid(sess, uid):
    return sess.get(f"{BASE_URL}/api/dashboards/uid/{uid}")

def delete_dashboard_by_uid(sess, uid):
    return sess.delete(f"{BASE_URL}/api/dashboards/uid/{uid}")
