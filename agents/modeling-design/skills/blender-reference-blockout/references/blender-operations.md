# Blender 执行与操作索引

## 连接与边界

1. 只读查询插件/连接状态、Blender 版本、当前文件、集合、活动场景与渲染设备；只使用实际可用的工具名和签名。可用 MCP 时通常先 `get_addon_status`，再查询场景；工具名变化则按当前接口。
2. 在宿主读取提示词/合同/代码后，以桥接支持的审查过的代码文本操作 `bpy`。安全模式与遥测设置遵守宿主要求；不开安全旁路，不在 Blender 里使用 os、子进程、网络、动态 exec、handlers/timers 或驱动器绕过限制。
3. 明确工作文件与归属集合；先检查同 ID 已有产物，是恢复、更新还是新版本。清理只针对本轮归属且明确可替换的派生物，不清空场景、不删共享母件或他人数据。
4. 生成组件 → 查询求值结果 → 实际视图检查 → 使用获准的保存/渲染 API 落盘。若桥接禁止文件保存/资产附加，报告缺口或请用户通过 UI 操作；不换 shell 绕过桥接。
5. 记录真实路径、版本与保存结果；有权且适用时重开工作副本检查依赖。没有重开就注明未重开，不把“保存成功”当成所有缓存/贴图已打包。

一个实时场景只允许一个写入者。执行失败后先保存可恢复状态或只读取证，再报告；不自动安装依赖、清模块、重启应用或反复重试。

## 操作对应（官方 4.5 文档为索引基线）

| 操作目的 | 人工入口 | Agent 注意点 |
| --- | --- | --- |
| 单位 | 属性 → 场景 → 单位 | 设置显示约定并记录作者尺度，非物理自动换算 |
| 变换/维度 | 3D 视图 N → 项目/变换 | 父级与局部轴维度不等于世界占地 |
| 测量 | 左侧工具栏 → 测量 | Ctrl 吸附；平行面可用 Shift 辅助，标尺不自动进入渲染 |
| 应用缩放 | 物体模式 → 物体 → 应用 → 缩放 | 先检查绑定/动画/实例；不要无差别全应用 |
| 相机 | 相机数据 → 镜头/背景图 | 透视与正交分开，保护匹配相机 |
| 曲线造型 | 曲线控制点、截面/倒角 | 曲率/截面/连接先于增加采样 |
| 倒角/实体化 | 修改器属性 | 检查顺序、法线、非均匀缩放、自交与局部厚度 |
| 缩裹 | 修改器 → 缩裹 | 指定目标/方向/偏移，只是贴合，不证明物理接触成立 |
| 实例 | 共享网格、阵列、几何节点 | 保留源依赖；实现实例可能显著增加内存 |
| 白模预览 | Workbench 或可用 Eevee/Cycles | 确认真实引擎枚举；中性光与无纹理，检查视角不靠景深 |

变换与修改器接口用当前 RNA/节点类型检查，非本地化显示名猜测。CPU/GPU/渲染引擎及导出参数以本机为准。

## 辅助脚本

- `../scripts/check_contract.py`：在宿主终端验证合同，可按需检查输入文件存在与哈希；不安装 bpy，不生成白模。
- `../scripts/blender_audit.py`：宿主读代码，经允许的 Blender 通道发送；调用 `audit_blockout(collection_name, required_names)`。它仅返回求值对象边界、规模与缺口，**不**进行完整实例/曲面碰撞验证，不修改对象，不读写磁盘。

辅助脚本拒绝/缺少能力不代表可以绕过安全控制。实际造型仍由 Agent 根据参考编写任务专用 bpy 操作，不复用一个固定办公室/角色生成器。

## 官方查阅入口

- [场景单位](https://docs.blender.org/manual/zh-hans/4.5/scene_layout/scene/properties.html)
- [变换与维度](https://docs.blender.org/manual/zh-hans/4.5/scene_layout/object/properties/transforms.html)、[应用](https://docs.blender.org/manual/zh-hans/4.5/scene_layout/object/editing/apply.html)、[测量](https://docs.blender.org/manual/zh-hans/4.5/editors/3dview/toolbar/measure.html)
- [摄像机](https://docs.blender.org/manual/zh-hans/4.5/render/cameras.html)、[曲线](https://docs.blender.org/manual/zh-hans/4.5/modeling/curves/introduction.html)
- [倒角](https://docs.blender.org/manual/zh-hans/4.5/modeling/modifiers/generate/bevel.html)、[实体化](https://docs.blender.org/manual/zh-hans/4.5/modeling/modifiers/generate/solidify.html)、[缩裹](https://docs.blender.org/manual/zh-hans/4.5/modeling/modifiers/deform/shrinkwrap.html)
- [实例](https://docs.blender.org/manual/zh-hans/4.5/modeling/geometry_nodes/instances/instance_on_points.html)
- [当前 API 总入口](https://docs.blender.org/api/current/)

版本敏感功能先检查活动版本；这些历史文档链接不是未来安装版本的保证。官方手册操作摘要署名 Blender Documentation Team，依据 Blender 4.5 Manual 整理，按 CC BY-SA 4.0 提供；官方图标、商标、脚本等例外见其 copyright 页面。此许可不涉及私有案例。
