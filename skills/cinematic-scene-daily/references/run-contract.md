# 每集运行合同

用户确认的默认制作根目录：`<PROJECT_ROOT>/<项目目录>`。一条视频一个文件夹，不写入导演安装目录，不沿用<示例项目>角色与音轨。原素材保留；正式采用的图片与音频另存入本集目录，候选素材仍可仅引用。

## brief 与建档

`examples/first-episode.json` 是可执行输入例子。修改故事和参数后调用：

```powershell
python "D:/知识库/persons/AIGC导演/skills/cinematic-scene-daily/scripts/daily_scene.py" prepare --brief "<绝对路径>/brief.json" --date 2026-10-12
```

输入含 series_id（英文短名）、revision（正整数）、title、organization、world_premise、style_id、output、music、shots。每镜必须有 shot_id、story、composition、lighting、duration_seconds、image_prompt、motion。brief 中保留 assumptions，不能把假设写成人审结论。

subject_motion 填 none/required/unknown，不能把“轻运动”自动解读为主体静止；未填则交总控澄清。镜头设计以 proposed facts 和 scene_brief 传入 V3 小上下文，仍可按人审修改。

默认输出 `<root>/<YYYY-MM-DD>_<series_id>/`，`--root` 仅在用户另行指定位置或隔离测试时覆盖。每个视频文件夹包含：

- `图片/`：各镜静态图与总览，文件带镜头号和版本。
- `音频/`：本片实际使用的音乐、截取或混音文件。
- `镜头视频/`：每镜生成或本地微动片段。
- `成片/`：合成结果及渲染记录。
- `制作记录/rNN/`：本轮版本的下列JSON文件；修改版本不改变所属视频文件夹。

- `brief.json`：本集创作快照；修改请求使用新 revision，旧审核不跨版本套用。
- `run.json`：输入指纹、日期、状态；生成期间由总控更新实际状态，prepare 不自动推进。
- `director-state.json`：V3 工作状态，初始 artifacts/reviews/completed_calls/issues 均为空。实际制作走原有 `workflow.py`，根据最新素材更新 brief 的 visual_source/asset_ids 和每镜 solution_facts，不使用占位文件充当静态通过。
- `edit.json`：本地剪辑清单模板；path=null 必须换为真实素材。生成视频填 kind=video，静态轻推拉填 kind=image。

相同日期、版本及相同 brief 会返回 resume，不重写状态。同日同版本输入变更返回冲突，不覆盖。目录存在但 run.json 缺失表示中断，需检查原文件再决定恢复；不能删掉重跑。前一日 run.json 的 status 非 completed/cancelled 时，prepare 阻止创建新一天，先处理积压。completed 仅在用户最终认可后由总控写入，不能凭成片文件存在代填。

同一天升 revision 时保留旧版本；总控明确新版本取代关系后，将旧 run 标 cancelled 并附 superseded_by 与决定来源，避免旧待审版本一直阻挡后续日期。脚本不擅自取消旧版本。

`run.json` 建议状态：planned → awaiting_image_budget（如需）→ awaiting_static_review → awaiting_contract → generating → assembling → awaiting_final_review → completed；问题状态 blocked。状态不是批准依据，批准原话、对应文件版本和 fingerprint 仍存 V3 reviews。不要伪造用户反馈。

## edit.json

导演调用由外层自动化完成。建档后运行 `daily_scene.py director-request --run-dir <制作记录/rNN> --phase contract` 可取得当前合同阶段任务包（设计或审片对应 design/final_review）。任务包绑定素材及方法文件哈希，尚不意味着已调用 Agent；宿主实际派发后才在 run.json.director_calls 写入调用ID与返回结果。完整职责与防递归约定见主 Skill 的“调用导演”段。本地 workflow.py 仍是导演的路由辅助程序。

```json
{
  "output": {"width": 1920, "height": 1080, "fps": 24},
  "music": {"path": "<实际音轨或带音轨视频的绝对路径>", "start_seconds": 0, "gain_db": 0, "fade_seconds": 0.25},
  "shots": [
    {"shot_id": "S01", "kind": "image", "path": "<实际图片>", "duration_seconds": 3, "start_seconds": 0, "fit": "pad", "zoom": 1.03}
  ]
}
```

真实清单有4–5镜。`fit=pad` 保全画面，`crop` 中心裁切须事先确认构图保护区；当前助手不支持自定义焦点或复杂转场。`zoom` 仅支持静态图的居中缓推，范围1–1.08，不能代表真实环境运动。视频按 start_seconds 裁取，每镜统一尺寸/帧率，关闭自带音频，以硬切拼接；复杂剪辑另选已可用的本地执行器。

```powershell
python "D:/知识库/persons/AIGC导演/skills/cinematic-scene-daily/scripts/daily_scene.py" assemble --edit "<视频目录>/制作记录/r01/edit.json" --output-root "<视频目录>/成片" --ffmpeg "<已核实的ffmpeg.exe>"
```

依赖 Python 标准库及本地 FFmpeg。脚本检查素材、音轨存在及可解析时长；音轨或视频片段不足时停止，不默默填黑、静音或循环。输入内容和 FFmpeg 版本加入渲染指纹，同输入成功结果复用；相同指纹有未完成目录时停止，由人检查。完成清单保存输出哈希，文件损坏/改变则报错，不自动再渲染。已有素材和源文件永不覆盖。

这是离线合成工具，不是人类授权认证器。总控在调用前必须完成适用人审并确认本次素材职责；脚本本身不会联网、调用模型、上传或写入 approved。

## 一次完整的验收

- 静态：整组有4–5幅真实图片；各镜有可读的小故事、空间层次和尺度，组内差异明显且风格统一。
- 合同：主体/环境/摄影机分开说明，并用主要驱动力、连接/接触、主次响应及保持项解释整幅画如何共同运动；活体设定需要可见的生命证据。方案库结果可追溯；音乐区间足够；具体服务、规格、次数、费用范围已核对并得到适用批准。
- 成片：逐镜/切点可解码、正确宽高帧率、音乐连续覆盖；实际取用区间里主要运动与连带反应可读，接触连续、刚性材料不融化，生命感不只来自背景雾。无明显几何漂移或突然增殖。自动检查通过不等于创作人审通过。
- 每日：相同任务重入不重复提交；失败/未知状态停止；修改素材只使受影响的认可过期；未确认前不自动发布到任何平台。

## 参考视频的本次证据（2026-10-12）

用户提供 `<PROJECT_ROOT>/<示例项目>/素材/示例素材.mp4`。

本地读取：2520×1080、30fps、355帧，约11.83秒；含AAC音轨。16个时间点接触表显示四组场景，约每3秒换景：树冠/宫殿水面、森林遗迹与兽群、云海中的垂直残构、巨树下的建筑群。画面可用来参考尺度层次、光影和剪辑密度；采样帧不足以证明原片使用何种生成模型或真实三维运镜。

旁边有 `10月4日.mp3`，FFmpeg估计约11.89秒；仅标为候选音轨，未作听觉判断或宣称与视频音轨逐样本相同。若用户选择“与参考一样的音乐”，优先从原视频音轨挂载以确保来源一致。公开使用的授权范围尚未提供，不把本地参考关系等同公开发布许可。

首集例子使用5×2.2秒=11秒以容纳参考音轨，是本轮草案参数；不是每天都用11秒。题材与配乐组织的用户选择到达后应更新草案。
