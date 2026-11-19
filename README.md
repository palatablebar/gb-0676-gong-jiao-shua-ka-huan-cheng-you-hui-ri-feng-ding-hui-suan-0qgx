# 公交刷卡换乘优惠与日封顶回算

供公交清分中心复核员核对原始记录、处理差异并封存证据。

## 启动

```sh
docker compose up --build -d
docker compose exec -T app pytest -q
```

打开 http://localhost:18245 。首次进入自动运行仓内脏样例。工具条可重跑、切换样例或上传CSV。SQLite保存在命名卷records中，重建服务保留批次。

## 模块

- 1. 刷卡采信：`/taps`，`/api/taps`。
- 2. 线路换乘：`/routes`，`/api/routes`。
- 3. 票价版本：`/fares`，`/api/fares`。
- 4. 行程配对：`/journeys`，`/api/journeys`。
- 5. 优惠回算：`/discounts`，`/api/discounts`。
- 6. 清分对账：`/clearing`，`/api/clearing`。
- 7. 日结归档：`/settlement`，`/api/settlement`。

## 核心规则

换乘按上次有效付费行程的时间窗计算，优惠与日封顶按确定顺序裁决并保留分币守恒。旧编码经版本化对照表进入当前口径：记录保留route_legacy原码，route归一到现行线路；封存批次不改写，按生效对照派生唯一迁移批补算换乘与日封顶，重跑复用不新增，未对平不得迁移与封存。

## 演示

1. 打开首页，核对当次计算、差异和隔离原因。
2. 切换模块查看源行及裁决依据。
3. 重跑相同样例，批次号与行数保持一致。
4. 复核后导出一份证据CSV。版本已变化的复核提交返回409。
5. 运行legacy.csv，`/routes`可见1·等旧编码被隔离；在对照面板加入`"1·":"01"`并提交生效，失败时旧版保留。
6. 点迁移重算生成迁移批，`/clearing`并列旧编码、现行线路、旧批应扣与迁移差额；再次迁移复用同一批次，原批不变。

## 输入与输出

输入列见 `docs/DATA-DICTIONARY.md`。项目包含dirty.csv、clean.csv、legacy.csv，统一走实际导入路径。上传限制4MB，拒绝不带时区的时间。业务键按字符串保留，Decimal参与计算，空值不会当零。

`POST /api/runs` 接收sample或csv；`GET /api/runs`返回历史批次；`POST /api/runs/<id>/review`需要version与decision；`GET /api/runs/<id>/archive`返回唯一证据导出。`GET/POST /api/aliases`与`POST /api/aliases/<id>/activate`管理线路对照版本；`POST /api/runs/<id>/migrate`按生效对照生成唯一迁移对账批。

## 范围

样例均为虚构。单机复核工具不连接生产系统；不提供登录、远端数据库或自动支付。内存计算按4MB输入上限控制，SQLite事务保证结果完整写入。

## 目录

app为服务与规则，sample_data为输入，tests为测试，docs为定义与深度登记。
