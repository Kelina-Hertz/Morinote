# 三轨、Voice 与演出操作配方

下列 JSON 是 `morinote_operate` 的参数。大写占位值必须替换成当前工具返回的真实 ID、标签或来源位置。适配器填写期望摘要；直接 `morinote_write` 则使用最近一次 `read` 的 hash 和完整新内容。一次修改后重新读取受影响源码／投影再进行下一次定位操作。

## 文字、旁白、手机与 Auto

每句普通文字、每条交互手机消息对应一个推进点。旁白或同说话人的连续对白，在画面及音乐不变时可显示为一个长编辑区；不改变实际推进次数。普通对白不能直接改成手机消息，需要按手机系统的角色和上下文新增。

改一句文字：
```json
{"adapter":"stage","operation":{"operation":"text","nodeId":"LINE_ID","value":"新的台词"}}
```
改为旁白用 `speaker`、`value:""`；改为对白使用 `nativeRenpy.characters` 中已定义的普通角色 alias，不用显示名。`speaker` 不负责把普通文字切换到手机系统。

插入一句：`{"adapter":"stage","operation":{"operation":"insert","nodeId":"NEXT_LINE_ID","command":"a \"新增一句\""}}`。这会在锚点语句前插入；要加在某句后，选下一句锚点，或读取源码后在明确位置编辑。先确认角色 `a` 存在，不随意新增跳转或结尾。新增文字本身不插入额外画面和音乐命令。

Auto：`auto_wait`、`nodeId`、`value:2.5` 设置文字显示完后的秒数；`value:null` 恢复项目／玩家默认规则。不会改变手动推进，也不按秒数拉伸轨道高度。预填的 `interact=False` 语句不是等待节点。

Voice：
```json
{"adapter":"stage","operation":{"operation":"voice","nodeId":"LINE_ID","asset":"VOICE_ASSET_ID"}}
```
省略 `asset` 可移除这一句的 Voice。素材取当前项目的语音条目；不使用 `play music` 模拟逐句语音。删除一句文字可使用 `delete_text`，适配器同时处理该句已识别的 Voice／Auto 辅助语句。

## 变化点和继承

对某推进点从此独立：
```json
{"adapter":"stage","operation":{"operation":"split_track","nodeId":"LINE_ID","track":"visual"}}
```
音乐使用 `track:"audio"`，两轨独立。拆分复制当前有效设置，之后沿用这一段，直到下一处独立设置。先拆分、刷新，再修改新来源；否则修改早先 `show/play` 会影响整个继承段。未知入口／汇合状态不能复制为猜测构图。

恢复沿用：`{"adapter":"stage","operation":{"operation":"restore","nodeId":"LINE_ID","track":"visual"}}`。只移除适配器可识别的受管边界；手写演出无法可靠归属时用源码处理。不存在 `inherit_track` 操作。

## 背景、多人和坐标

换图片使用实际 `scene/show` 行，而不是台词行：
```json
{"adapter":"stage","operation":{"operation":"image","path":"game/SCENE.rpy","line":12,"value":"REGISTERED_IMAGE_TAG"}}
```
只改该条语句的图片标签，保留 `as` 实例名、已有变换和其他属性。Ren’Py 的 `scene` 会清除图层中的人物；需要更换背景并保留人物时，应在变化点按当前实例重新 `show`，不能只改 UI 后宣称人物保留。

添加人物先取得已登记标签及当前构图，再通过 `insert` 插入原生 `show TAG as INSTANCE`，必要时带 ATL 位置。换表情沿用同一个实例，避免重影；离场用 `remove`、`nodeId`、`tag` 显式生成 `hide`。没有 `actor` 适配器操作。

修改已有 show 的位置与缩放：
```json
{"adapter":"stage","operation":{"operation":"properties","path":"game/SCENE.rpy","line":13,"values":{"xpos":960,"ypos":1080,"xanchor":0.5,"yanchor":1.0,"zoom":0.8}}}
```
以上坐标仅示范 1920×1080 项目，实际读取项目分辨率、锚点和图片定义。整数位置是像素，浮点位置是 Ren’Py 比例值，`960` 与 `960.0` 不等价。人物标签可能内置缩放；`nativeOriginal.intrinsicZoom` 与外层 zoom 不可重复相乘。要填写最终有效缩放，使用 `property`、`property:"zoom"`、`effective:true`；`properties` 中的数值是代码属性值。保留原图层、实例和手写 ATL，不能用静态构图替代复杂显示对象。

## 立绘动作

已存在人物实例才能新增动作。支持 `move`、`enter_left`、`enter_right`、`fadein`、`jump`、`shake`；曲线为 `linear/ease/easein/easeout`：
```json
{"adapter":"stage","operation":{"operation":"motion","nodeId":"LINE_ID","tag":"EXISTING_INSTANCE","motion":{"kind":"move","easing":"ease","duration":0.6,"start":[640,900],"end":[960,900],"amplitude":30,"repeat":1,"wait":false}}}
```
起终点为项目像素坐标。`duration` 0.05–30 秒，`repeat` 1–10，`amplitude` 0–2000。`wait:false` 允许台词与动作同时开始；`wait:true` 会等待动作完成，只有演出设计需要时使用。适配器生成受管 ATL 块并保留实例的锚点与缩放。`action:"remove"` 移除本句受管动作。自定义图层或已手改动作块可能拒绝表单编辑，此时读取源码再局部修改，不覆盖原动作。

## BGM、环境音和音效

Voice 以外的音频按声道并行。先读取 `nativeRenpy.audioChannels`，选择项目已支持的声道。`music` 不代表所有音频；不能通过第二次 `play music` 实现两首同时播放。

在当前句更换一个声道：
```json
{"adapter":"stage","operation":{"operation":"audio_layer","nodeId":"LINE_ID","channel":"music","action":"play","asset":"AUDIO_ASSET_ID","volume":0.7,"fadeout":0.5,"fadein":0.8}}
```
同曲从此调音量使用 `audio_layer`、`action:"volume"`、`volume:0.4`，保留播放位置；静音该声道用 `action:"stop"`。不改玩家偏好；数值是此段的演出音量。

若要修改原播放语句覆盖的整个段，可用 `audio`、`path/line` 指向实际 `play` 行、`property:"volume"`、`value:0.4`。`property:"asset"` 的 value 是音频素材 ID；`fadein/fadeout` 也是数值属性。改变原 play 与从某句新增音量变化的影响范围不同。
