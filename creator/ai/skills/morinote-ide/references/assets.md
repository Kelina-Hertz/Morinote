# 虚拟素材与缺失需求

用 `morinote_assets` 读取 `library.entries/resources/labels` 和项目素材。素材只属于当前工程，ID 不在其他项目间通用。显示名用于阅读；运行标签／路径用于执行；实际文件保留原名与位置。

| 对象 | 意义 |
|---|---|
| 虚拟条目 | 稳定 id、显示名、类型、角色／服饰／表情、需求、运行标识和绑定 |
| 图片标签 | Ren’Py 完整图片定义，可包含内置变换；同一文件的不同标签不能合并 |
| 实际资源 | 当前工程已登记的物理文件，只读；不能用工程外路径建立隐式共享 |
| 画面实例 | `show ... as tag` 中的在场对象；不是图片文件或素材库条目 |

状态 `unbound/broken/temporary/bound` 是内部值。面向用户讲清楚“缺失什么”“现用什么临时替代”；无需给正常卡片附“可用／正式绑定”等标签。临时替代仍属待补，不能清空需求或声称素材已经补齐。

所有操作通过 `morinote_operate(adapter="assets", operation=...)`，写入副本的 `game/creator_assets/asset_bindings.rpy`，保留原标签引用。

新建缺失项：
```json
{"adapter":"assets","operation":{"operation":"create","name":"汐泉·女仆装·微笑（待补）","type":"sprite"}}
```
类型为 `sprite/background/cg/bgm/ambience/sound/voice/interface/unknown`。创建后重新查询取得新 ID 和运行标识。它没有绑定文件时使用项目的占位支持；缺图片显示需求，缺音频静音，不能假称已经生成新美术或配音。

设置分类与具体需求：
```json
{"adapter":"assets","operation":{"operation":"update","id":"VIRTUAL_ID","values":{"character":"汐泉","costume":"女仆装","expression":"微笑","requirement":"需要女仆装微笑差分"}}}
```

临时使用已有差分标签：
```json
{"adapter":"assets","operation":{"operation":"bind","id":"VIRTUAL_ID","binding":{"kind":"label","key":"EXISTING_FULL_IMAGE_TAG"},"temporary":true}}
```
或选择当前 resources 中的原文件，使用 `binding:{"kind":"file","key":"images/EXISTING.png"}`。key 是 `nativeGamePath`，不加 `game/`，也不使用绝对路径。AI 工具把更换视为临时替代，不负责把缺失项认证为补齐。

`unbind`、`id` 取消更换后回到占位；`delete`、`id` 删除无引用的虚拟条目，不删除任何实际文件。有引用时不能删除，应保留条目并明确需求。重命名只用 `update.values.name`，不能重命名运行标签或资源文件。

已有图片标签带缩放时，引用其原定义，不再套相同缩放。复杂定义／自定义显示对象无法可靠静态预览时保留原定义与源码入口。不要把用户未提供的服饰、场景、CG 或音乐视为“已有素材”，也不要通过覆盖只读资源绕过缺失状态。
