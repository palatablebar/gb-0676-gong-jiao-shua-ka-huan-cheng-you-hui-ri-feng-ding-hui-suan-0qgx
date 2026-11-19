import sqlite3,json,hashlib
from datetime import datetime,timezone
from pathlib import Path
from app.config import DATA_DIR,BUILTIN_ALIASES,CURRENT_ROUTES
from app.errors import DomainError
def alias_id(mapping):
    "对照版本按内容寻址：同一映射永远得到同一版本号。"
    return hashlib.sha256(json.dumps(mapping,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:20]
def connect():
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(DATA_DIR/"records.db",timeout=20)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY,payload TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,decision TEXT NOT NULL DEFAULT '待复核')")
    db.execute("CREATE TABLE IF NOT EXISTS alias_versions (id TEXT PRIMARY KEY,payload TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'draft',created_at TEXT NOT NULL)")
    builtin=alias_id(BUILTIN_ALIASES)
    db.execute("INSERT OR IGNORE INTO alias_versions(id,payload,status,created_at) VALUES (?,?,?,?)",(builtin,json.dumps(BUILTIN_ALIASES,ensure_ascii=False,sort_keys=True),"draft","2026-11-19T00:00:00+00:00"))
    db.execute("UPDATE alias_versions SET status='active' WHERE id=? AND NOT EXISTS (SELECT 1 FROM alias_versions WHERE status='active')",(builtin,))
    return db
def save(run_id,payload):
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO runs(id,payload) VALUES (?,?)",(run_id,json.dumps(payload,ensure_ascii=False)))
    return get(run_id)
def get(run_id):
    with connect() as db: row=db.execute("SELECT payload,version,decision FROM runs WHERE id=?",(run_id,)).fetchone()
    if not row: raise DomainError("NOT_FOUND","批次不存在",404)
    return {**json.loads(row[0]),"version":row[1],"decision":row[2]}
def latest():
    with connect() as db: row=db.execute("SELECT id FROM runs ORDER BY rowid DESC LIMIT 1").fetchone()
    return get(row[0]) if row else None
def history():
    with connect() as db: return [{"run_id":i,"version":v,"decision":d} for i,v,d in db.execute("SELECT id,version,decision FROM runs ORDER BY rowid DESC")]
def review(run_id,version,decision):
    if decision not in {"已复核","退回复核"}: raise DomainError("BAD_DECISION","复核状态无效")
    with connect() as db:
        cursor=db.execute("UPDATE runs SET version=version+1,decision=? WHERE id=? AND version=?",(decision,run_id,version))
        if cursor.rowcount!=1:
            if not db.execute("SELECT 1 FROM runs WHERE id=?",(run_id,)).fetchone(): raise DomainError("NOT_FOUND","批次不存在",404)
            raise DomainError("STALE_VERSION","版本已更新，请刷新",409)
    return get(run_id)
def _alias_row(row): return {"id":row[0],"mapping":json.loads(row[1]),"status":row[2],"created_at":row[3]}
def alias_versions():
    with connect() as db: rows=db.execute("SELECT id,payload,status,created_at FROM alias_versions ORDER BY rowid").fetchall()
    return [_alias_row(row) for row in rows]
def get_alias(alias):
    with connect() as db: row=db.execute("SELECT id,payload,status,created_at FROM alias_versions WHERE id=?",(alias,)).fetchone()
    if not row: raise DomainError("ALIAS_NOT_FOUND","对照版本不存在",404)
    return _alias_row(row)
def active_aliases():
    "当前口径：任一时刻只有一个生效对照版本。"
    with connect() as db: row=db.execute("SELECT id,payload FROM alias_versions WHERE status='active'").fetchone()
    return row[0],json.loads(row[1])
def create_alias(mapping):
    "登记对照草稿：只做形状校验，内容寻址保证重复提交不新增版本。"
    if not isinstance(mapping,dict) or not mapping: raise DomainError("ALIAS_INVALID","对照需要非空对象")
    clean={}
    for key,value in mapping.items():
        if not isinstance(key,str) or not isinstance(value,str): raise DomainError("ALIAS_INVALID","对照键值需要文本")
        key,value=key.strip(),value.strip()
        if not key or not value: raise DomainError("ALIAS_INVALID","对照键值不能为空")
        clean[key]=value
    aid=alias_id(clean)
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO alias_versions(id,payload,status,created_at) VALUES (?,?,?,?)",(aid,json.dumps(clean,ensure_ascii=False,sort_keys=True),"draft",datetime.now(timezone.utc).isoformat()))
    return get_alias(aid)
def activate_alias(alias):
    "原子生效：先校验后切换，任一失败整体回滚，旧版继续生效。"
    mapping=get_alias(alias)["mapping"]
    unknown=sorted({value for value in mapping.values() if value not in CURRENT_ROUTES})
    if unknown: raise DomainError("ALIAS_UNKNOWN_ROUTE","对照目标不是现行线路: "+",".join(unknown))
    missing=[route for route in CURRENT_ROUTES if mapping.get(route)!=route]
    if missing: raise DomainError("ALIAS_INCOMPLETE","现行线路必须恒等保留: "+",".join(missing))
    with connect() as db:
        db.execute("UPDATE alias_versions SET status='superseded' WHERE status='active'")
        db.execute("UPDATE alias_versions SET status='active' WHERE id=?",(alias,))
    return get_alias(alias)
