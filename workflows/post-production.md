# 生成后的特效与画面调色 V2.1

前六个专业角色的生成设计结束后，总控执行并审片，再开启后期：

`video_delivery → vfx_design → vfx_delivery → color_grading → post_delivery`

特效设计、画面调色均只在已有实际视频之后调用。前期记录“需要哪些效果、期望什么色调”属于导演简报/场景设计，不提前派发这两个 Agent。默认特效先行、调色随后；无特效也需要明确的 bypass 记录，不能绕过视频验收。

## 总控与角色交接

- 总控负责视频交付验收、工具/节点选择、批准范围与最终审美判断。
- 特效角色负责可见特效的设计和合成要求，生成后按需调用。
- 调色角色基于通过验收的特效版本或未处理原片，负责技术校色与视觉统一。
- 节点角色按需协助核对本机后期工具，不因此再生成视频或改变时轴。
- 声音仍交声音设计角色负责。特效/调色不改原声、语速、时长、帧率、画幅或切点；确需变更先由总控更新合同。

沿用 production-v2.md 的 artifact 外壳：revision、status=accepted、owner、approved_by、inputs 和 input_hashes。approval 字段只记录责任，不等同付费或外部操作授权。

## 阶段正文 data

| 阶段 | 必要字段及意义 |
|---|---|
| video_delivery | generation_completed=true；clips[]；human_review；media_probe。node_design 完成仅允许总控登记这里，不释放特效角色 |
| vfx_design | treatment=apply/bypass；reason；shots[] |
| vfx_delivery | clips[]；human_review；media_probe。特效已实际处理并验收，或按已认可的 bypass 原样交接 |
| color_grading | treatment=apply/bypass；reason；shots[]；color_pipeline |
| post_delivery | clips[]；human_review；media_probe。调色处理/明确跳过后的最终逐镜交付 |

clips 按分镜 shot_id 顺序，每项：shot_id、path（绝对路径）、sha256、duration_seconds、fps、width、height。时长来自实际视频，video_delivery 核对锁定时轴，后期输出参数需保持上游一致。若先合片，另保留逐镜文件或由总控按同一时轴导出检查片段，不伪造 shot_id。

human_review 是 `{passed: true, reviewed_by: "审片责任人"}`。media_probe 是实际媒体检查证据的路径或报告说明，须含探测工具与结果。登记真实任务/生成来源、审片意见可放 evidence。接口成功、文件存在、静态抽帧均不等于审片通过。

两个设计阶段的 shots：`[{shot_id, plan, acceptance, intervals: [{start, end}]}]`。用真实视频秒数定位，0 ≤ start < end ≤ 对应视频时长。apply 至少有一个效果区间；不处理的镜头 intervals=[]。bypass 时全部区间为空，reason 明确说明不处理原因；交付文件哈希及媒体参数与上游相同。

color_pipeline 记录输入色彩解释、工作空间、输出色彩空间/范围及选择依据，不填写凭空推断的相机曲线。媒体元数据未知可明确待确认，不冒充已完成技术色准验收。

2026-10-13独立调色Skill升级：`../agents/color-grading/skills/color-grading/SKILL.md`，风格目录`../agents/color-grading/styles/catalog.json`。grading_style_id仅选择后期Look，不能改变input解释。RCM/ACES管理与手动CST链应明确职责，禁止重复等价输入/输出变换；相机观感参考不等于厂家技术LUT。旧字段兼容不变，新增grading_style及LUT/节点记录可附color_pipeline或plan。

处理镜头使用新文件路径，不覆盖任何已验收视频。无处理镜头可复用原文件。每次处理记录工具、参数、素材/LUT版本和结果路径；付费、上传、额外生成或重试仍逐次确认。

## 门禁、失效与状态

- 设计齐备返回 status=DESIGN_READY，绝不代表视频已经存在。post_status=AWAITING_VIDEO 表示仍等实际生成和验收。
- 后期正在设计、等待渲染或存在过期结果时为 POST_IN_PROGRESS；post_delivery 有效才是 POST_READY_FOR_HANDOFF。若前期变更，则 WAITING_FOR_DESIGN。
- video_delivery 改版使所有后期产物过期；vfx_design / vfx_delivery 改版使调色和最终交付过期。文件原地变化即使未改 revision，也会因实际哈希不匹配被拒绝。
- 同类失败两次停止自动尝试，回到最近责任角色。主体身份、动作或空间错误应退回生成，不通过特效或重度调色掩盖。
- 离线检查器校验依赖、声明字段、文件存在/哈希及登记的媒体参数，不解码视频、不做审美判断、不执行渲染、不认证审片人。媒体探测和人审必须真实完成，execution_authorized 永远为 false。
- example_only=true 仅用于演示，可跳过文件存在/哈希核验，但返回结果持续标注示例，不能当真实交付证据。
