# 导演总控与专业设计交接 V2

总控把人的需求翻译为导演简报；镜头与声音并行设计，汇合并冻结时轴后，再依次完成场景、动作、提示词和节点。节点最终由总控选择。

## 调用与产物

总控读取 manifest，给当前角色简报与上游产物，加载该角色 AGENTS.md 和自有 Skill。六个前期/生成设计角色与两个后期角色由宿主调度；没有委派能力时在当前上下文分阶段执行，不能声称启动了八个 Agent。脚本不会调用模型。

PowerShell 示例：`Get-Content -Raw -Encoding UTF8 examples/production_state.json | python -X utf8 workflow.py`。`python scripts/demo_production.py` 演示依赖与返工，不生成媒体。

状态入口 `schema_version=director-production/v2`。`artifacts` 中每个阶段记录 `revision`（正整数）、`status`（draft/accepted）、`owner`、`approved_by`、`inputs`（直接上游版本）、`input_hashes`（上游data的规范JSON SHA256）和 `data`（正文）。accepted 表示总控接受设计，不等于用户批准付费；approved_by是责任记录，不是认证令牌。

| 阶段 | data字段 |
|---|---|
| director_intent | user_request、interpretation、audience_feeling、perspective、constraints、has_dialogue |
| shot_design | shots[]：shot_id、purpose、shot_size、perspective、duration_seconds（草案）、has_dialogue、transition |
| sound_design | has_dialogue、dialogue[]：line_id、speaker、text、duration_seconds、measured、audio_path；sound_cues[]、mix_plan |
| timing_lock | locked=true、basis、duration_seconds、timeline[]：shot_id、start、end、dialogue_ids |
| scene_design | assets[]：asset_id、path、role、status；shots[]：shot_id、space、asset_ids；continuity |
| action_design | shots[]：shot_id、beats[]（start、end、subject、camera、contact）、previs |
| prompt_design | shots[]：shot_id、reference_roles、prompt、negative、acceptance |
| node_design | selected_by=director、shots[]：shot_id、mode、node_class、inputs；capability_evidence、cost_preview、auto_retry=0 |

分镜、场景、动作、提示词与节点始终用同一组 shot_id。没有对白时 dialogue=[] 合法；sound_cues=[] 也可用于完全静音设计，但 mix_plan 必须有说明。

## 声音决定时轴

先锁角色底声与逐句表演，得到认可的干声后实测句长、句间静音和尾音。估算秒数只用于草案，不冻结正式时轴。若没有付费授权，保留待生成/待测量状态，不虚构实测值。旁白、画外音同样占用时长。

时轴容纳台词、停顿、动作和反应。当前检查器要求每句恰好归属一个镜头；跨镜对白按同源音频实际区间拆成不同 line_id，避免重复计时。音效设计可先计划，动作设计后再核对同步点与最终混音。

## 版本与回退

需求变更使全部下游失效；分镜或对白变更使时轴及其下游失效；场景变更使动作、提示词、节点失效；动作变更使提示词、节点失效。节点能力不足时总控退回最接近的设计层，不偷偷改时长或参考。

总控接收产物后更新revision及上游指纹。检查器递归验证上游是否有效，即使下游自身版本没变也能识别过期。输入文件实际存在、音频实测真实性、节点端口正确性和审美仍需要执行前检查，不能仅靠JSON status证明。

## 执行、展示和兼容

V2.1 在生成后新增后期链路，字段和调用门禁见 `post-production.md`。前八项仍在 manifest.stages，后期在 post_stages；旧设计示例不需要虚构视频来通过。status=DESIGN_READY 仅表示生成前设计齐备，另看 post_status 和 ready 判断后期进度。特效、调色必须等待已验收视频，不作为前期并行角色。

正式执行前核对真实素材文件、节点版本、模式、时长、分辨率、费用范围及批准记录。离线规划器永远返回 execution_authorized=false。

静态图不能证明动作连续，接口成功不能证明镜头合格。自动媒体检查与人工审片分别记录。对白只对可见说话嘴部安排后置口型流程。

examples/production_state.json 为 example_only=true 的教学数据，路径和时间不是实际生成证据。V1无schema输入继续走旧G1–G8检查；其DESIGN_READY仅表示旧问卷齐全，新制作必须使用V2。
