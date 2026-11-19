from app.config import BUILTIN_ALIASES
from app.reasons import reject
def evaluate(rows,context):
    "旧编码经生效对照表归入现行线路；原码存入route_legacy，永不改写。"
    aliases=((context or {}).get("parameters") or {}).get("aliases") or BUILTIN_ALIASES
    good=[];bad=[]
    for row in rows:
        legacy=row.get("route")
        route=aliases.get(legacy)
        if not route:bad.append(reject(row,"UNKNOWN_ROUTE",f"线路未登记: {legacy}"));continue
        if not row.get("card"):bad.append(reject(row,"EMPTY_CARD","卡号为空"));continue
        good.append({**row,"route":route,"route_legacy":legacy,"line_group":"city"})
    return {"rows":good,"quarantine":bad,"metrics":{"routes":len(set(r["route"] for r in good)),"accepted":len(good),"aliased":sum(r["route_legacy"]!=r["route"] for r in good)}}
