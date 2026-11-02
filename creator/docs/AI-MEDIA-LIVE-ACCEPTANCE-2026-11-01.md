# Seedream＋MiniMax 真实限额验收

日期：2026-11-01。承接 [初次离线验收](AI-MEDIA-ACCEPTANCE-2026-11-01.md)。本次用户提供媒体凭据后，完成真实 API、原生游戏与同批产物离线复跑；没有重新打包、提交或推送。

## 结论

| 范围 | 结果 |
|---|---|
| 媒体凭据 | 经新增媒体设置保存到本机原有 `Morinote-IDE-Offline` 配置，Electron 安全存储加密；不写项目或测试脚本 |
| Seedream 真实 API | 1 次提交、1 张有效 2048×1152 JPEG，已入库、绑定并实际显示 |
| MiniMax 真实 API | 1 次提交，短句“我忘记带伞了。”，13 计费字符，MP3，约 1.4 秒，已绑定 Voice |
| 原生源码与修改确认 | 独立 RPY、两个内嵌选项、稳定节点注释、虚拟素材、同批保存；从正常侧栏发送需求并经过既有 checkpoint |
| lint／真实游戏 | 通过；两条路线分别回应并返回标题，指定台词时 Voice 声道正在播放 |
| 真产物离线编辑／重开 | 通过；三轨修改旁白、保存、退出后重新打开，编辑内容仍在，两个媒体摘要及调用计数不变 |
| 真产物离线复跑 | 通过；重开后再次跑通两路线，真实云请求增加为零 |
| 音频播放 | Chromium 播放器实际播放时间前进、解码时长有效；Ren’Py Voice 断言通过。尚未进行人工主观听音评价 |
| AI 最终文字总结 | **未完成**。真实制作已成功，但总结请求被输入估算额度拦在本机；没有放宽额度或追加请求 |

因此本次证明“真实媒体＋可编辑可玩原生片段”闭环可用，不能写成“自然语言到最终 AI 总结全程无误”。原生引擎和媒体证据独立于 AI 是否完成总结。

## 过程与保护

1. 使用正常 AI 侧栏及原有 `deepseek` / `deepseek-flash` 文字模型，没有额外付费连接测试。
2. 第一次计划含 6 条共用文字、两个分支各 3 条、结尾 1 条，共 13 条，且自行填写了不支持的配音参数。本地校验拒绝，图片和配音提交均为零。
3. 原对话的后续请求被输入额度拒绝。保留完整原记录，在共用同一个持久额度的独立修正对话中使用唯一一次收费前计划修正；没有清空台账或伪造成功。
4. 补充工具说明：6–12 句指所有分支合计；配音省略参数即继承配置，并列出允许的情绪。修正计划为共用开头 3 句、两个选项各 1 句、共用结尾 1 句，只有指定句子带 `voice:{}`。
5. 两个真实媒体任务均成功，源码入库／绑定、修改确认、lint 和片段预览已执行。后续模型总结被输入预算保护拦住，因此停止模型调用，以同一批真实产物继续离线验收。

本次媒体模型分别为 `doubao-seedream-5-0-pro-260628` 和中国站 `speech-2.8-hd`，声线沿用 `female-shaonv`。图片保留服务默认 AI 水印。没有自动重试、切换模型、生成音乐／音效或新增主线入口。

## 实际调用及 usage

持久额度 ID：`acceptance-live-c1ee9ae3583d38985c3b6895b49e37e7`。

| 项目 | 真实结果 |
|---|---|
| 文字模型上游 HTTP | 2 次：首次计划、唯一修正；最终总结仅在本机被拦截，不计为上游请求 |
| 文字输出 | 831＋472＝1,303 tokens，未结算预占为 0 |
| 文字输入估算 | 4,884＋5,481＝10,365，未超过已提交请求的单次 8,000／总计 16,000 限制 |
| 文字服务原始 usage | 首次 `input_tokens=1396, output_tokens=831`；修正 `input_tokens=1170, cache_read_input_tokens=384, output_tokens=472` |
| 图片提交／产出 | 1／1；图片服务 usage：`generated_images=1, output_tokens=9216`，此为图片服务自己的计量，不是文字模型输出 |
| 配音提交 | 1；`usage_characters=13, audio_length=1476ms`；本机 MP3 解码约 1.405 秒 |
| 媒体费用预占 | 估算 ¥0.30455；未读取平台账单，不宣称是实际扣款金额；文字服务费用另计 |
| 离线阶段新增请求 | 文字 0、图片 0、配音 0 |

## 独立工程、文件与证据

工程：`.test-projects/media-fragment/live-rain-campus/`，已在项目忽略规则内。

- 入口：`creator_fragment_43c68f99ca778f2b09a1bbc7`
- 源码：`game/creator_fragments/fragment_43c68f99ca778f2b09a1bbc7.rpy`
- 背景：`game/images/creator_generated/14e41f9585c346089c46/output.jpg`
- 配音：`game/audio/creator_generated/f1c1c4cc6a3145349d5d/output.mp3`
- 图片 SHA256：`8a73b1a3ef830059db305db0ac7d27245eb7a56b045d1a93b1fc2bc5b6d0585f`
- 配音 SHA256：`4b44253cc3910dc10539d99152461c32a7b8f371aab201c3cb838d752903a9b1`

两条路线：

- 送她回家 → “那就……拜托你了，我们一起走吧。” → 片段结尾 → 标题。
- 把伞借给她 → “真的可以吗？谢谢你，明天我一定还给你。” → 片段结尾 → 标题。

原始与重开后的 Ren’Py 测试各通过 2 个 testcase、3 个 hook、1 个 Voice 断言。通过三轨将第一条旁白改为“雨下得很密。我撑着伞走到校门口，校门外的灯光映在水面上。”后保存并重开，图片、配音不变，台词与 Voice 的来源记录仍然匹配。

脱敏记录：

- `.checks/media-fragment-live/711adad1-936f-4d4b-88fe-2ce3da06f8c4/report.json`：首次计划拒绝，未提交媒体。
- `.checks/media-fragment-live/aaf66f6b-5355-4344-bf4b-e75a84658f97/playable.json`：真实计划、产物摘要与 usage；其 `report.json` 保留自动总结失败的原始结果，不改成成功。
- 同目录 `engine-original/`、`engine-reopened/`：真实 Ren’Py 记录。
- `.checks/media-fragment-live/offline-edit/`、`offline-reopen/`：正常 IDE 的试听、三轨修改保存、重启恢复与截图。
- 工程 `tests/screenshots/media_live_*.png`：真实画面、选项、两条回应。

![真实媒体三轨编辑](../.checks/media-fragment-live/offline-reopen/tracks.png)

![真实引擎分支](../.test-projects/media-fragment/live-rain-campus/tests/screenshots/media_live_route_1.png)

## 后续零费用复跑

不要为了查看效果重新运行生成器。直接用更新后的开发版 IDE 打开上述工程，从生成片段卡片“打开片段／试玩”，或使用下面的专用脚本。原有免安装包仍未包含本轮功能。

```powershell
# 在 Creator 目录，先配置已有 Ren’Py SDK 路径。
$env:CREATOR_RENPY_SDK = '你的 renpy-8.5.3-sdk 完整路径'
python -B scripts/test-media-live-engine.py --record .checks/media-fragment-live/aaf66f6b-5355-4344-bf4b-e75a84658f97/playable.json --tag reopened
```

`run-media-fragment-offline.cjs --verify-reopen` 会拒绝发送对话、恢复 Agent、连接测试和媒体提交，只读取已保存产物。`run-media-fragment-live.cjs` 是显式收费验收工具，需要 `--allow-bounded-live`；其一次性本机凭据入口不把 Key 放在命令行、环境变量或文件中。当前持久额度已经提交图片和配音，脚本禁止再次开始新的付费验收。

剩余事项：低额度下的自动总结应进一步缩小上下文并清楚区分“制作成功、总结未完成”；本次没有为验证该优化再调用真实模型。已有媒体契约回归 24 项再次通过。未修改 README、正式剧情或已有素材；未重新打包。
