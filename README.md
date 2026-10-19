# Morinote

《原来在动漫社真的能邂逅美少女！》Ren'Py 游戏工程，游戏内社团为「青枫动漫社」。当前工程版本：`test_demo`，基准分辨率：1920 × 1080。

## 获取工程

安装 [Git](https://git-scm.com/)、[Git LFS](https://git-lfs.com/) 和 [Ren'Py SDK](https://www.renpy.org/release_list.html)。本次上传时本地配套 SDK 为 **Ren'Py 8.5.3**；SDK 自身不放入仓库。

```sh
git lfs install
git clone https://github.com/Kelina-Hertz/Morinote.git
cd Morinote
git lfs pull
```

请使用 Git 克隆获取素材。图片、PSD、音频和字体由 Git LFS 管理；尚未下载 LFS 文件时，文件内容只是一小段指针文本。

在 Ren'Py 启动器的设置中，将“项目目录”指向本工程文件夹的上一级，选择 `Morinote` 并启动项目。

## 目录

- `game/*.rpy`：剧情、系统、菜单和界面脚本。
- `game/gui/`、`game/images/`：界面、角色及场景素材；现有 PSD 源文件一并保留。
- `game/audio/`：音乐及音效。
- `game/test_script/`：现有自定义界面脚本。
- `game/tl/`：翻译及公共文本。
- `project.json`：现有 Ren'Py 项目配置。

## 日常协作

开始修改前先更新本地分支；多人并行修改时，建议各建分支，通过 Pull Request 合并。示例：

```sh
git switch main
git pull --ff-only
git switch -c feature/menu-update
# 在编辑器中修改并在 Ren'Py 中检查后：
git add .
git commit -m "Update menu UI"
git push -u origin feature/menu-update
```

已有本地修改时先提交或暂存，再切换分支或更新。`.gitattributes` 会自动将相应素材放入 Git LFS；新增素材时保持此文件生效。PSD 等二进制素材无法逐行合并，修改同一文件前请先在团队内协调。

`.gitignore` 已排除存档、运行日志、可重新生成的脚本编译文件、缓存、编辑器本地设置和备份。这些文件仍保留在原电脑上，无需提交。

## 首次导入说明（2026-10-19）

来源为本地 `G:/Morinote/Morinote`。本次导入保留现有游戏脚本、素材及带 ` (1)` 的副本，未修改剧情、界面实现或素材内容。

- 部分带 ` (1)` 的脚本与无后缀文件内容不同；Ren'Py 会扫描 `.rpy`，同名 label、screen 或定义可能发生冲突。后续整理前请先比较文件并确认保留版本，不要直接批量删除。
- `game/phone_main.rpyc` 和 `game/phone_main (1).rpyc` 没有对应源文件，因此作为例外保留。若找到原始 `.rpy`，建议补回源码后再整理。
- 首次上传只验证版本控制、文件完整性和远程同步；不代表现有游戏已经通过运行或发行测试。
