import csv,io
from decimal import Decimal
from app.config import COLUMNS
from app.errors import DomainError
from app.values import money,number
from app import store
from app.pipeline import calculate
def canonical_input(run):
    "从封存批次的首阶段记录还原规范输入；原批一字节不改写。"
    stage=run["stages"][0]
    rows=list(stage.get("rows",[]))+list(stage.get("quarantine",[]))
    rows.sort(key=lambda r:r.get("_line",0))
    stream=io.StringIO(newline="");writer=csv.writer(stream,lineterminator="\n")
    writer.writerow(COLUMNS)
    for row in rows:
        cells=row.get("_raw")
        if isinstance(cells,list) and cells: writer.writerow([str(c) for c in cells])
        else: writer.writerow([str(row.get(c,"")) for c in COLUMNS])
    return stream.getvalue().encode("utf-8")
def build_migration(run,alias_version,aliases):
    "按现行对照重算旧批的换乘与日封顶，生成唯一迁移对账结果。"
    stages=run.get("stages",[])
    if len(stages)<7: raise DomainError("RUN_INCOMPLETE","原批结果不完整，不能迁移")
    if stages[5].get("metrics",{}).get("balanced") is False:
        raise DomainError("UNBALANCED","旧批未对平，不得迁移封存")
    params=dict(run.get("manifest",{}).get("parameters",{}))
    for key in ("aliases","alias_version","migration_of"): params.pop(key,None)
    params.update(aliases=aliases,alias_version=alias_version,migration_of=run["run_id"])
    result=calculate(canonical_input(run),params)
    old_expected={row.get("event_id"):row.get("expected","0") for row in stages[4].get("rows",[])}
    new_rows=result["stages"][5]["rows"]
    new_ids={row.get("event_id") for row in new_rows}
    delta=abs_delta=Decimal(0)
    fields={}
    for row in new_rows:
        before=old_expected.get(row.get("event_id"),"0.00")
        change=number(row["expected"])-number(before)
        fields[row.get("event_id")]={"expected_old":before,"migration_delta":money(change),"migration_note":"旧批隔离" if row.get("event_id") not in old_expected else "—"}
        delta+=change;abs_delta+=abs(change)
    for stage in (result["stages"][5],result["stages"][6]):
        for row in stage["rows"]: row.update(fields[row.get("event_id")])
    dropped=sum(1 for event in old_expected if event not in new_ids)
    metrics=result["stages"][5]["metrics"]
    result["migration"]={"migrated_from":run["run_id"],"alias_version":alias_version,
        "expected_old_total":money(number(stages[4].get("metrics",{}).get("expected_total","0"))),
        "expected_new_total":metrics["expected_total"],
        "delta_total":money(delta),"abs_delta_total":money(abs_delta),"dropped_events":dropped}
    metrics.update(migration_delta_total=result["migration"]["delta_total"],migration_abs_delta_total=result["migration"]["abs_delta_total"],migrated_from=run["run_id"],alias_version=alias_version)
    return result
def migrate(run_id):
    "迁移幂等：同一旧批同一对照版本只产生一个迁移批，重跑复用不新增。"
    run=store.get(run_id)
    alias_version,aliases=store.active_aliases()
    result=build_migration(run,alias_version,aliases)
    return store.save(result["run_id"],result)
