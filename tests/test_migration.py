import pytest
from decimal import Decimal
from app import store
from app.config import BUILTIN_ALIASES
from app.errors import DomainError
from app.migration import build_migration,canonical_input,migrate
from app.modules.m2_routes.rules import evaluate
from app.pipeline import calculate,execute,load_sample
NEW={**BUILTIN_ALIASES,"1·":"01"}
@pytest.fixture
def old_run(): return execute(load_sample("legacy.csv"))
@pytest.fixture
def migrated(old_run):
    store.activate_alias(store.create_alias(NEW)["id"])
    return migrate(old_run["run_id"])
def test_legacy_codes_quarantined_under_builtin(old_run):
    quarantine=old_run["stages"][1]["quarantine"]
    assert sum(q["reason"]=="UNKNOWN_ROUTE" for q in quarantine)==9
    assert sum(q.get("route")=="1·" for q in quarantine)==8
def test_route_legacy_preserved(old_run):
    rows=evaluate([{"route":"1路","card":"01"}],{"parameters":{"aliases":NEW}})["rows"]
    assert rows[0]["route"]=="01" and rows[0]["route_legacy"]=="1路"
def test_migration_recognizes_legacy_codes(migrated):
    rows={r["event_id"]:r for r in migrated["stages"][1]["rows"]}
    assert rows["0010"]["route_legacy"]=="1·" and rows["0010"]["route"]=="01"
    assert [q["reason"] for q in migrated["stages"][1]["quarantine"]]==["UNKNOWN_ROUTE"]
def test_transfer_recomputed_not_split(migrated,old_run):
    def row(run,event): return next(r for r in run["stages"][4]["rows"] if r["event_id"]==event)
    assert row(old_run,"0011")["expected"]=="2.50" and row(old_run,"0011")["transfer_discount"]=="0.00"
    assert row(migrated,"0011")["expected"]=="1.50" and row(migrated,"0011")["transfer_discount"]=="1.00"
def test_migration_delta_columns(migrated):
    rows={r["event_id"]:r for r in migrated["stages"][5]["rows"]}
    assert rows["0010"]["expected_old"]=="0.00" and rows["0010"]["migration_delta"]=="2.50" and rows["0010"]["migration_note"]=="旧批隔离"
    assert rows["0011"]["expected_old"]=="2.50" and rows["0011"]["migration_delta"]=="-1.00"
    assert rows["0013"]["expected_old"]=="2.00" and rows["0013"]["migration_delta"]=="-1.50"
def test_migration_books_balance(migrated,old_run):
    rows=migrated["stages"][5]["rows"];summary=migrated["migration"]
    assert summary["expected_old_total"]==old_run["stages"][4]["metrics"]["expected_total"]
    assert summary["expected_new_total"]==migrated["stages"][4]["metrics"]["expected_total"]
    assert sum(Decimal(r["migration_delta"]) for r in rows)==Decimal(summary["delta_total"])
    assert sum(abs(Decimal(r["migration_delta"])) for r in rows)==Decimal(summary["abs_delta_total"])==Decimal("40.00")
    assert summary["dropped_events"]==0
def test_migration_idempotent(migrated,old_run):
    before=len(store.history())
    again=migrate(old_run["run_id"])
    assert again["run_id"]==migrated["run_id"] and len(store.history())==before
def test_old_batch_untouched(old_run,migrated):
    after=store.get(old_run["run_id"])
    assert after["stages"]==old_run["stages"] and after["run_id"] in {r["run_id"] for r in store.history()}
def test_unbalanced_old_batch_not_migrated(old_run):
    old_run["stages"][5]["metrics"]["balanced"]=False
    with pytest.raises(DomainError) as e: build_migration(old_run,"v",NEW)
    assert e.value.code=="UNBALANCED"
def test_migration_run_balanced_and_sealable(migrated):
    assert migrated["stages"][5]["metrics"]["balanced"] is True
    assert migrated["stages"][6]["metrics"]["ready"] is True
def test_canonical_input_replays_lineage(old_run):
    replay=calculate(canonical_input(old_run),old_run["manifest"]["parameters"])
    assert replay["stages"][5]["metrics"]["balanced"] is True
    assert replay["stages"][4]["metrics"]["expected_total"]==old_run["stages"][4]["metrics"]["expected_total"]
def test_migrate_endpoint(client,old_run):
    assert client.post("/api/runs/missing/migrate").status_code==404
    client.post("/api/aliases",json={"mapping":NEW})
    draft=client.get("/api/aliases").get_json()["versions"][-1]
    client.post(f"/api/aliases/{draft['id']}/activate")
    r=client.post(f"/api/runs/{old_run['run_id']}/migrate")
    assert r.status_code==200 and r.get_json()["migration"]["migrated_from"]==old_run["run_id"]
def test_migration_page_shows_legacy_current_difference(client,migrated):
    html=client.get("/clearing").get_data(as_text=True)
    for text in ("旧编码","现行线路","迁移差额","1·","迁移对账","差额合计"):
        assert text in html
def test_migrate_button_disabled_when_current(client,migrated):
    html=client.get("/routes").get_data(as_text=True)
    assert 'id="migrate" disabled' in html
