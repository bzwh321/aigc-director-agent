# AIGC Director Agent · AIGC 导演 Agent

把创作需求整理成可执行、可审阅的镜头方案。导演总控按需协调镜头、声音、场景、三维白模、动作、提示词、节点适配、特效和调色九个专业角色，维护素材职责、连续性、制作合同与项目记录。

**其他 AI 从 [AI_ENTRYPOINT.md](AI_ENTRYPOINT.md) 开始读。** 它规定最小读取顺序；完整角色注册表在 [workflow_manifest.json](workflow_manifest.json)。

An AI-readable directing playbook with nine specialist roles, shot-scoped context, a three-level human-review contract and three human review checkpoints. Instructions are primarily in Chinese. Python helpers plan, gate and validate locally; a host AI and user-provided production tools perform the actual work.

| 项目 | 说明 |
| --- | --- |
| 导演核心版本 | 3.1.0 |
| 公开快照 | `v3.1.0-public.2`，2026-11-05 |
| 执行方式 | 由支持读取文件的 AI 客户端承载；辅助代码不自行调用大模型 |
| 生成工具 | 使用者提供自己的节点、工作流及配置；本仓库没有默认供应商 |
| 人审节点 | 静态素材 → 制作合同 → 最终结果 |
| 人审合同 | 单元 / 组 / 镜三层编排，同一份 HTML 合同贯穿三个阶段 |

## 直接交给其他 AI

把下面这段发给能访问网页或本地文件的 AI：

```text
请使用 https://github.com/bzwh321/aigc-director-agent 的导演协议。
先读取 AI_ENTRYPOINT.md，再按其顺序读取 AGENTS.md、SKILL.md 和
workflow_manifest.json 的角色摘要；仅在任务需要时读取相关专业 Skill。
如果网页只能展示目录，请读取对应文件的 Raw 内容；无法读取时直接说明，
不要凭仓库名称假装已经加载。没有工具的客户端可以先做文字方案。

先复述我的目标、已有素材和必须保留的内容，说明需要调用或跳过哪些角色。
只有会改变画面、动作、声音或交付的缺口才追问，每轮最多三个问题。
本轮先做文字方案，不生成媒体、不安装软件、不上传素材或调用付费服务。
不继承示例中的角色资产、通过状态、节点选择或历史授权。
```

当前公开入口：

- [AI_ENTRYPOINT.md 原始文本](https://raw.githubusercontent.com/bzwh321/aigc-director-agent/main/AI_ENTRYPOINT.md)
- [AGENTS.md 原始文本](https://raw.githubusercontent.com/bzwh321/aigc-director-agent/main/AGENTS.md)
- [SKILL.md 原始文本](https://raw.githubusercontent.com/bzwh321/aigc-director-agent/main/SKILL.md)
- [角色注册表原始 JSON](https://raw.githubusercontent.com/bzwh321/aigc-director-agent/main/workflow_manifest.json)
- [llms.txt](llms.txt)：精简文件索引
- [ai-manifest.json](ai-manifest.json)：机器可读的接入信息

正式项目建议固定到版本或提交，避免后续更新改变规则。例如本次快照的
[固定版本 AI 入口](https://raw.githubusercontent.com/bzwh321/aigc-director-agent/v3.1.0-public.2/AI_ENTRYPOINT.md)。
引用时记录仓库、文件路径及版本；要求严格复现时用完整提交 SHA 替换 URL 中的 `main` 或版本标签。

## 在本地使用

```sh
git clone https://github.com/bzwh321/aigc-director-agent.git
cd aigc-director-agent
```

在 AI 客户端中选择这个文件夹，再发送上面的首次对话。无需运行 Python 即可阅读和使用文字协议。
客户端若不能启动独立子 Agent，可以按同样职责分步工作，但应说明实际执行方式。
仓库文件不会自动注册 MCP、连接制作软件或赋予工具权限。

## 角色与职责

| 角色 | 负责什么 | 入口 |
| --- | --- | --- |
| 导演总控 | 理解目标、按需调度、装配当前镜头上下文、审核交付 | [AGENTS.md](AGENTS.md) |
| 镜头 `shot-design` | 景别、机位、运镜、转场及跨镜叙事 | [角色](agents/shot-design/AGENTS.md) |
| 声音 `sound-design` | 配音表演、语义重音、中英表演翻译、音效及混音 | [角色](agents/sound-design/AGENTS.md) |
| 场景 `scene-design` | 将已确定的故事转成空间、构图、美术与连续性 | [角色](agents/scene-design/AGENTS.md) |
| 建模 `modeling-design` | 从文字与参考图建立可编辑三维白模，核对轮廓、尺度与接触 | [角色](agents/modeling-design/AGENTS.md) |
| 动作 `action-design` | 主体路径、关节、受力、时序及摄影机协同 | [角色](agents/action-design/AGENTS.md) |
| 提示词 `prompt-design` | 把已确认设计编译成当前执行端可用的指令 | [角色](agents/prompt-design/AGENTS.md) |
| 节点适配 `node-design` | 核对使用者提供的节点能力、端口和输入输出 | [角色](agents/node-design/AGENTS.md) |
| 特效 `vfx-design` | 根据已有视频设计必要效果与合成 | [角色](agents/vfx-design/AGENTS.md) |
| 调色 `color-grading` | 技术校色、跨镜匹配、风格及保护色 | [角色](agents/color-grading/AGENTS.md) |

默认按实际需要选择角色。例如已有图和音频的简单平移，可由总控处理。
[夫妻萌宠短片](skills/couple-pet-daily-video/SKILL.md) 有专属的四角色协作要求，
不把这个系列的例外扩展到其他任务。
[日常场景短片](skills/cinematic-scene-daily/SKILL.md) 是另一可选入口，不会自动建立定时任务。

## 一次制作怎样推进

1. 明确观众应看到、听到什么，以及现有素材的实际内容。
2. 按**单元 → 组 → 镜**三层把片子拆开：单元是一幕，组是一次视频生成的单位（时长由导演按叙事节奏判断，硬上限 15 秒），镜是一张独立静态帧。这一步只谈分组和镜头内容，不出图。
3. 选择必要角色，按当前镜头装配事实、约束、相关素材与经验；不一次加载全部历史。
4. 提交静态素材供人判断，整合动作、声音、输入职责及实现方案形成制作合同。
5. 核对使用者的工具与本轮授权后执行；最终返回实际结果、已知问题及版本供验收。

三个阶段共用**同一份合同**（`导演制作合同/导演制作合同.html`），逐阶段补写而不是另起文件；
合同里每个镜头一行，含描述、时长、静态帧、视频节点、分镜提示词与最终完整提示词，
另有全局资产、思考记录、审核记录与版本历史。
合同的层级、台账字段与「被拒绝版本不进上下文」的门槛见
[workflows/contract-v1.md](workflows/contract-v1.md)。

三个创作审核点分别绑定对应版本。生成、素材外传、付费和重试需要明确的授权范围；
没有当前授权时先交付可审阅的文字方案。执行失败或任务状态未知时停止受影响分支，
默认自动重试为零。方案类别选择、提示词通过和离线测试均不等于真实媒体已通过验收。

## 文件导航

| 文件或目录 | 用途 |
| --- | --- |
| [AI_ENTRYPOINT.md](AI_ENTRYPOINT.md) | 面向其他 AI 的最小读取流程与接入约定 |
| [SKILL.md](SKILL.md) / [agent.json](agent.json) | Skill 元信息、触发条件和能力入口 |
| [workflows/director-control-v3.md](workflows/director-control-v3.md) | V3 总控操作、上下文包与项目状态约定 |
| [workflows/contract-v1.md](workflows/contract-v1.md) | 人审合同协议：三层结构、合同台账、上下文门槛、思考记录 |
| [contract_html.py](contract_html.py) | 把状态文件渲染成一份 HTML 合同（含逐镜单页） |
| [方案库/SKILL.md](方案库/SKILL.md) | 按素材和运动目标区分制作方法，不配置供应商 |
| [templates/](templates/) | 需求、镜头合同、预算及质量审查模板 |
| [references/](references/) | 按问题读取的方法和经验；保留适用条件与来源 |
| [examples/](examples/) | 路由及状态示例，不是已授权项目 |
| [workflow.py](workflow.py) / [director_control.py](director_control.py) | 本地规划、上下文装配、状态和审核记录检查 |
| [tests/](tests/) | 已有离线行为测试 |
| [validation-report.json](validation-report.json) | 本次公开快照的真实校验范围与结果 |

`stages`、`post_stages` 和旧 G1–G8 材料用于 V2 兼容，不是新 V3 任务的固定必经流水线。
角色路径和能力摘要以注册表为准，当前项目事实及使用者要求优先于历史经验。

## 离线校验

辅助代码需要 Python 3.11+；下面三项仅用 Python 标准库，不需要 API Key。

```sh
python -B scripts/validate_agent.py
python -B -m unittest discover -s tests -p "test_*.py"
python -B skills/cinematic-scene-daily/scripts/test_daily_scene.py
```

最后一项中实际媒体合成测试依赖 FFmpeg；环境未提供时会跳过对应测试。
测试结果详见 [validation-report.json](validation-report.json)。本次没有运行生成服务，
没有验证接收方节点、实际配音、视频生成或创作验收。

## 私人配置、素材与引用

实际项目及其 `.director/` 状态应放在使用者自己的项目目录。
不要把密钥、Cookie、私人节点配置、客户资料、生成媒体或运行日志提交到这个仓库。
`${PROJECT_ROOT}` 等表示接收方路径占位，不代表仓库中已经存在对应素材。
公开版只登记通用能力槽（`provider-video-a/b/c`、`local-compositing`），不含供应商、主机、
账号或密钥；凭据登记为空。能力槽由使用者在本机绑定后才可用。

## 配套可视化面板

合同是 HTML，但不必去文件夹里一个个双击。配套插件
[aigc-design-plugin](https://github.com/bzwh321/aigc-design-plugin) 在 DSH Web GUI 左侧栏提供
「AIGC 设计」入口：选中项目 → 直接打开这个项目的 `导演制作合同/` → 主合同与子合同在顶部标签间切换，
图片按项目内相对路径正确加载。插件只做浏览与渲染，渲染仍调用本仓库的 `contract_html.py`，
一张合同只有一个生成器。

公开版供其他 AI 读取和引用。引用请标注本仓库及具体版本，保留方法文件中的来源、
适用范围与未验证说明。第三方文章、项目、商标、模型及素材仍遵循其各自权利和许可；
仓库不附带这些第三方资产，也不新增第三方内容的使用许可。
