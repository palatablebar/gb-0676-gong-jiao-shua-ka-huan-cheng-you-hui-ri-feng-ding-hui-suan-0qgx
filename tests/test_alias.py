import pytest
from app import store
from app.config import BUILTIN_ALIASES
from app.errors import DomainError
NEW={**BUILTIN_ALIASES,"1·":"01"}
def test_builtin_active_by_default():
    version,mapping=store.active_aliases()
    assert mapping==BUILTIN_ALIASES and "1·" not in mapping
def test_create_draft_idempotent():
    a=store.create_alias(NEW);b=store.create_alias(dict(NEW))
    assert a["id"]==b["id"] and len(store.alias_versions())==2
def test_activate_swaps_and_keeps_old():
    old_version,_=store.active_aliases()
    draft=store.create_alias(NEW)
    store.activate_alias(draft["id"])
    assert store.active_aliases()[0]==draft["id"]
    kept={v["id"]:v["status"] for v in store.alias_versions()}
    assert kept[old_version]=="superseded" and kept[draft["id"]]=="active"
def test_failed_activation_keeps_old():
    old_version,old_mapping=store.active_aliases()
    bad=store.create_alias({**BUILTIN_ALIASES,"1·":"99"})
    with pytest.raises(DomainError) as e: store.activate_alias(bad["id"])
    assert e.value.code=="ALIAS_UNKNOWN_ROUTE"
    assert store.active_aliases()==(old_version,old_mapping)
def test_activation_must_keep_current_routes():
    old_version,_=store.active_aliases()
    incomplete=store.create_alias({"01":"01","1·":"01"})
    with pytest.raises(DomainError) as e: store.activate_alias(incomplete["id"])
    assert e.value.code=="ALIAS_INCOMPLETE"
    assert store.active_aliases()[0]==old_version
def test_activation_atomic_on_mixed_mapping():
    old_version,_=store.active_aliases()
    mixed=store.create_alias({**BUILTIN_ALIASES,"1·":"01","2·":"99"})
    with pytest.raises(DomainError): store.activate_alias(mixed["id"])
    version,mapping=store.active_aliases()
    assert version==old_version and "1·" not in mapping
def test_activate_unknown_404():
    with pytest.raises(DomainError) as e: store.activate_alias("missing")
    assert e.value.status==404
def test_create_rejects_bad_shape():
    for mapping in ({},[],{"":"01"},{"1·":""},{"1·":1}):
        with pytest.raises(DomainError) as e: store.create_alias(mapping)
        assert e.value.code=="ALIAS_INVALID"
def test_alias_api_flow(client):
    r=client.get("/api/aliases");assert r.status_code==200
    active=r.get_json()["active"]
    draft=client.post("/api/aliases",json={"mapping":NEW}).get_json()
    assert client.post(f"/api/aliases/{draft['id']}/activate").status_code==200
    assert client.get("/api/aliases").get_json()["active"]==draft["id"]!=active
def test_alias_api_failed_activation_keeps_old(client):
    active=client.get("/api/aliases").get_json()["active"]
    draft=client.post("/api/aliases",json={"mapping":{**BUILTIN_ALIASES,"1·":"99"}}).get_json()
    assert client.post(f"/api/aliases/{draft['id']}/activate").status_code==422
    assert client.get("/api/aliases").get_json()["active"]==active
