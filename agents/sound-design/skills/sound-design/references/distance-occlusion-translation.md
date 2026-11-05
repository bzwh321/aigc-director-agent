# 距离、遮挡与声场翻译

适用于声源移动、隔门/隔墙、开门显声及跨镜对白。保持当前角色、对白、模型与制作范围；本规范不授权新音轨、付费试音或重试。它是设计方法，不是已验证的模型控制能力。

## 分开写演员与听感

- 源声线：年龄感、性别呈现、音域、自然沙感、人物关系及情绪。演员用有投射力的呼喊，不代表听者会听到贴耳、明亮的干声。
- 接收声场：谁在听、声源在哪、是否移动、隔着什么、当前距离如何被听见。源声线固定，接收效果可以明显变化。
- 例如源声线可写 `a naturally lightly husky young adult female voice`；隔门阶段另写 `heard at a distance through the closed solid-wood door, with veiled articulation and softened consonant edges`。不要全程写 `clear and close` 后又要求远闷。
- 情绪与声场并行：`anxiously searching` 表演的是寻找；`distant and door-filtered` 才是听到的空间质感。不能让一组情绪形容词承担两种职责。

## 写清声音变化的物理事件

逐阶段记录：声源位置 → 听者/听点 → 遮挡状态 → 听感 → 进入/退出事件。没有测量时距离是设计关系，不伪造精确米数。时间标记只是目标，不冒充模型硬控制。

1. **远而被遮挡**：`distant, veiled and dull-edged; audibly filtered through the closed wooden door; softened consonants and subdued vocal presence`。初始音节可辨到什么程度按剧情决定；要求不够清楚，不等于默认整句无法理解或让演员含混吐字。
2. **走近但仍被遮挡**：`gain body and presence gradually as she approaches, while remaining audibly door-filtered; do not restore crisp articulation before the door opens`。接近是连续过程；演员不必随之用力越来越大，门也不会因为走近就消失。
3. **开门解除遮挡**：`at the first actual opening, sharply reveal the same voice: restore consonant definition, brightness and directness, not merely loudness`。把变化绑定实际门缝出现/门扇转动，不绑任意切镜或配乐冲击。按镜头节奏设计短促的解除过程，不要求在门尚未动时先变清晰。
4. **开门之后**：`clear but still several steps away, with the room's natural acoustic space; not a close-miked studio voice`。清晰不等于贴耳。切近景也不自动搬动听者或声源。

需要变化发生在同一句内时，标明具体词前后的接收差异，保持同一个演员与自然呼吸。不要要求在停声期仅靠门响证明人声已变清晰。若分成独立生成任务，明确存在音色、环境及动态重置风险；同一个S编号不能保证消除接缝。优先评估让关键声场转折留在同一段连续原生表演内，但不能自行改变用户已批准的生成范围。

## 中英回译校对

英文须能回译出：远还是近、闷还是亮、因何变化、在何时变化、谁说话、谁在听。`slightly muffled` 只表示略闷，不能用来满足明显的远闷→清晰对比；`louder` 不是 `clearer`。`intelligible` 指能辨词，不必等于齿音锐利、录音棚式干净。避免彼此抵消的全局形容词。

把源声线与接收声场放说明区；中文台词不改、不加英文台词、不朗读舞台指示。执行端只暴露提示词时，不发明低通频率、声像、分轨或自动化参数接口。可使用声学词描述目标听感，但不得声称已经执行滤波或混音。

## 实际听审

- 不看画面先听：是否仍能听出被遮挡、逐渐靠近、突然解除遮挡三个阶段？如果只能靠画面猜，不通过。
- 开门前后对比：是否同一演员、同句连续、字头细节恢复，而非仅增大音量或换人？
- 声音与动作对看：变化是否发生在门首次真实打开时，而非镜头切近时？撞击不能遮掉关键字。
- 远处喊声应有投射力；近处清晰声应仍有现场距离，不能换成旁白或耳语。
- ASR、响度和频谱可辅助定位，不能替代听审。当前不能实际听到时标 `unverified`；用户直接听评可以记录为用户反馈，不能冒充Agent独立听核。
