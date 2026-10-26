# 总流程图、原生系统与组件

## 剧情图

项目只有一张总剧情图，章节是其中的分组。跳转、调用、返回、条件与选项来自源码控制流，不按文件排列或 label 命名推测。场景中的手机会话是剧情调用，手机系统的函数实现不是一串剧情场景。番外与测试入口保留自己的用途，不擅自插入主线。

`morinote_workspace` 的 `flow` 包含完整节点、连线和剧情展示层 `story/storyDetail`。选择修改时用原始节点 ID 与 source；展示层的标题和折叠布局不作为运行目标。静态 `jump` 是转向，`call` 执行后按返回点继续。动态目标显示运行时确定，不补出猜测连线。

新建独立场景：
```json
{"adapter":"flow","operation":{"operation":"scene","path":"game/creator_scenes.rpy","name":"new_scene","title":"会后走廊","group":"第二章"}}
```
这会创建带默认文字和 return 的场景模板，不等于已接入主线。刷新并将模板正文替换为用户要求的内容；未授权时保留独立测试入口。

改一个已有静态 jump/call：`{"adapter":"flow","operation":{"operation":"target","node":"FLOW_NODE_ID","target":"EXISTING_LABEL"}}`。

在明确位置新增选项或条件：
```json
{"adapter":"flow","operation":{"operation":"choice","node":"FLOW_NODE_ID","options":[{"text":"去图书馆","target":"route_library"},{"text":"去教室","target":"route_classroom"}]}}
```
```json
{"adapter":"flow","operation":{"operation":"condition","node":"FLOW_NODE_ID","condition":"visited_library","yes":"route_known","no":"route_new"}}
```
目标标签必须存在且无歧义。condition 使用到达时可求值的已有状态。上述操作插入代码，不会自动消除原出口；先检查插入点的 jump/return 和分支汇合，避免新代码不可达。复杂块编辑先查看 `flow.authoring` 的能力与参数，不能猜 `connect_exit` 等操作字段；也可局部修改源码。

状态使用 Ren’Py 的 `default`／persistent 及现有项目约定；运行事件依旧由原代码明确触发，不把 screen 每次渲染当成一次剧情事件。测试状态只用于副本的预览入口，不写成游戏默认值。

## 原生配置

从 `morinote_workspace.config` 取得真实 binding ID、来源、editable 状态和字段类型。基础写法：
```json
{"adapter":"config","operation":{"operation":"set","binding":"BINDING_ID","value":"NEW_VALUE"}}
```
只给字符串字段传字符串；布尔／数值／列表等保留真实类型。转场字段使用返回的 references 中的名称。复杂表达式拒绝表单编辑时保留表达式，用 `read/write` 局部改源码。不要把原生系统迁移成第二套结构化短篇运行时。

## Morinote 的脚本职责

下面是当前项目的常见来源，实际以 files 和配置来源为准：

- `script_c1a.rpy`、`script_c1b.rpy`、`script_c1c.rpy`：第一章剧情与其原生调用；其中启动入口按实际源码确定。
- `settings.rpy`：角色、图片差分标签、变换等定义，引用完整标签，保留其内置变换。
- `message.rpy`、`message_system.rpy`：手机相关声明、会话／界面与运行逻辑；先看角色 kind 和调用关系再改。
- `contact_system.rpy`：通讯录、联系人、好友申请、未读等系统。
- `ova.rpy`、`ova_script.rpy`：番外目录与正文；不是主线默认节点。
- `achievements.rpy`：成就及解锁条件，保留 Steam ID 对应关系。
- `options.rpy`、`gui.rpy`、`screens.rpy`、`qingfeng_ui.rpy`、`00_ui_sounds.rpy`：基础配置、界面与音效。并非每个工程都有所有文件。

## 手机和自定义组件

手机是在剧情中调用的原生 NVL／Screen 系统。会话中的消息顺序、标题、发送者、头像、预填、选项和退出清理共同决定效果。聊天叠加在背景与人物之上，进入退出不自动修改画面或音乐。

新增会话先读取现有一个同类会话、角色 alias 和被调用标签，按原模式新增并在指定位置调用。保留 NVL 回调、`interact=False` 预填、nvl clear／hide、退出清理和调用返回上下文；预填消息不能变成额外点击。不能根据旁白文本自动认定它是手机消息。

通讯录需保留同意／拒绝结果、初始列表与未读规则。OVA 已读、成就和其他 persistent 状态只在隔离试玩中测试，不更改用户正式存档；复杂成就条件保留源码，未实际联网不能报告 Steam 同步成功。

新手机变体、调查界面等可在副本的独立 RPY／Python 中实现。定义参数、调用入口、返回值、退出清理以及存读档／回滚行为；screen 渲染本身不要执行一次性剧情副作用。未提供可视化接口的组件通过源码编辑和原引擎运行，不承诺 IDE 自动生成其全部拖拽控件。当前工具没有专用“自动点击游戏／存读档”接口；可以按用户授权编写 Ren’Py testsuite，再用 test 执行，不能伪称已经手动验证交互。
