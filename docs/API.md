# 接口

模块GET使用仓内样例，模块POST可传csv或rows与context，直接计算当前规则。/api/runs使用完整流水线并原子保存。每个阶段返回rows、quarantine、metrics；后续阶段还返回累计隔离。/api/upload接收multipart文件file。/api/runs/<id>/archive只导出一份带清单与证据的CSV。

线路对照：`GET /api/aliases`返回生效版本与全部版本；`POST /api/aliases`接收{"mapping":{旧编码:现行线路}}登记草稿，内容寻址，重复提交不新增；`POST /api/aliases/<id>/activate`原子生效，目标非现行线路或缺少恒等映射时返回422并保留旧版。

迁移对账：`POST /api/runs/<id>/migrate`按当前生效对照重算该批换乘与日封顶，返回迁移批；迁移批ID由（原批ID、对照版本、规则版本、规范输入）唯一确定，重复调用复用同一结果，原批不变。旧批未对平时返回422。
