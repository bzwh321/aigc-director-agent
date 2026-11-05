# H3原生对白：官方格式与验收边界

适用：MiniMax H3 Ref2VA/全参考输入的原生有声多人对白。依据官方仓库提交 `d21241f0a4b3acbb34c97dae47fa417b7065e438` 的 h3-prompt-writing skill 及 ref-en 5.1/5.4、base-en 4.2/4.4；2026-10-22核验。服务升级后复核当前节点和官方文档。

## 编译规则

- 六个英文段按此顺序：`subject_definitions`、`summary`、`retention_analysis`、`detailed_description`、`overall_soundscape`、`non_diegetic_music`。描述用英文，实际台词保留原语言。
- `<Subject N>`定义人物或可见内容；`<Picture N>`对应真正送入模型的第N张图，勿把角色编号当上传槽位或脸部注册ID。
- `(S1)`、`(S2)`等按目标视频实际发声先后分配一次，跨镜复用。它们不是持久音色库ID，也不能保证跨独立生成天然保持音色。
- 发声句写出视觉主体和说话人：`<Subject 1> (S1) asks, <d>[Chinese] 是谁省心？</d>`；再发声仍用同一主体和S编号。这里只是格式示例，不能固定角色映射到项目之外。
- `<d>`内仅语言标签及应说正文；身份、动作、情绪、延音和静默说明放外部，不朗读舞台指示。保留用户原词，不擅自加词、重复字或发明SSML停顿控制。
- `retention_analysis`不加说话人ID。第一镜用`[Shot 1]`，后续可写`[Shot 2] At 00:01.250, the camera cuts to ...`；规划时间非精确执行保证，切点递增且容纳完整台词，不硬切断词尾。
- 仅当确实供入音频时才定义`<Audio N>`；`<scenetrans>`只用于同句跨镜，`<cutoff>`只用于有意截断。没有这些需求则不添加。

## 中英表演翻译入口

所有中文表演要求转英文时，先应用声音角色的通用 [中英表演翻译规范](performance-translation.md)，再按本文编译H3标签。本文件后半的项目样片仅为附属案例，不承担通用翻译标准。

## 词级表演与角色画面

先按含义组织意群，再落实轻重、局部语调和词内情绪。若用户的“你……”是连续延音，在`<d>`外明确`continuously sustain the voiced vowel; not silence`；若明确要求停声，则写`stop vocalizing briefly`，并说明停在何词后。省略号本身不能保证实现。轻音须清楚，不等于吞词。

根据当前剧本把每次接话对应到发声角色、画面可见嘴、视线和动作；多人错配时可采用每次接话切当前人物近景，但单人近景仍不自动等于正确声音。继承已通过前镜的实际末态，参考图外观不等于恢复其旧托腮、赠菜或重复递纸动作。

## 服务链和交付检查

核对应用当前有效图，确认文本是否原样进入H3编码、是否经活动增强器，以及参考图顺序。应用标题“提示词增强”不是增强器生效证据。用当前导出图和节点源码区分已验证链路与未认证云端版本；不能把某个应用节点号写成所有H3固定接口。

保存实际发送文本和哈希、5句或当前全部对白、主体/说话人序列、真实参考图映射及授权范围。静态格式通过不证明生成效果；ASR只辅助查词和时间，不能证明音色归属、情绪或口型。不得将缺少官方格式断言为历史错配的唯一原因。出现错词、漏句、串人、平读、延音变死停或动作复位时保持未通过，按现有授权停止，不自动重试。

官方资料：
- https://github.com/MiniMax-AI/MiniMax-H3/blob/d21241f0a4b3acbb34c97dae47fa417b7065e438/skills/h3-prompt-writing/SKILL.md
- https://github.com/MiniMax-AI/MiniMax-H3/blob/d21241f0a4b3acbb34c97dae47fa417b7065e438/skills/h3-prompt-writing/references/ref-en.txt
- https://github.com/MiniMax-AI/MiniMax-H3/blob/d21241f0a4b3acbb34c97dae47fa417b7065e438/skills/h3-prompt-writing/references/base-en.txt

## 潜台词与复合情绪已通过案例

2026-10-23，示例短片 S06 v020，用户评价“哎，对了，非常好”并要求写入配音skill。该8秒H3 Plus原生声画样片已获用户认可，无后置变声、延音或倍速修补；只作为这一组合方案的案例证据。

### 中文语境到英文表演

豆包原句：“路的问题，可以饭后再研究。再不吃，鹅都凉了。”主要说给DeepSeek听。表面催饭、饭后再聊；潜台词是细节暂搁，趁眼前机会推进生意，别错过交易时机。此前“嫌争论烦、着急吃饭”的解释被用户纠正。

有效输入先明确语义，再写复合情绪及词级处理（均在`<d>`外）：

> She uses talk of dinner as socially acceptable cover for a business nudge: set aside the road detail for now and keep the deal moving while the opportunity is still open.

> Her delivery is shrewdly tactful and knowingly coaxing, with discreet deal-making urgency beneath a convivial surface.

具体落到“路的问题”轻带、“饭后”给台阶、“再研究”轻收、“再不”略收紧、“凉”低而有分量地落住；“鹅”自然带过，不夸张成食欲笑料。用轻重、局部音高走向和语速变化表达会意劝进，不靠全句增大音量、播报式逐词强调或堆罕见词。豆包看向主要听者，克制微笑，原筷低幅示意菜后回看DeepSeek；不新增笑词或强迫延音。

### 中英情绪选词与回译

用户在样片通过后特别强调：“很重要的是中英文的翻译，相当于我们用更好的形容词实现了这个效果。”将准确选词作为后续表演翻译的重点，保留中文里的对象关系、分寸与情绪层次，避免只译成笼统的happy、urgent或impatient。

| 中文表演意图 | 本例采用的英文组合 | 要传递的分寸 |
|---|---|---|
| 机敏、懂场面、给人留台阶 | shrewdly tactful | 知道如何把事情往前推，话说得周全 |
| 会意地劝进 | knowingly coaxing | 让对方领会暗示，柔和地推动她行动 |
| 不露声色地提醒交易时机 | discreet deal-making urgency | 有催进的压力，表面仍克制 |
| 面上热络、维持饭桌客套 | beneath a convivial surface | 内外两层语气同时成立 |

从当前中文意图挑选英文形容词、动词和修饰语，再回译核对“听者会收到什么暗示”；若回译变成抱怨、厌烦或食欲催促，先修正词义再生成。选词要能连接到具体的轻重、音高走势、局部速度和动作，不堆彼此冲突的情绪词。此表是已通过案例的语境映射，不是四组词的普适替换表；后续保持相同翻译方法，按新对白重新选词。

### 声脸与镜头共同约束

同一角色连续两句可用一个完整`<d>`块、同一全局说话人ID，并在同一连续中景运镜里完成；需要桌面时小幅后撤展开圆桌，让发言者的嘴持续可读。这样可兼顾表演、桌面和运镜，不必机械地每句切极近特写。本例另有DS问话近景，全片两镜；不是固定镜数模板，也不保证其他输入必然免错配。

参考图须按职责筛选：已接受前镜末帧管起态和座位；人物图管身份。若末句需豆包发言，不用GPT正在说话的近景暗示末镜。v020用豆包带桌参考替换了该冲突参考，保留GPT左、豆包中、DeepSeek右；不能据此断言历史错配的唯一原因。

### 证据与适用边界

原片：`<PROJECT_ROOT>/<示例短片>/runs/S01-S06-contract-v002/S06-subtext-v020/示例-S06-趁热谈生意-v020.mp4`。
SHA-256：`c846575720474d7308be355867668595dfd97026f16d9c36a501595343ea9d5f`。
同目录`user-acceptance.json`记录用户认可，`review-before-user-acceptance.json`保留抽帧与ASR疑点；项目`previs/S06-subtext-v020/h3-native-prompt.txt`保存完整输入。

本次同时改变了语义、情绪描述、词级处理、参考图和镜头组织，未执行原提议的A/B试听且未固定seed；只能说用户认可该完整方案，不能证明复杂英文词单独优于普通词、英文总优于中文或声线可跨任务永久锁定。ASR疑点不是确证错词，Agent抽帧/转写检查不冒充实际听核。后续按当前对白重新解释与试听，本案例不授权追加生成或付费试验。
