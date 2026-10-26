# IDE 结构与数据归属

## 修改如何进入游戏

原工程 RPY → IDE 当前编辑稿 → DSH 原生文件工具或 Morinote 适配器 → 共享源码服务的版本检查 → 源码事务保存涉及文件 → 编辑器同步及差异记录 → Ren’Py 原生执行。

AI 正常编辑直接生效，不需要先创建副本或点击应用。未保存的手工输入也是读取与编辑的基础；保存同一文件会保留其中的手工内容，不顺带保存其他文件。只读索引和草稿备份不能代替当前编辑稿。

| 层 | 职责 |
|---|---|
| React NativeWorkbench、SourceEditor | 当前源码缓冲区、三轨、配置、Hot Exit 与统一保存队列 |
| Electron source-service | 所有会话共用的源码访问、版本检查、提交台账、差异与撤销 |
| Electron ai-live-manager | 项目内独立会话、排队与引导、权限请求及独立审核 |
| 独立 Node dsh-worker | 锁定 SDK、原生会话历史、流式消息、恢复 |
| ide-filesystem 插件 | 实现 DSH ctx.fs，复用原生 read/write/edit 与 fs-observation-policy |
| morinote 插件 | 三轨、Voice、流程、配置、素材适配器；隔离执行、试玩、截图 |
| Python workspace、native_* | 源码事务、中断恢复、解析及既有可视化编辑逻辑 |
| game/ | 用户游戏的原 RPY、Python 与实际素材；只有允许的文本源码可写 |
| .creator/ai/tasks | 检查、试玩和通用终端使用的内部隔离快照，不是日常编辑的副本审核流程 |

## 界面与源码

项目文件和源码编辑器打开同一文档；整个游戏一张剧情总图，章节是分组，手机等系统实现在剧情调用处显示。场景三轨以稳定文字节点推进，画面与音乐按执行顺序继承，Voice 附着台词。素材库分开记录虚拟条目、运行标签与实际资源。复杂 ATL、Screen 和动态表达式保留源码执行。

`morinote_project` 仅返回概览及选择上下文；`morinote_workspace` 根据 section、sceneId、groupId 和分页参数返回当前需要的编辑内容。scene ID、文字 ID、图片标签、人物实例 tag、素材 ID、源码行号不能互换；编辑后重新查询定位。

多个会话可同时工作；提交阶段统一排队。普通文件工具必须先读后改，过期版本返回 FS_STALE_VERSION。`operate` 前读取所需 workspace 分组或素材；之后再次编辑先刷新受影响内容，不能把旧定位或旧版本用于后续修改。外部程序修改由磁盘摘要检查发现，必要时在 IDE 合并。

图片、音频、字体等实际资源只读，通过虚拟素材适配器处理更换与缺失。不能直接写编辑器索引、恢复数据、确认记录或 API 凭据。IDE 本身源码不属于游戏编辑工具的写入范围。游戏发行使用 Ren’Py 启动器的“构建发行版”。
