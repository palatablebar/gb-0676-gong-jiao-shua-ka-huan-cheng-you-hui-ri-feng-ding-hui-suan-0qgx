from pathlib import Path
import os
ROOT=Path(__file__).resolve().parent.parent
DATA_DIR=Path(os.environ.get("DATA_DIR", "/tmp/transitcap"))
TITLE='公交刷卡换乘优惠与日封顶回算'
SHORT='transitcap'
COLUMNS=['event_id', 'card', 'route', 'event_time', 'result', 'reported', 'note']
MODULES=[('taps', '刷卡采信'), ('routes', '线路换乘'), ('fares', '票价版本'), ('journeys', '行程配对'), ('discounts', '优惠回算'), ('clearing', '清分对账'), ('settlement', '日结归档')]
RULE_VERSION="2026.11.19-r1"
# 现行线路归属：归并后的现行线路编码。旧编码经版本化对照表进入当前口径。
CURRENT_ROUTES=("01","02","03")
# 内置对照（旧版口径）：不含 1· 等更早期写法，作为首个生效版本落库。
BUILTIN_ALIASES={"01":"01","1路":"01","02":"02","2路":"02","03":"03","3路":"03"}
