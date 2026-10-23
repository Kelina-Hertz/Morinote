# B「剪贴色签」游戏接入

2026-10-23，用户选择新主视觉配套菜单 B 和其 UI 精修版，替换旧界面。这里的 B 对应美术目录 `main-visual-menu-1013` / `ui-elements-1013-v02`，与早期 1002 方案无关。

## 资源位置

| 位置 | 内容 |
| --- | --- |
| `game/gui/qingfeng/main_visual.png` | 已确认的 1920×1080 主视觉，保留主美 Logo；移除旧底部五个图标 |
| `game/gui/qingfeng/menu/` | 六项主菜单的默认、焦点、激活、禁用 PNG |
| `game/gui/qingfeng/components/` | 无字底板、按钮、选项、快捷菜单、标签、存档卡、滑条、开关、确认弹窗及状态 |
| `game/gui/qingfeng/icons/` | 规定枫叶与功能图标 |
| `game/gui/qingfeng/manifest.json` | 美术源文件相对路径和 SHA-256 |
| `game/fonts/qingfeng/` | 完整字体及 OFL 许可证 |
| `game/qingfeng_ui.rpy` | 本轮全部屏幕与共用样式，晚于旧界面初始化 |

源图、背景与人物未重绘。主视觉沿用美术项目已批准的缩放版；Logo 的构图、比例和颜色保持该版本。枫叶来自规定的 `旧物料/window_icon.png` Alpha。运行游戏不需要美术项目或 Photoshop。

## 接入内容

- 六项主菜单：开始、读取、小说模式、成就、设置、退出。
- 剧情阅读底板、动态宽度姓名签、正文、继续标记、可滚动选项。
- 八项快捷操作；快进/自动具有持续开启状态。
- 设置的阅读、声音、显示、快进四页，滑条和开关直接操作 Ren'Py Preference。
- 保存/读取六格存档、页码、自动/快速页、页名编辑、实际截图、时间、长标题缩略显示；Delete 删除保留引擎确认。
- 通用确认弹窗，以及历史、关于、帮助、成就、小说目录与小说阅读界面。

正文为原 `SourceHanSansLite.ttf`；组件标题和短按钮为 Chiron GoRound SemiBold，其余 UI 文本为 Medium。主菜单继续使用原设计中已排好的思源黑体 Heavy 字形 PNG。字体完整、可离线运行。

`init offset = 20` 统一覆盖旧屏幕，不删除历史素材，不改变剧情标签或存档槽命名。原 Character 注入的 `window/namebox/say_*` 样式同步指向 B，避免旧蓝色姓名框和对话底板残留。后续调整应优先修改 `qingfeng_ui.rpy`，避免在旧 screens 文件中同时维护第二套有效界面。

## 验证方式

在仓库根目录执行：

```powershell
& 'G:/Morinote/renpy-8.5.3-sdk/lib/py3-windows-x86_64/python.exe' 'G:/Morinote/renpy-8.5.3-sdk/renpy.py' . lint
python tools/test_qingfeng_ui.py --sdk G:/Morinote/renpy-8.5.3-sdk
```

测试器把脚本复制到 `.ui-test/project`，只对不写入的运行素材建立硬链接。命令行 savedir 与 game/saves 均指向测试目录；玩家存档与个人设置不作为测试数据。每轮只清理此前生成的隔离测试存档。不要在同一目录并行运行两个测试器。

`ui_qa` 包含主菜单、设置、阅读/选项、存读档、信息页、小说六组实际引擎测试；保存/覆盖/加载恢复/删除均执行真实动作。截图位于 `.ui-test/project/screenshots/`，日志可重定向保存。测试标签仅由测试器进入，正式流程没有测试按钮或自动覆盖层。

验证范围为 Windows 桌面、Ren'Py 8.5.3、1920×1080 逻辑画布，窗口等比缩放。未进行移动端重排和完整剧情通关。现有 lint 中缺失手机头像、重复旧定义及用户本地导入剧情的未声明图像告警不属于本次改动。

2026-10-23 实测：六组测试全部通过、45 项断言通过、21 张引擎截图；lint 退出码 0，无新增 UI 告警。116 个来源文件 SHA-256 均匹配，两个运行圆体覆盖被检 UI 源码中的全部 496 个汉字。修正了引擎样式覆盖造成的旧对话底板残留、存档截图越界和窄分页按钮形变。
