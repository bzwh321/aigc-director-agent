# 导演 Agent 交接

## 入口

导演根目录：`D:/知识库/persons/AIGC导演`

交接时读取：

- `../../AGENTS.md`：当前导演总控规则；
- `../../SKILL.md`：导演能力入口；
- `../../workflow_manifest.json`：角色路径与调用条件；
- `../../方案库/SKILL.md`：视频执行前的方案选择。

通常导演按需加载专业 Skill；但本 Skill 是用户确认的项目级例外。每个拟生成镜头必须调用 `shot-design`、`sound-design`、`scene-design`、`action-design`，简单单镜和已有图片都不能跳过。场景角色可以返回复用核对，声音角色可以返回无对白音效方案，但四个角色都要有实际调用记录和当前版本产物。

## 任务包

```json
{
  "origin": "couple-pet-daily-video",
  "director_invocation_active": true,
  "phase": "design | contract | final_review",
  "episode_id": "YYYYMMDD-short-slug",
  "aspect_ratio": "9:16",
  "video_generation_mode": "h3_full_modal_native_audio",
  "native_audio": true,
  "external_audio_input": "none",
  "emotion_arc": [],
  "prosody_cues": [],
  "required_role_calls": {
    "shot_design": "required",
    "sound_design": "required",
    "scene_design": "required",
    "action_design": "required"
  },
  "source_dialogue": [],
  "rewrite_permission": "verbatim | light_cleanup | adaptive",
  "speaker_cast": {
    "speaker_a": "cat | pig | unconfirmed",
    "speaker_b": "cat | pig | unconfirmed"
  },
  "scene_facts": [],
  "character_assets": [],
  "dialogue_timeline": [],
  "shot_draft": [],
  "must_keep": [],
  "must_avoid": [],
  "generation_authorization": {
    "static_images": "approved scope or pending",
    "video": "approved scope or pending",
    "automatic_retries": 0
  }
}
```

`director_invocation_active=true` 表示已经进入导演阶段。导演直接返回当前阶段结果，不再次调用 `couple-pet-daily-video`。

## 阶段返回

- `design`：返回角色资产使用情况、逐镜意图、配音分镜、动作与场景设计，以及需要用户判断的静态图。
- `contract`：在静态图通过后，返回镜头秒数、素材职责、主体/摄影机/环境动作、声音、具体实现方案、服务、次数、规格、成本状态和验收点。每个视频节点必须标记 `h3_full_modal_native_audio`、`native_audio=true` 与 `external_audio_input=none`，并列出逐字台词、声线、逐短语情绪弧线、重音/停顿/语速/呼吸、口型对象和错词/错情绪/无口型停止条件；不得写成普通图生视频加 TTS。合同逐镜附 `role_call_evidence`，记录四个必需角色的 call_id、输入摘要指纹、输出版本和路径。
- `final_review`：读取实际成片，核对合同、口型对象、对白顺序、动作完成度、角色一致性、竖屏构图和音画质量，返回真实文件与已知问题。

每次实际调用记录调用 ID、输入摘要指纹、阶段、状态和返回路径。`prepared` 只是准备完成，不能写成导演已执行。相同输入已有完成结果时先复用；状态未知时先查原调用，不重复提交。

静态图属于角色和场景审核材料，可以作为 H3 的视觉参考或首尾状态，但导演不得把“用到参考图”解释为回到无声图生视频路线。全模态节点必须由同一次 H3 生成共同完成动作、对白、情绪、声音与动物口型。导演在提交前先把情绪拆成可听见、可计时、可验收的短语级变化，并绑定相应画面动作；只写“生气”“可爱”等单词不算完成声音设计。H3 原生有声出现错词、错情绪、平读或口型失败时先返回用户，不自动接入外部 TTS 或改走其他模型。

每镜统一输出 `director_shot_package`：

- `storyboard`：叙事目的、景别、轴线、视线、起止状态、切点与时长；
- `camera`：运镜类别、路径、速度、起止和停稳，以及转场承接；
- `voice`：说话人、原文、意图、声线、情绪弧线、韵律和口型对象；
- `action`：逐主体动作、重心、接触、惯性、次数、停止条件与末态；
- `scene`：空间、路线、接触面、遮挡、道具、光线和连续性；
- `sound_effects`：对白、拟音、环境、静音区、音乐避让和声音桥。

六项不是并列文案清单，而要共享同一时间轴。比如一句重音触发抬爪时，动作角色给出受力和落点，声音角色给出重音与接触声，镜头角色给出机位与是否跟随，场景角色确认路径和接触面；总控消解冲突后才交提示词角色。缺一项即停在合同阶段。

画外角色属于镜头合同，不是临场可见资产。若 `storyboard` 或用户设定某角色始终画外，`camera`、`action`、`scene` 与 `sound_effects` 必须共同用画缘局部手势、既有道具、主体视线、构图留白、画外声音和切点表达其动作；不得让提示词角色擅自生成该角色的脸、身体、侧影、倒影或影子。任何可见局部都要列明数量、进入边缘、路径和离场方式。
