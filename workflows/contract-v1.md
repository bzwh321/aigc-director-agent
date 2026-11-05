# 人审合同与三层编排 V1

本文件是 `director-production/v3` 的**增量规格**：`units`、`thinking`、`contracts` 三个字段全部可选，缺省时行为与旧版完全一致。旧状态文件不需要迁移。

## 一、三层结构

```
单元 unit（一幕/一集，如 U01）
└─ 组 group（一次视频生成的单位，如 G01；时长由导演按叙事节奏判断，硬上限 15 秒）
   └─ 镜 shot（一张独立静态帧，如 S01-01；时长由导演判断，通常 1–3 秒，但服从动作与台词的完整性）
```

- **镜**是创作判断的最小单位：一张静态帧、一段描述、一段台词、一组音效。镜的长度也由导演判断：一句台词、一个完整动作没走完就不要硬切；只有当一镜长到一次生成撑不住时才拆。
- **组**是一次视频生成的最小单位：一个视频节点、一段视频提示词、一次付费。组内镜头靠时间轴切分。组的长度不是配额，导演按这一组要讲完的叙事节拍定长度，短到 3 秒、长到 15 秒都可以，超过 15 秒必须拆组；人在合同里辅助修改。
- **单元**是叙事单位：一幕、一集或一个独立段落。

字段：

```json
"units": [
  {
    "unit_id": "U01",
    "title": "潮闸内部",
    "goal": "让观众知道门后有活物",
    "groups": [
      {
        "group_id": "G01",
        "summary": "她推门进入，光先落在墙上",
        "target_seconds": 15,
        "video_node": "Seedance · reference",
        "video_mode": "reference",
        "group_prompt": "组级提示词：本次生成实际提交的那段",
        "shot_ids": ["S01-01", "S01-02", "S01-03"]
      }
    ]
  }
]
```

`target_seconds` 是导演声明的组时长，用于记账与一致性核对，不是系统配额；一致性检查只在两种情况下报警：超过 15 秒硬上限（group-too-long，阻塞），或声明值与组内镜头时长之和相差超过 20%（group-duration-mismatch，只做账目提醒）。

`shots[]` 每条增加三个可选键：`unit_id`、`group_id`、以及下面第二节的字段。缺少 `units` 时，全部镜头视为同一隐式组。

镜头字段（全部可选，缺省显示为「待定」）：

```json
{
  "shot_id": "S01-01",
  "group_id": "G01",
  "summary": "她推开铜门，光先打在墙上",
  "duration_seconds": 2.4,
  "audience_takeaway": "有人在里面",
  "framing": "中景",
  "angle": "平视",
  "camera_motion": "缓慢推",
  "subject_action": "手推门→门开 30°",
  "dialogue": [
    {"speaker": "她", "text": "有人在吗？", "emotion": "试探", "seconds": 3.2, "source": "estimated"}
  ],
  "sound_effects": [
    {"cue": "门轴吱呀", "at_seconds": 3.0}
  ],
  "static_frames": [
    {"path": "...png", "revision": "v002", "sha256": "...", "role": "首帧"}
  ],
  "video_node": "Seedance · reference",
  "video_mode": "reference",
  "video_prompt": "实际提交给节点的那段",
  "final_prompt": "含风格/角色/场景/负面词的全量版",
  "contract_id": "S01-01-v004"
}
```

`static_frames` 是**数组**：一次视频生成可能吃多张静态帧（首帧 + 尾帧、或多张参考）。表格单元格必须能并排显示多张缩略图。

`dialogue[].source` 只允许 `measured`（实测）或 `estimated`（估算草案）。不写实测值就标 `estimated`。

## 二、合同台账

三层合同：`shot` / `group` / `film`。每条合同一个不可变版本，追加不覆盖。

```json
"contracts": [
  {
    "contract_id": "S01-01-v004",
    "scope": "shot",
    "target_id": "S01-01",
    "revision": 4,
    "decision": "approved",
    "reviewer": "user",
    "decided_at": "2026-11-02T23:50:00+08:00",
    "reason": "通过",
    "fingerprint": "…",
    "context_eligible": true,
    "files": [{"path": "...", "sha256": "..."}]
  }
]
```

- `scope`：`shot` | `group` | `film`。
- `target_id`：镜头号 / 组号 / `"film"`。
- `decision`：`pending` | `approved` | `rejected`。
- `context_eligible`：只有 `decision=approved` 才允许为 `true`；程序不代填 `approved`。
- 同一 `target_id` 取 `revision` 最大的一条作为当前版本。

### 上下文门槛（硬规则）

**被拒绝的合同及其产物绝对不进入任何子任务上下文。**

`context_packet()` 装配前必须调用 `contract_state(state, scope, target_id)`：

| 当前版本 | 该镜/组/片可否进入下游上下文 |
|---|---|
| 无合同记录 | 可以（旧状态向后兼容） |
| `pending` | 不可以，且不派发下游角色 |
| `rejected` | **不可以**，且不派发下游角色 |
| `approved` | 可以 |
| `approved` 但指纹与当前内容不符 | 不可以（认可已过期） |

指纹覆盖：镜头内容、静态帧路径 + sha256、提示词。任一变化即视为认可过期。

被拒版本的静态帧、提示词不得出现在任何角色的上下文包里，也不得出现在 HTML 合同的「当前有效」区；只在版本历史里保留为证据，标红并写明「不入上下文」。

## 三、思考记录

```json
"thinking": [
  {
    "thinking_id": "T001",
    "at": "2026-11-02T23:40:00+08:00",
    "scope": "group",
    "target_id": "G01",
    "question": "这组怎么切分？",
    "understood": "用户要 15 秒内交代她进门的犹豫",
    "assumptions": [
      {"claim": "门是铜制的", "evidence": "inferred", "note": "用户未确认"}
    ],
    "options": [
      {"option": "一镜到底 15s", "cost": "1 次生成", "risk": "动作密度不足", "chosen": false, "why": "缺少停顿"},
      {"option": "三镜 4/5/6s", "cost": "1 次生成", "risk": "切点需精确", "chosen": true, "why": "能在 5s 处给一次停顿"}
    ],
    "decision": "三镜 4/5/6s",
    "open_questions": ["铜门的材质是否需要实测"],
    "revisit_when": "用户给出实际场景参考图后"
  }
]
```

`evidence` 只允许 `user_confirmed` | `measured` | `inferred`。三者混用会让后续无法判断哪条能当依据。

## 四、HTML 合同

### 命令

```
python contract_html.py <state.json> --project <project.json> --out <输出.html>
```

- 只读，不联网，不调用模型，不生成图片。
- 输出单文件，CSS 内联，图片用**相对路径**引用（不 base64）。
- 相对路径按 `--out` 所在目录计算；文件不存在时显示占位框而不是报错。

### 页面结构

1. **页头**：标题、单元、合同版本、生成时间、总体状态徽章、锚点导航。
2. **全局资产**（`#assets`）：人物 / 场景 / 道具 / 故事背景 四组卡片。每张卡：缩略图、ID、名称、用途、出现的镜头、sha256 前 8 位。数据来自项目 `.director/assets.json`，按 `kind` 分组；无 `kind` 的归入「其他资产」。
3. **设计表**（`#design`）：一行一镜。
   - 列：组号 | 镜头号 | 时长 | 镜头描述 | 观众应理解 | 景别·视角·运镜 | 主体动作 | 台词/配音 | 音效 | 状态
   - 每个组前插一行组标题行（`colspan` 跨满），显示：组号 · 目标时长 · 镜头数 · 组级合同状态。
4. **生成表**（`#generate`）：一行一镜。
   - 列：组号 | 镜头号 | 静态帧 | 静态审核 | 视频节点 | 模式 | 视频提示词 | 最终完整提示词 | 单镜合同 | 入上下文
   - 「静态帧」单元格并排显示该镜全部缩略图，每张带 `role` 与 `revision` 角标。
   - 组标题行显示：组号 · 视频节点 · 模式 · 组级提示词 · 组级合同状态。
   - 「最终完整提示词」用 `<details>` 折叠。
5. **思考记录**（`#thinking`）：按 scope 分组，每条一张卡：问题、理解、假设（带证据等级色标）、候选方案（被选中的高亮，被放弃的显示 `why`）、决定、待验证、重访条件。
6. **审核记录**（`#reviews`）：三层合同的版本历史表。列：合同ID | 层 | 目标 | 版本 | 结论 | 审核人 | 时间 | 入上下文 | 理由。`rejected` 行整行标红并在「入上下文」写 ✗。
7. **版本历史**（`#versions`）：本文件历史版本列表（`--out` 目录下的同名 `-vNNN.html`）。
8. **页脚**：生成命令、state 指纹、本文件的 `schema` 版本。

### 样式

沿用项目既有合同风格：深色 `#10171b` 底、`#e6eeed` 字、`"Microsoft YaHei"`、`main{max-width:1400px}`。状态色：通过 `#4ade80`、拒绝 `#f87171`、待审 `#fbbf24`。表格用 `overflow-x:auto` 包裹，首列 `position:sticky`。加 `@media print`：白底黑字、去掉导航、展开全部 `<details>`。

### 归档

所有合同放在**项目下的一个合同文件夹**里：`<项目>/导演制作合同/`。

- 主合同（整片）：`导演制作合同/导演制作合同.html`
- 单镜视频制作合同：`导演制作合同/导演制作合同-镜头S01.html`
- 主合同历史归档：`导演制作合同/导演制作合同-vNNN.html`
- 被拒版本一律在文件名里带 `-rejected`：`导演制作合同/导演制作合同-镜头S01-rejected.html`

一个项目一个合同文件夹，人打开面板点进项目直接看到这一堆；项目下其他目录不会混进来。

**命名是识别协议，不是习惯**：AIGC 设计面板只把匹配 `^导演制作合同(-v\d+|-镜头[^\s.]+)?(-rejected)?\.html$` 的文件当成视频合同列出来；带 `-rejected` 的一律不显示，其他命名的 HTML（如 `设计审阅-v001.html`、`镜头制作台-v001.html`）也不显示。所以新合同必须严格用这套命名，否则人在面板里看不到它。

### 渲染单镜合同

```bash
# 单镜
python contract_html.py <state.json> --project <project.json> --shot S01 --out <项目>/导演制作合同
# 全部镜头各出一份
python contract_html.py <state.json> --project <project.json> --shots --out <同上>
```

不带 `--shot` / `--shots` 时行为不变，渲染整片主合同。单镜页面自带：镜头设计、静态帧、视频生成参数、本镜合同记录、相关一致性告警、返回主合同链接。

## 五、一致性检查

`consistency(state, project)` 返回问题列表，接进 `plan()` 的 `result['consistency']` 和 HTML 的页头警示条。检查项：

1. 镜头引用的 `asset_id` 在资产库里不存在。
2. 同一 `asset_id` 在不同镜头里 sha256 不一致（身份漂移）。
3. 组内 `shot_ids` 之和与 `target_seconds` 偏差超过 20%。
4. 组内镜头 `duration_seconds` 之和与组目标不符。
5. 镜头 `group_id` 指向不存在的组。
6. `approved` 合同的指纹与当前内容不符（认可过期）。
7. 台词 `source=measured` 但无实测依据字段。
