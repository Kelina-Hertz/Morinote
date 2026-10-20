# Morinote IDE（无 AI 版）

版本：`0.2.21-no-ai.1`。面向 Windows，使用 Ren’Py 8.5.3。

这是仓库游戏的可视化编辑工具。IDE 源码独立放在 `creator/`，不参与游戏启动或发行；仍可直接通过 Ren’Py Launcher 运行根目录游戏。

## 使用免安装版

仓库包含 `portable/Morinote-IDE-0.2.21-no-ai.1-win-x64.zip`，通过 Git LFS 保存，内含 Electron、Python 和 Ren’Py 8.5.3。Windows x64 用户无需另装 Node.js、Python 或 Ren’Py，也无需构建源码。

1. 安装 Git LFS，在仓库根目录运行 `git lfs install`，然后运行 `git lfs pull` 下载免安装包及游戏素材。使用 GitHub Desktop 时，也应确认 LFS 文件已经完整下载。
2. 双击 [`启动IDE.cmd`](启动IDE.cmd)。首次启动校验压缩包并解压到 `.portable/`，可能需要等待；以后直接启动已解压版本。
3. 首次启动自动打开当前仓库的游戏，以后恢复上次工程；也可手动打开其他工程。

启动依赖 Windows 自带的 PowerShell 5.1，脚本仅为当前进程设置执行方式，不修改系统执行策略。若启动窗口提示下载的只是 LFS 指针，请先完成 `git lfs pull`。从 GitHub 网页下载的源码 ZIP 不保证包含 LFS 实体，推荐使用 Git + Git LFS 克隆。

无 AI 版使用独立的本机配置目录，不读取 AI 版的账号或密钥配置。解压缓存、构建目录和单独的开发 SDK 不进入 Git；**免安装 ZIP 和清单进入 Git**，不包含 Morinote 私有素材或 C2-1，游戏素材仍读取当前项目。

也可手动解压免安装 ZIP 后启动 `win-unpacked/Morinote IDE.exe`；要自动识别本仓库，请保持解压目录位于仓库内。若移到仓库外，启动后手动打开工程。

## 从源码构建

需要 Node.js 22 LTS、npm，以及 Windows 版 Ren’Py 8.5.3 SDK。

在 PowerShell 中：

```powershell
cd creator
npm ci
$env:CREATOR_RENPY_SDK = 'C:\Tools\renpy-8.5.3-sdk'
npm run build
npm start
```

`CREATOR_RENPY_SDK` 指向解压后的 SDK 根目录，其中应有 `renpy.py` 和 `lib/py3-windows-x86_64/python.exe`。也可将 SDK 解压到仓库根目录的 `renpy-8.5.3-sdk/`。

生成含运行依赖的免安装目录、仓库分发 ZIP 及校验清单：

```powershell
npm run package:dir
```

构建命令只编译打包，不自动启动游戏或运行测试。打包完成后同步更新 `portable/manifest.json`；仅重新压缩已构建目录可运行 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/package-portable.ps1`。发布新版本时一并提交版本配置、ZIP、清单和启动脚本，ZIP 使用 Git LFS 上传。

## 剧情图适配

首次打开现有 Morinote 时，直接从 RPY 建图并采用共享的场景名称预设，不依赖作者机器上的 `.creator` 缓存。用户自行改过的名称优先保留。默认展开第一章、按执行方向纵向排列，手机会话收进所属场景；末尾单一返回标题选项显示为一张收尾卡片，源码细节模式保留原步骤。

第一章主干为：噩梦醒后 → 百团巡游 → 摊位初遇 → 答题抽奖 → 与文竹同行 → 组织部宣讲 → 加入组织部。场景名称、摘要和分组仅是 IDE 展示配置，不更改剧情或原 label。总图不混入 OVA、系统功能或已识别的测试入口。

仓库存在带编号的同名脚本副本。默认剧情展示采用相同目录下无编号的原文件，并提供「同名副本」入口查看所有相关源码；完整控制流索引仍保留重复声明和不明确的运行目标。此展示规则不删除副本，也不解决 Ren’Py 本身的重复标签问题；原生运行仍需用户另行验收。

本轮仅更新 IDE、编译打包，未执行测试或试玩，不包含 C2-1。

## 功能

- 主线剧情总图、章节折叠、三轨编辑和多角色构图。
- 项目独立的虚拟素材库、临时替代、缺失占位和引用定位。
- 项目文件、Monaco 源码编辑、三方分块合并。
- 自动草稿备份、历史恢复、多文件保存中断恢复。
- 手机、通讯录、OVA、成就和游戏配置的已识别字段编辑。
- 原游戏／片段试玩、独立 Ren’Py 预览窗口、参数联动和立绘动作预览。
- 拖动面板、收起／拉出和中央编辑区最小宽度。
- 打开 Ren’Py 原生启动器构建游戏发行版。

本版本不含 AI 侧栏、API 配置、模型调用、任务副本或 AI 自动测试接口。正常使用不需要 API Key，也不调用模型服务。

## 使用 Codex 导入 Word 剧本

仓库提供共享 Skill：[morinote-word-import](../.agents/skills/morinote-word-import/SKILL.md)。在 Codex 中打开本仓库，提供 `.docx` 路径后可以直接说：

> 使用 $morinote-word-import 载入这个 Word 剧本，作为第二章的独立导入稿。保留原文、选项和手机聊天；缺失素材用占位，有合适差分则临时替代并保留缺失提示。更新 IDE 中的场景名称和分组，暂不接入主线，不运行测试或试玩。

Skill 在 `.agents/skills/` 中随仓库共享，不需要安装模型 SDK，也不需要开启 IDE 内置 AI。若当前 Codex 客户端未自动列出它，可以直接让 Codex 读取上述 `SKILL.md`。

导入过程为：

1. 保留原 Word，提取正文、表格位置、段落编号及附注信息。
2. Codex 区分对白、旁白、手机消息、分支、演出和制作备注。
3. 生成独立原生 RPY，复用现有人物及演出系统，登记缺失或临时替代素材。
4. 保存段落到文字节点、label 和源码行的对应关系，刷新 IDE 名称与总图分组。
5. 在 IDE 查看三轨和缺口；需要时再由用户发起试玩、正文确认或主线接入。

原稿与导入记录默认放在 `.creator/imports/<章节>/<版本>/`，不会自动提交 Git；新剧情源码位于 `game/creator_imports/<章节>/`，素材运行配置位于 `game/creator_assets/`。再次更新时沿用已有 label 和人工演出，不整章覆盖用户修改。

辅助脚本只负责提取、来源登记核对和索引刷新，不能单独理解剧情，也不是“一键把任意 Word 转成正确游戏”的转换器。由外部 Codex 执行 Skill，不改变此 IDE 的无 AI 版本定位。

## 游戏文件与保存

打开工程只建立索引和项目内 `.creator/editor/` 元数据，不重构原游戏。修改先进入编辑器；`Ctrl+S` 和部分试玩操作会保存对应源码，保存后的内容会影响游戏。

更改素材名称、分类和对应关系不移动或覆盖实际素材；首次保存素材库修改会创建 `game/creator_assets/asset_bindings.rpy`，供原生运行和打包读取。

`.creator/` 包含本地索引、草稿和恢复记录，不提交 Git。不要把它当成唯一的游戏版本备份。游戏发行使用 Ren’Py Launcher 的「构建发行版」，无需包含 IDE。

## 当前范围

以 Morinote 为适配工程；复杂 ATL、自定义显示对象和动态表达式保留源码入口，不保证完整可视化解析。热更新可能从场景测试入口重启。

本次交付进行了静态复核和编译打包；按项目约定，未运行自动测试、故障注入或游戏试玩。保存恢复、素材替代和原生发行效果仍需后续专项验收。

共享 Skill 及其 Word 辅助脚本进行了源码编写和语法检查，未在本次任务中实际导入 Word 或运行生成章节。
