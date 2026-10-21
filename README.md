# 原来在动漫社真的能邂逅美少女！

> **Morinote** —— A galgame demo produced by Aoikaze,HUST

![Ren'Py](https://img.shields.io/badge/Ren%27Py-8.3%2B-ff69b4)
![Version](https://img.shields.io/badge/version-test__demo-blue)
![Language](https://img.shields.io/badge/language-简体中文-brightgreen)
![Resolution](https://img.shields.io/badge/1920×1080-informational)
![Status](https://img.shields.io/badge/status-开发中-orange)

---

## 目录

- [原来在动漫社真的能邂逅美少女！](#原来在动漫社真的能邂逅美少女)
  - [目录](#目录)
  - [游戏简介](#游戏简介)
  - [已实现系统](#已实现系统)
  - [快速开始](#快速开始)
    - [使用 Ren'Py Launcher（推荐）](#使用-renpy-launcher推荐)
    - [构建发行版](#构建发行版)
  - [项目结构](#项目结构)
    - [关于仓库内容](#关于仓库内容)
  - [开发进度](#开发进度)
  - [制作人员](#制作人员)
  - [素材与授权说明](#素材与授权说明)
  - [免责声明](#免责声明)

---

## 游戏简介

| 项目 | 内容 |
|---|---|
| 类型 | 日常 / 校园 / 恋爱喜剧，视觉小说 |
| 引擎 | [Ren'Py](https://www.renpy.org/) 8.3+（Python 3.12） |
| 分辨率 | 1920 × 1080 |
| 语言 | 简体中文 |
| 当前版本 | `test_demo`（第一章试玩） |
| 游玩时长 | 约 20 分钟（Demo 主线内容，视阅读速度） |
| 平台 | Windows |

---

## 已实现系统

- **手机聊天系统** —— 仿 QQ / 微信的对话界面，支持己方 / 对方 / 旁白三种气泡、头像、逐条发送音效。
- **通讯录系统** —— 联系人与群聊列表、最后一条消息预览、未读红点与数字（超过 99 显示 `99+`）、好友申请弹窗（同意 / 拒绝）。
- **音量分轨** —— 音效、音乐、语音三轨独立调节（Ren'Py 内置混音器）。
- **OVA 阅读系统** —— 独立的篇章阅读界面，记录已读进度。
- **成就系统** —— 基于 Ren'Py 原生 `achievement` 模块，内置 7 个成就，支持 Steam 同步。
- **UI 音效** —— 按钮悬停 / 点击音效统一挂载。（注：当前音效已被撤换，目前此功能暂时为空）

---

## 快速开始

### 使用 Ren'Py Launcher（推荐）

1. 到 [Ren'Py 官网](https://www.renpy.org/latest.html) 下载 **Ren'Py 8.3 或更新版本** 的 SDK 并解压。
2. 运行 `renpy.exe`（macOS 为 `renpy.app`）打开 Launcher。
3. 把本项目文件夹放到 Launcher 的**项目目录**下（或修改 `偏好设置 → 项目目录` 指向本项目所在路径）。
4. 在项目列表中选择 `Morinote`，点击 **启动项目**。

### 构建发行版

Launcher 中选中项目 → **构建发行版（Build Distributions）** → 勾选目标平台 → **构建**。
产物位于项目根目录的 `dist/` 下。

> 代码中已通过 `build.classify` 排除 `**.bak`、`**~`、`thumbs.db` 等临时文件，PSD 源文件不会被一起打包。

---

## 项目结构

```
Morinote/
├── game/
│   ├── script_c1a.rpy          第一章 A 节游戏脚本
│   ├── script_c1b.rpy          第一章 B 节游戏脚本
│   ├── script_c1c.rpy          第一章 C 节游戏脚本
│   ├── message.rpy             手机聊天剧本（phonemsg_* 标签）
│   ├── message_system.rpy      聊天界面布局与气泡样式
│   ├── contact_system.rpy      通讯录 / 好友申请 / 未读计数（demo阶段暂未启用）
│   ├── achievements.rpy        成就表与解锁逻辑
│   ├── ova.rpy                 OVA 目录与阅读界面
│   ├── ova_script.rpy          OVA 篇章正文（目前以test_OVA作为临时脚本，正式OVA完成后将替换）
│   ├── screens.rpy             全局界面定义
│   ├── gui.rpy                 界面样式与配色
│   ├── options.rpy             游戏配置（标题、版本、存档目录等）
│   ├── settings.rpy            立绘 / 场景图像定义与位置参数
│   ├── 00_ui_sounds.rpy        UI 音效挂载（目前暂未启用）
│   ├── audio/                  BGM 与音效（.mp3 / .ogg）
│   ├── gui/                    界面素材、场景背景、角色立绘、头像等UI组件
│   ├── images/                 道具图标等杂项图片（现阶段暂未使用）
│   ├── characters/             立绘源文件（仅作存档）
│   ├── test_script/            界面定制脚本（与测试脚本无关，仅为临时UI设计脚本，后期将进行替换）
│   ├── tl/                     翻译文件
│   ├── cache/                  运行时生成的字节码缓存（可删）
│   └── saves/                  存档与 persistent 数据（构建发行版将自动删除）
├── project.json                Ren'Py 工程描述文件
└── .vscode/settings.json       编辑器排除规则
```

### 关于仓库内容

本仓库按**完整工程目录**上传，包含源码、美术源文件、音频与运行缓存。其中：

- `game/cache/`、`game/saves/`、`*.rpyc` 为运行时自动生成，删除后 Ren'Py 会重新编译生成；
- `game/saves/` 内是本机测试存档，与游戏逻辑无关；
- `game/gui/characters/**/*.psd` 为美术源文件，游戏运行不需要，现保留以便后续修改。

---

## 开发进度

- [o] 手机聊天 / 通讯录 / 好友申请核心系统
- [o] 成就系统与 Steam 对接预留
- [o] OVA 阅读模块
- [o] 第一章 A 节（`C1a`）
- [o] 第一章 B 节（`C1b1` – `C1b3`）
- [o] 第一章 C 节（`C1c1` – `C1c3`）
- [ ] 第一章演出细化与文本校对打磨
- [ ] 正式版 UI 与配乐替换
- [ ] OVA脚本制作与替换

> 当前为**试玩测试版**，不代表最终版本的内容与品质。

---

## 制作人员

| 职位 | 成员 |
|---|---|
| 总策划 | 小野寺日向 |
| 原案 & 编剧 | HUST基米 |
| 脚本 | 洛鸢羽、HUST基米 |
| 作画 | 枝冬 |
| 美术设计 | Ela |
| 背景 CG | Venwil |
| 音乐 | 洛鸢羽、柯良、ハサミ |
| 制作 | 洛鸢羽、Ela、框 |


---

## 素材与授权说明

- `game/audio/` 下的 BGM 、`game/gui/` 下的美术资源归对应的音乐制作人员与作画人员所有。
- 引擎与运行库版权归 [Ren'Py](https://www.renpy.org/) 项目及其贡献者所有。

---

## 免责声明

本作品纯属虚构。游戏中一切人名、地名、组织名等均为架空设计，与现实无任何关联，如有雷同纯属巧合。
本作品适合 **14 周岁以上**人群，所有登场人物均已年满十八周岁。
制作组保留对游戏内容的最终解释权。



## 可视化 IDE

仓库新增独立的 [`creator/`](creator/README.md) 开发工具，版本 `0.2.21`。支持剧情总图、三轨、素材库、源码编辑、草稿恢复和 Ren’Py 试玩。

仓库已包含 Windows x64 免安装包（`creator/portable/`，由 Git LFS 保存），内含 Electron、Python 和 Ren’Py 8.5.3，无需另外安装 Node.js、Python、Ren’Py 或构建源码。

使用 Git + Git LFS 克隆仓库后，在仓库根目录运行：

```powershell
git lfs install
git lfs pull
```

然后双击 [`creator/启动IDE.cmd`](creator/启动IDE.cmd)。首次启动校验压缩包并解压，之后直接启动；首次使用自动定位当前仓库的游戏。游戏图片、音频等 LFS 素材也需要完整下载。从 GitHub 网页下载的源码 ZIP 不保证包含 LFS 实体。

开发构建说明见 [creator/README.md](creator/README.md#从源码构建)。免安装 ZIP 与校验清单进入 Git；解压缓存、开发依赖和构建目录不提交。

IDE 独立于游戏：原有 Ren’Py 启动和构建方式继续使用。添加开发工具不会改写游戏文件；之后在 IDE 中保存的剧情和素材配置会写入对应源码。

### Word 剧本导入

提供共享 Skill：[morinote-word-import](.agents/skills/morinote-word-import/SKILL.md)。在 Codex 中打开本仓库并提供 Word 文件，可说：

> 使用 $morinote-word-import 将这个 Word 剧本导入 IDE，保留原文和分支，缺素材使用占位或临时差分

Codex 负责理解剧本和生成原生 RPY；附带工具提取 Word、核对段落来源并刷新 IDE 索引。详细流程见 [IDE README](creator/README.md#使用-codex-导入-word-剧本)。



