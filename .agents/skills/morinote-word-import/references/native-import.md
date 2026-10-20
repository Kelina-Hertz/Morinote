# 原工程接入约定

## 读取当前工程

从目标仓库读取，勿使用作者工作区或旧网页服务作为依赖：

- `game/settings.rpy`：人物、图片标签和变换；并扫描其他 RPY 中的声明。
- `game/message.rpy`、`message_system.rpy`、`contact_system.rpy`：实际文件存在时查看手机调用、NVL 回调、头像和清理。
- `game/options.rpy`、`gui.rpy`：文字与 Auto 默认值、已声明转场。
- `creator/backend/native_stage.py`、`native_audio.py`：可视化演出支持的原语句。
- `creator/backend/native_assets.py`、`native_assets_runtime.rpy`：虚拟素材模型及运行支持。

文件不存在时扫描实际名称，不凭上述文件名新建一套替代系统。对于复杂 ATL、screen 或 Python，保留原代码并提供源码位置。

## 推进与演出

一句对白、旁白或手机消息通常对应一个推进点。背景、人物和音频变化放在该句话前，沿用状态不重复生成语句。手机预填消息保留当前系统的 `interact=False` 语义，不能算成玩家需要点击的新消息。

同一角色换差分使用同一实例 tag，保持位置，避免重复立绘。换背景不能顺带让所有人物离场；离场使用显式 `hide`。多人位置按实际图片尺寸与项目坐标规则设置；图片标签原定义包含缩放时不得重复乘一次。

同曲调音量使用当前通道的音量操作，不重新播放。换曲的默认淡出／淡入为 0.5／0.8 秒，除非相关场景另有设计。音乐音量与玩家设置相乘；不要改写全局玩家偏好。普通文字保留原文字速度与 Auto，除非剧本或用户明确要求逐句覆盖。

片段末尾清理本片段打开的手机界面、临时状态及必要音频，并按调用语义 `return`。不要清理不属于本片段的全局系统，或把 `return` 随意改成 `jump start`。完整章入口只是测试包装时，可在 IDE 元数据中标为 `test`，不把它画成额外剧情场景。

## 虚拟素材

`game/creator_assets/asset_bindings.rpy` 是受管素材表和运行支持。不要在 `settings.rpy` 中批量改标签，也不要移动、重命名、复制覆盖或删除实际媒体文件。

可读取当前索引中的 `project['nativeAssetLibrary']`。需要修改时优先调用已有 `assets` 源码准备操作；在独立 Python 操作中也可使用：

```python
from backend.native_assets import edit
from backend.workspace import commit

# project 为当前仓库 load_project 的新鲜结果。
change = edit(root, project, {"operation": "create", "name": "汐泉／女仆装／害羞", "type": "sprite"})
# commit(..., engine=None) 使用保存中断恢复事务，只写源码和索引，不调用引擎。
result = commit(root, [change], project["revision"], engine=None)
```

为避免重入或跨进程竞争，IDE 打开时优先使用它已有的 `/api/workspace/prepare`、`/api/workspace/save` 接口和当前项目会话，不另起进程同时保存同一项目。接口需由受信任 IDE 客户端调用，不寻找或输出认证凭据。

新建条目后重新读取项目，根据返回条目取得稳定 `id` 和运行标识，不能猜测 UUID。可合并同一批受管文件更改后保存，避免逐句重复重建条目。

- 图片：`runtime.kind == "image"` 的 `runtime.key` 是 `show`／`scene` 使用的标签。未指定素材时，运行支持显示带需求名称的占位。
- 新音频需求：通过素材表创建音频条目，使用其项目内虚拟路径；未绑定时运行支持提供静音。不要自己伪造空 `.ogg`／`.mp3`。
- 临时差分：`operation: "bind"`，`binding: {"kind": "label", "key": "原图片标签"}`，`temporary: true`。保留 `requirement`，不当作需求完成。
- 直接文件：只能选本工程登记的资源，`binding.kind: "file"` 的 key 相对于 `game/`。
- 更换映射到图片标签时，使用其原始完整定义，不把虚拟条目互相串联，不重复应用原定义缩放。

正常素材不显示状态；缺失、目标丢失均写“缺失”，暂用已有素材写“缺失 · 临时替代”。报告也沿用这些称呼，不写“正式绑定”。

生成器仅使用实际取得的运行标识。只在正文中出现、尚未明确呈现的照片等道具，可以先登记为需求；不要为了补齐清单自行加一句台词或擅自展示 CG。

## 来源文件与段落登记

提取结果保存在 `.creator/imports/<chapter>/<version>/`，默认不会提交 Git。若需团队共享原 Word 和导入记录，由用户选择仓库内的共享位置；不要悄悄上传原文档。

源码使用来源注释，例如：

```renpy
label c22_before_meeting:
    # word: p000012; node: c22_before_meeting_001
    narrator "逐字保留这里对应的原文。"
    return
```

说话人 `narrator` 仅为格式示例，必须换成实际已声明的角色；旁白也可使用原工程的无说话人语句。字符串中的反斜杠、引号以及 Ren’Py 的 `{}`、`[]` 需按文字意图转义；制作指令不能意外变成可执行插值。不要用“删去特殊字符”代替转义。

`source-map.json` 最小格式：

```json
{
  "version": 1,
  "source_sha256": "source.json 中的 source.sha256",
  "paragraphs": [
    {"id": "p000012", "original": "原段落全文", "disposition": "text", "node_ids": ["c22_before_meeting_001"]},
    {"id": "p000013", "original": "制作备注原文", "disposition": "note", "node_ids": [], "reason": "制作备注，不进入玩家正文"}
  ],
  "nodes": [
    {"id": "c22_before_meeting_001", "kind": "narration", "paragraph_ids": ["p000012"], "text": "生成的玩家可见文字", "rpy": {"path": "game/creator_imports/chapter_2_2/story.rpy", "label": "c22_before_meeting", "line": 4}}
  ]
}
```

处置值为 `text`、`direction`、`note`、`heading`、`pending`。非正文处置写明理由；`pending` 必须在交付中列出。复合段落可以关联多个节点；反过来节点可以关联多个源段落。若原段落含角色名、括号演出和对白，分别登记，但原段落全文仍需保留。

来源检查不校验 Ren’Py 字符串转义，也不证明文字无删改。Codex 必须对照原文、生成代码和分支逐项检查，避免把制作备注作为对白、遗漏短句或把选项文字当旁白。

## IDE 名称与分组

可准备 `ide-metadata.json`，仅声明需要更新的项：

```json
{
  "sceneTitles": {"c22_before_meeting": "会前 · 汐泉与渡鸥"},
  "flowGroups": {"c22_before_meeting": "第二章 · 2-2"},
  "flowRoles": {"c22_preview": "test"}
}
```

刷新脚本只合并这三个字段，验证 key 是真实已识别 label；没有提供的用户设置保留。`flowRoles` 为 `story`、`conversation`、`system`、`test`。正文场景正常显示，手机系统函数不是主线节点。不会修改入口或确认记录。

输入元数据可以用可读 label 名。脚本会把 `sceneTitles` 的 key 转为 IDE 实际使用的稳定 label ID，`flowGroups` 则保留 label 名，不能把三种字段机械写成同一种 key。

离线刷新使用 `open_native` 重扫，不调用可能回写旧缓存台词的 `reindex_project`。IDE 有未保存修改时先保存或保留恢复稿；刷新后重新打开同一工程，处理外部修改冲突，不丢弃旧缓冲区。不要靠修改缓存中的 `scenes` 来“导入”剧情。
