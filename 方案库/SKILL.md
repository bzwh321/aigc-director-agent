---
name: director-solution-library
description: Select a scoped, evidence-backed AI video production recipe before director-led video work, using existing assets, motion requirements and provider capabilities. Includes service and credential references, not secrets or execution authority. Excludes pure PPT layout and node explanations.
---

# AI 视频方案库

这是导演总控的视频决策入口，不是新增子 Agent，也不是第四个人审点。任何新建、继续、换模式或更换素材的 AI 视频制作，先经过本库；普通节点解释、纯 PPT 排版、单张场景设计不强制走视频选型。

## 最短路径

1. 总控把本镜需求整理为少量事实。已有确认不重新询问；未知写 `unknown`，不把“有素材”当成“有可用真实运动”。字段与调用方式见 [决策输入](决策输入.md)。
2. 运行 `decide.py`，或通过导演 V3 的 `workflow.py` 自动取得每镜 `solution_decisions`。规则唯一命中则复用；缺事实问关键问题，多个方案交总控选，不轮询模型。Jev 尚未接入。
3. 只读命中的 `catalog.json` 条目。服务入口与执行工具在 `services.json`；凭据仅按 `credentials.json` 的引用交给获准的执行器，选型阶段不读密钥值。
4. 合同记录 `recipe_id`、决策指纹、输入版本、排除理由、具体服务/模型/节点或应用、当前能力证据与预算。已有合同或旧 V2 状态恢复时补上本库决策，不强制重生素材。
5. 执行前核对实际节点端口、模式、媒体约束、账户与费用；历史“已跑通”不等于当前可用。失配返回用户，不静默换供应商或社区应用。选型程序始终 `execution_authorized=false`，不上传、不调用 API、不自动重试。

## 维护

涉及清晰度、超分、插帧或导出质量时，按需读 [经济提质](经济提质.md)：先原片保真与定稿裁切，再短片对照，仅必要镜头升级；不默认4K/60fps或新增计费。

涉及调色/镜头匹配/相机观感时，读取 `../agents/color-grading/skills/color-grading/SKILL.md`，按grading_style_id选风格。它是已有视频的确定性后期候选，不因“相机风格”改走重新生成，也不默认买LUT/插件。

- `catalog.json`：可复用制作方案，不混入项目人物、素材、口令或任务状态。
- `services.json`：网站/文档、已知本地执行器与节点、历史应用指纹、需复核项。
- `credentials.json`：API Key 的环境变量名、安全文件位置和用途；绝不保存明文值。文件存在、凭据有效、账户可用三者分开。
- 项目 `.director/`：只保存本项目的方案决定、版本及人审结果，不复制全库。

新增方案先标 `candidate`；实际运行证据和人审记录齐全后，才标对应项目历史验证。无命中时补方案或向用户说明缺口，不伪造“最相近”的可执行节点。素材/要求/规则/当前能力版本改变时重新决策，未变不重新论证。
