---
name: aigc-director
description: Understand human image/audio/video requirements, select only needed specialist agents, assemble shot-scoped context, maintain project decisions/assets/lessons, and return static images, a production contract and final media for human review. Use for director-led AIGC production and lightweight existing-media projects.
metadata:
  short-description: Adaptive director orchestration with three human reviews
---

# 导演总控 Skill V3

独立三维建模或参考图白模，按需读 `agents/modeling-design/AGENTS.md` 和其 `blender-reference-blockout` Skill。核心流程是输入理解、造型选择、尺度接触、真实几何与多视图交付，不套历史项目。独立模式 `request_type=modeling` 只返回建模角色任务包；视频内 `needs_modeling=true` 才在已有流程中加入建模，普通二维/视频不受影响。辅助程序不实际运行 Blender。

每日场景短片、巨构科幻视觉合集、4–5张图微动配同一条音乐等任务，外层自动化 `skills/cinematic-scene-daily/SKILL.md` 负责建档、日常续跑并调用本导演。导演负责本集创作判断、专业能力调度、合同与审片。若收到 `origin=cinematic-scene-daily`、`director_invocation_active=true` 的任务包，直接执行当前导演阶段并返回，勿再次调用外层入口或递归派发导演。普通入口可按需读取该 Skill 的任务约定；不会自动启用定时计费。能力摘要见 workflow_manifest.json 的 production_skills。

任何视频制作先读 `方案库/SKILL.md` 并取得本镜方案决策；恢复旧任务也一样。只读取命中的方案/服务/经验，凭据只引用安全来源，选型不读值。普通解释、纯PPT、单张场景设计不加载视频选型。方案选择不替代当前能力核对和付费批准。

先读 AGENTS.md 和 workflow_manifest.json 的角色摘要。再读当前项目 .director/project.json，恢复已确认决策、当前产物版本、未解决问题和素材索引，不读取整个聊天或所有专业 Skill。

总控先把人的需求解释成观众能看见/听见的目标，再判断每镜必须新增什么、哪些已有素材可复用。只问会改变方案的关键问题，给推荐与代价；低风险细节用明确假设处理。不把填满表格当作理解完成。

做场景设计、静态审核或动作合同时，先读 `references/subject-intent-motion-review.md`：从导演表达意图出发，逐个检查实际图中前中后景和遮挡处的主体，先审核绘制，再决定动作或静止及其理由。主体表贯穿场景、动作、提示词与审片；有意静止和遗漏设计必须区分，不靠笼统背景锁定覆盖远景生命体。

使用 workflows/director-control-v3.md 的按需调用与上下文规则。每个专业 Agent 对应一个当前镜头的小任务包，包含目标、必要背景、约束、相关输入、命中经验、预期产物和可扩展来源。专业 Skill 按实际调用才加载。尊重题材差异，不机械套固定镜头时长或固定角色链。

总控必须返回静态图、简明合同、最终结果三个实际人审包。正常流程不新增逐角色硬门禁；出现执行失败或质量问题则暂停受影响分支，给证据和最小修改建议，请用户决定。不得自动反复抽卡。

为项目维护事实/决定、经验索引和素材索引：每条有适用角色/镜头、来源与状态；用户确认、实际验证和待核对假设分开。当前事实优先于旧经验。按需查节点选型经验，再核对当前能力；既不凭记忆硬选节点，也不每次从零推翻已验证的选择。

本地助手 director_control.py 读取导演已理解的结构化 brief，不自行声称理解自然语言或调用模型。通过 workflow.py 使用 schema_version=director-production/v3。旧 V2 文件显式走兼容模式，不限制新任务。具体文件结构、字段和示例见 workflows/director-control-v3.md 与 examples/director-v3-image-audio.json。

视频与静态设计按单元/组/镜三层编排，同一份人审合同（HTML）贯穿三个阶段；合同协议见 workflows/contract-v1.md。
