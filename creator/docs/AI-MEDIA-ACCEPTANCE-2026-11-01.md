# Seedream＋MiniMax 实施及验收记录

后续真实验收已补充，见 [真实 API 与同批产物离线复跑](AI-MEDIA-LIVE-ACCEPTANCE-2026-11-01.md)。本文保留初次 mock 验收当时的结果。

日期：2026-11-01。代码基线：GitHub/Morinote `0928860` 加现有 0.4.3 未提交改动；DSH 固定 `22ddee3792402c3e70ec5f86a63c3e3e895a2f60` / `0.2.1-rc.3`，未升级。Ren’Py 实测版本 `8.5.3.26051504`。

## 验收结论

| 项目 | 结果 | 证据与范围 |
|---|---|---|
| mock 契约与故障测试 | 已通过 | 默认 Node 测试含 24 项媒体契约／故障测试；供应商调用均由注入传输替代 |
| 真实侧栏＋DSH 工具链 | fixture 已通过 | 正常对话输入、既有 checkpoint、受管入库、源码事务、lint、真实预览启动及打开三轨；本机假文字服务，云 API 为零 |
| 低额度计量 | fixture 已通过 | 真实 HTTP 代理链路、上游请求前预占、总输出限制、第四次请求拒绝、未知结果保持预占；不是服务商账单验收 |
| 原生编辑 | 已通过 | 两路线内嵌同 label，稳定节点、Voice 过期、格式转义、源码整批撤销／重做保留媒体；新测试接入默认命令 |
| 真实引擎试玩 | fixture 已通过 | Ren’Py 原生测试两条路线、返回标题、Voice 声道正在播放，含引擎截图 |
| 保存、编辑、离线重开 | fixture 已通过 | 台词修改后 Voice 显示待更新，同一图片／音频摘要不变，再次跑完两路线，API 为零 |
| 真实 Seedream／MiniMax API | **未执行** | 本机没有已配置媒体凭据；没有为探测而发付费请求 |
| 真实成果离线复跑 | **未执行** | 尚无真实付费产物；fixture 复跑不能替代该项 |
| 人工听音与真实媒体质量 | **未验收** | fixture 音频仅为 0.5 秒测试音；解码和 Voice 声道断言不等于人工听音或真实配音质量 |

## 已交付实现

- 独立加密媒体设置、Seedream／MiniMax 原生 HTTP 适配器、统一请求／结果／任务类型与聚合 `generate_fragment` 工具。
- 持久额度和任务台账、跨并发预占、重复提交缓存、取消、未知结果、重启恢复及已生成产物恢复绑定。
- 仅接受宿主凭证的受管入库；生成目录和文件名由后端决定，实际格式／解码／大小校验，项目内非覆盖发布。
- 单个顶层 label、两条内嵌分支、原生三轨、虚拟素材绑定、逐句 Voice 来源和待更新状态；复用源码事务、差异、撤销与恢复。
- 可收起进度卡、图片／音频预览、真实提交次数、计费字符和预计费用；素材／片段／试玩／恢复入口。
- 更新按需读取的 DSH `media` 指南及受管写入边界，不在每轮自动加载完整源码或三轨。

音乐、独立音效、视频生成保留待开发接口并拒绝提交。README、正式游戏、已有素材及当前文字模型配置未改动；未提交、推送、发布或重打免安装包。

## 执行记录

默认检查使用 `CREATOR_TEST_PYTHON` 指向本机现有 Python，`CREATOR_RENPY_SDK` 指向已有 8.5.3 SDK：

```text
node scripts/test.cjs
node node_modules/vite/bin/vite.js build
electron electron/tests/run-media-fragment-fixture.cjs
electron electron/tests/run-media-fragment-fixture.cjs --low-cost
python -B scripts/test-media-engine.py --project .test-projects/media-fragment/fixture-c5032e9d --label creator_fragment_21f1900c2c3f3e4ffbea0bc2
```

类型检查、默认 Node 30 项、renderer 11 项、Python 后端 176 项全部通过；构建通过，仅有 Monaco 常规包体积提示。片段专用 Python 测试 10 项通过，包括新增的整批撤销与重做。完整输出见随附 `test-full.log`。

官方 Skill 验证脚本因本机缺少 PyYAML 未能运行；另用已安装的 YAML 解析器检查了 Skill 元信息及全部引用文档路径，通过。未为此安装依赖。

桌面截图工具两次捕获超时后停止重试。GUI 应用内截图和 Ren’Py 原生截图可用；不把操作系统截图失败表述为通过。

## 自然语言与用量

测试从正常侧栏发送：

> 做一个一分钟左右的雨夜校园片段。我在校门口遇见忘带伞的同学，可以选择送她回家或把伞借给她，最后都有各自的回应。新画一张雨夜校门背景，只给她第一句台词配音，其他素材优先用已有的，没有合适立绘就只显示背景和对话。

最终低额度 fixture 记录 `87f79807-868e-403a-ae77-f1781e28912d`：

| 项目 | 计数 |
|---|---|
| 真实云端请求／费用 | 0 / 0 |
| 本机 fixture 文字 HTTP | 2 次：规划、结果总结 |
| 文字输出 | fixture usage 分别 300、50，总计 350 tokens；并非真实模型账单 |
| 文字输入 | 按体积估算 4,415＋4,168＝8,583 tokens；fixture usage 报告各 100，分别保留 |
| 媒体提交 | fixture 图片 1 次、配音 1 次 |
| 配音文本 | `我忘记带伞了。`，估算计费字符 13 |
| 媒体预占 | 估算 0.30455 元，仅用于测试额度，不产生真实费用 |
| 重试／压缩 | 低额度会话均关闭 |

Seedream 适配器发送 `doubao-seedream-5-0-pro-260628`、2048×1152、单图请求，不发送 Pro 不支持的流式／组图参数。MiniMax 默认中国站、`speech-2.8-hd`、`female-shaonv`、非流式 MP3，并校验业务状态、解码十六进制音频。fixture 实际输出明确为纯色 PNG 和 WAV 测试音，未伪装成这些服务的真实结果。

## 产物、路线及证据

最终独立样例：`.test-projects/media-fragment/fixture-c5032e9d/`。

- label：`creator_fragment_21f1900c2c3f3e4ffbea0bc2`
- 片段：`game/creator_fragments/fragment_21f1900c2c3f3e4ffbea0bc2.rpy`
- 图片 SHA256：`90c84160db871be317305be27439a614926ef6d648c7dc3c8aec5fb5f9fe5beb`
- 音频 SHA256：`ce225626c731a97a06ec872e3ebcbb19c5920f32ed7812d74cbd8f11933561b5`
- “送她回家” → “谢谢，我们一起走吧。” → 结尾 → 标题，通过。
- “把伞借给她” → “明天我会把伞还给你。” → 结尾 → 标题，通过。
- 引擎：2 个 testcase、3 个 hook、1 个 Voice 播放断言全部通过。

另一份已保存 fixture `fixture-e4a48808` 通过原生编辑事务将第一句改为“我今天忘记带伞了。”，重开后 `voiceStale=true`，媒体摘要不变，随后复跑两条路线通过；归档中仅保留其编辑恢复结果，不复制额外任务和缓存。

证据位于忽略目录 [`.checks/media-fragment-acceptance/`](../.checks/media-fragment-acceptance/)：`report.json`、`test-full.log`、`engine-report.json`、`engine.log`、`roundtrip.json` 和 GUI／原生引擎截图。不含 Key、加密配置、DSH 会话或任务副本。截图中的纯色背景及测试音属于 fixture。

## 验收中修复的问题及剩余工作

- Windows 深路径的 JSON 临时文件改用短名称，避免任务结果落盘失败。
- 修复非原生文字协议适配器的插件切换；保留固定 DSH 版本。
- 受限执行器为专用测试副本增加精确的只读权限，解决 LUA 进程无法读取快照；不修改原工程权限或扩大可写范围，无法建立限制时仍拒绝执行。
- 生成产物预览随项目素材版本刷新；补充图片真实解码尺寸与音频元数据断言，修复“已生成但预览破图”。
- 增加不同声线配置的缓存区分、媒体台账损坏时仅暂停媒体、供应商异常脱敏等故障保护。

下一步在新界面的媒体设置中录入两家 Key，再从“低额度验收对话”发送同一需求。首次真实失败或凭据缺失时保留记录，不增加收费次数。真实 API、真实图片／配音试听、同批真实产物的离线重开与路线验收仍需完成；不能以本报告的 mock 结果代替。
