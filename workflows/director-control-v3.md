# 总控按需调用与小上下文 V3

V3 取代新任务的固定流水线。总控的语义理解、提问、导演判断与交付仍由当前宿主中的 Agent 完成；本地程序只帮助列出路由、装配可追溯的小任务包、记录三个人审点，不自动运行子 Agent 或工具。

## 一次任务怎么开始

1. 读角色注册表摘要，恢复当前项目 `.director/project.json` 和索引摘要。
2. 复述需求：目标、已有素材、要新增的变化、哪些不能变。区分主体运动与摄影机运动。根据已有信息选择调用/复用/跳过，并说清理由。
3. 关键缺口主动问，通常一次 1–3 问。已有音频是否原样使用、人物是否需要动作、终点是否必须锁定是会改变方案的问题；无关细节不变成长问卷。
4. 有图就展示原图，无图才设计/制作图。用户确认静态素材后完成动作、提示词及工具方案的必要工作，汇总简明合同交人审。
5. 按明确范围执行。失败即报告并等待人决定。后期按需处理，最后返回实际视频/图片/音频供人审。

已有音频复用时总控记录文件、实际时长、挂载区间和裁切许可即可，不要求声音 Agent 编造对白或 mix_plan。跳过的角色不生成空壳“已完成”产物，也不要求它的 V2 上游全齐。

场景不是只在缺图时调用。已有图需要环境叙事、空间布局、一致性核对或参考研究时，总控可指定 needs_scene_design=true，或 scene_task=narrative_design/spatial_layout/continuity_check/reference_study。场景包按需含 story_background、narrative_purpose、emotion、world_rules、shot_contract、continuity_state、visible_clues、scene_questions；仅传当前镜头相关内容，不附声音制作历史。场景五项方法由该角色按需读取，不自动拆成五个Agent。

此处 narrative_design 仅指既定叙事的场景视觉转译，不是编写故事。故事内容、人物动机、事件因果与情绪目标由上游提供，经总控交接。缺少承重信息时场景角色返回具体问题，总控另行安排故事责任；不强制新增一个角色或新的审核阶段。

## 调用依据

### 三维建模分支

独立任务设置顶层 `request_type=modeling`，brief 中给 request；可用 `modeling_brief` 传本轮 prompt、reference_images（路径/职责/版本）、known_dimensions、scale_policy、object_category、preserve、assumptions、output_root、mode、modeling_contract_ref、review_views。单元级覆盖优先，缺失项由角色按任务判断，不要求用户填满。只装配 `modeling-design` 小包，不查视频方案、声音或视觉风格默认值，不伪造项目和已生成几何。

视频任务在 brief/shot 上显式 `needs_modeling=true` 才建议调用建模角色；位置在场景之后、动作/提示词之前。`modeling_brief` 只传本单元需要的事实与引用，媒体原件按需打开。建模结果可作为动作/提示词的必要上游，不把其他镜头/配音日志传进去。

`completed_calls` 仍按当前 input_fingerprint 复用；建模包对明确提供的本地图片/合同路径重算内容指纹，路径未变而内容已变时不沿用旧完成记录。宿主内联附件无文件路径时，由总控提供 input_versions。完成包未返回真实输出引用时不当作已建模；辅助程序不判定审美，也不自动批准输出。独立结果返回供审阅，沿当前任务授权处理，不新增所有任务固定关卡。

视频制作先走 `../方案库/SKILL.md`；小事实卡存 `brief.solution_facts` 或每镜同名覆盖。程序每次规划自动返回 `solution_decisions`，只把当前决策摘要给节点与提示词角色。状态为 NEEDS_FACTS / DIRECTOR_CHOICE 时总控补事实或明确新方案；不得按 SELECTED 处理。独立静态设计不因此增加人审；生成前合同必须包含方案与当前服务/节点证据。V2 恢复按相同规则补决策，不重新生成已接受素材。

注册表 roles 中的 entrypoint / skill 是真实路径；call_when / skip_when / context_topics / deliverable 是可按需读取的能力摘要。

总控依据上下文做最终决定。程序 select_roles 只根据已解释的 brief 给默认建议，可用每镜 role_decisions 覆盖，并附 reason；覆盖不能提前调用尚无视频的后期角色，不能替代执行授权。不以关键词命中冒充完成导演理解。

节点方案必须说明：本次目标，已有图片/视频真正提供什么信息，命中了哪条经验，为什么采用/排除候选，当前能力哪些待核对。仅平移图片不产生独立动作；视频素材需确认真实运动可用；首尾帧适用于明确且兼容的起止约束；多参考各司其职；Edit只承担保留已有运动的局部修改；Extend用于确需续写的已接受视频。以上是选择依据，不是机械必选规则。

## 每个子任务单独装配上下文

独立调色风格使用grading_style_id，按“镜头 > brief > 项目 > neutral-match”选择，与场景style_id独立。request_type=list_grading_styles只读列目录，不调用后期。实际color-grading包只带所选Skill入口、版本/指纹及grading_brief：媒体探测引用、输入解释、既有变换、输出/监看目标、匹配基准、保护色与Look意图；不传所有风格、TTS历史或所有视频。风格变化不改静态认可；当前合同/最终认可及调色完成指纹按受影响内容更新。

动作设计可用 `needs_action_design=true` 显式请求，即使主体应动还是静止尚待设计也不自动跳过。当前镜头 action_brief 按需含 static_image_ref/version、subject_audit_ref、narrative_purpose、story_background、emotion、world_rules、duration_seconds、shot_contract、continuity_state、sync_cues。大主体表只给权威引用与必要摘要，角色须查看原图和命中表；不复制TTS制作史或全片产物。输出以动作Skill V3.1为准，保留beats/previs兼容字段。

独立风格库为 agents/scene-design/styles/catalog.json。brief、shot 或项目配置中的 style_id 可用注册ID或中文名称，按“镜头 > 任务 > 项目 > 默认”解析，默认 photoreal-cinema。art_direction 和 cinematography 分别记录美术和摄影意图。小包的 visual_style 只给当前风格的ID、名称、版本、入口及明确覆盖项，不复制所有Skill正文。request_type=list_styles 可只读列出目录。未知风格返回澄清，不静默回退。

明确要改变已有图的风格时设置 style_change=true，由场景角色接任务；仅选择新任务风格不自动变更原资产。风格要求变更会使关联静态认可/下游认可过期，但不会自动重新出图或覆盖文件。原风格和新选择冲突时，总控解释需修改的表现范围，再按现有人审执行。既有素材不会仅因默认配置变化就被宣称已完成转换。

核心字段：call_id、shot_id、目标、该镜头摘要、必要约束、角色入口、Skill路径、任务、预期产物。补充字段按角色白名单选择相关事实、素材和经验，每项带来源与状态。

- 全局只共享跨角色必须遵守的少量约束，不共享完整剧本或聊天。
- 镜头背景按 shot_id 过滤；相邻镜头连续性需要时由总控提供简短前后状态，不附整片产物。
- 素材只带本镜选定 asset_ids 的用途、路径和状态，文件按需打开，不内嵌大段数据。
- 特效不带配音/TTS/混音历史，仅在效果和声音同步确有关系时，由总控提供效果时间点摘要。
- 调色不带提示词试错历史，仅带当前视频、目标色调和受保护的肤色/产品色等必要依据。
- 默认包体软预算 6000 字符，可由总控调节至 1500–12000 字符。不是精确 token 配额，角色 Skill/媒体还需另外计入使用量。核心目标与约束过长时由总控摘要或拆镜，不暗删；可选资料超限返回少量 omitted_refs，由角色说明原因再按需扩展。
- 记录 input_fingerprint。已完成记录与当前包一致则复用，避免恢复会话后再做一遍。输入实际变更时由总控更新对应事实/素材的版本及摘要，未更新文件内容不能靠记录指纹自动发现。

使用独立宿主子任务时只发送装配包，不全历史继承；若宿主只支持当前上下文按角色执行，应明确这是“按需读取”，不能声称实现了模型级隔离或精确节省多少 token。

被选中的角色仍按必要依赖交接：镜头与声音可并行，场景按已确定构图制作，动作结果再交提示词，提示词再交节点。跳过的角色不成为障碍。completed_calls 用 output_summary 和 outputs 保存该镜头的简短产物/引用，程序只将必要上游交给相应下游，不转发整段工作日志。

## 三个固定人审点

static_images、contract、final。返回实际文件/预览、简短说明、版本/指纹及请人判断的问题。静态预览要能看身份、构图和场景；合同要能核对时间、主体/镜头动作、声音复用、输入模式、角色选择及成本；最终要能观看成片并看到已知缺陷。

用户回复由总控记录：decision=approved/revise、reviewer、与本轮对应的 fingerprint。程序只检查记录是否对应当前材料，不认证人类身份，也不会生成 approved。没有用户原话不得代填认可。

图像不存在则不能用路径占位通过。无需静态图的任务可提供代表帧，或在 not_applicable_reason 中说明并请用户认可跳过。合同和最终结果仍须返回实际文件，不能因为不想执行而标为不适用。

静态认可通常只绑定静态材料与视觉约束；声音调整不强制重做未变化的静态图。合同绑定当前需求、镜头与静态材料，最终认可绑定合同和结果版本。修改范围不明时向人说明，不递归重跑所有角色。

正常流程不增加逐角色硬审核。issues 中任何未解决问题都停止自动派发，返回人审；状态 unknown 的远端任务先查询已有任务，不重发。解决问题后由总控记录用户决定和新任务范围，再继续。收费、外部上传、覆盖原片另按明确授权；可在合同审核时一并询问，但不隐含授权。

## 项目经验、记忆、素材

每个实际项目使用 `.director/project.json` 指向三份小索引，不把媒体复制到 Agent 安装目录：

- facts.json：当前目标、已确认选择、待办/问题、最新产物及用户决定。用于会话恢复。
- memories.json：经验摘要、适用/不适用条件、角色/主题标签、来源、候选或已验证状态、核对时间。新教训只影响有证据支持的情形，不自动变成全局门禁。
- assets.json：素材 ID、真实路径、主要职责、所属镜头/案例、状态。未核对内容的文件只标候选，不声称已验收。

总控在用户确认、得到实际结果或遇到失败后局部更新对应索引。稳定事实与猜测分开，保留被取代决定的依据；发生冲突以当前用户决定及本地事实为准。复用经验前看适用性，真实执行前重新核对节点能力和计费。项目外的个人记忆不自动改写。

## 人审合同与三层编排

项目按单元（unit，一幕/一集）→组（group，时长由导演判断，硬上限 15 秒，一次视频生成的单位）→镜（shot，一张独立静态帧，时长由导演判断，通常 1–3 秒）三层推进。字段定义见 workflows/contract-v1.md，本文不重复。

制作分三个阶段，全部写进同一份合同：
- 第一阶段：只定分组与镜头描述（units/groups/shots 的 summary 与 duration_seconds）。此阶段不生成任何图。
- 第二阶段：逐镜产出静态帧，写进 shots[].static_frames，出静态图供人审。
- 第三阶段：按组生成视频，写进组的 video_node/video_mode/group_prompt 与镜的 video_prompt/final_prompt。
禁止在第一阶段出图；禁止在静态图未通过人审前提交付费视频生成。

组长度由导演按叙事节拍决定，不追求凑满 15 秒；超过 15 秒必须拆组；人在合同上辅助修改。

合同台账 contracts[] 每层保存一个不可变版本，追加不覆盖。context_eligible 只在 decision=approved 时才为 true。

上下文门槛（硬规则）：当前版本为 pending / rejected / 指纹不符时，该镜与其组的产物绝不进入任何下游角色的上下文包，也不派发下游任务。被拒版本只留在版本历史里作为证据。此规则由 director_control.py 的 contract_eligible 强制，不靠标记。

思考记录 thinking[]：每次做出会影响画面、时间、人物动作、声音或交付的判断时写一条，含 question / understood / assumptions（evidence 只能是 user_confirmed|measured|inferred）/ options（被放弃的也要写 why）/ decision / open_questions / revisit_when。这是给用户看导演思路的，不是内部草稿。

一致性检查：每次规划自动跑 consistency()，结果出现在 plan 的 consistency 键和合同 HTML 的警示条。发现 approval-stale 或 blocked_shots 时停下等人，不自动补齐。

渲染与归档：
python contract_html.py <state.json> --project <project.json> --out <输出.html>
项目根目录主合同 导演制作合同/导演制作合同.html（当前有效版本）；.director/contracts/ 下按版本归档 导演制作合同-vNNN.html；被拒版本文件名带 -rejected，保留不删。三个固定人审点返回给用户时，合同节点返回的是这份 HTML 的实际文件路径。

## 本地状态最小格式

入口 schema_version=director-production/v3。brief 必须有 request，其余由总控按任务填：goal、audio_mode（provided/design/none）、visual_source（provided/create）、subject_motion（none/required/unknown）、camera_motion、render_mode（local_pan/local_edit/generate）、needs_vfx、needs_color、asset_ids 等。

shots 是 [{shot_id,summary,...本镜覆盖项}]，简单单镜可省略。需要共享给角色的内容在 facts/memories/assets 或项目索引中，条目含 id、summary、roles、topics、shot_ids（空表示相关的公共资料）、source/path、status。只有 roles 和 topics 同时命中才装配；素材还须 asset_ids 命中。纯声音制作史不要放到公共 constraints。

artifacts 对应 static_images/contract/video/vfx_video/final，每项有 revision、summary、files。文件可用绝对路径，或 {path,shot_ids:[...]}。多镜视频必须标 shot_ids，避免把无关镜头传给后期。

除原有键外，状态还可含 units、thinking、contracts 三个可选字段，缺省时行为与旧版一致；字段定义见 contract-v1.md。

reviews 存三个审核点的认可；completed_calls 以 call_id 为键保存 status=completed、input_fingerprint 和结果引用；issues 中保存失败/问题与解决决定。导演负责真实更新，辅助程序只读，不能把“计划”写成“实际结果”。

演示见 examples/director-v3-image-audio.json，全部是路由示例，不会触发任何模型。测试在 tests/test_director_control.py。V2 生产文件与 G1–G8 仍可显式兼容，默认新任务不走它们。
