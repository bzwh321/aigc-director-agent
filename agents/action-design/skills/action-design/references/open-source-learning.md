# 开源方法来源与适用边界

核对：2026-10-13。状态：一手文档已阅读，方法已转译为本地Skill；本轮未安装、运行或验证生成效果。引用是概念借鉴，不复制项目代码或宣称它们已经接入本机。未来安装/分发时再核对各项目代码、模型及依赖许可证。

| 来源 | 文档实际提供什么 | 我们据此形成的方法（推导） | 不应声称 |
|---|---|---|---|
| [SAM 2 官方仓库](https://github.com/facebookresearch/sam2) | 图像提示分割、视频多对象掩码传播与object IDs | 用稳定subject_id对应可见区域，复杂遮挡可用分割/跟踪辅助读图及审片 | 分割能识别动机、材质刚度、隐藏连接，或能自动决定动作 |
| [DragAnything 官方仓库](https://github.com/showlab/DragAnything) / [README](https://raw.githubusercontent.com/showlab/DragAnything/main/README.md) | 用实体表示与轨迹控制多个对象，演示前景/背景及摄影机运动控制 | 轨迹必须绑定对象；每个主体的位移与摄影机分开描述，先明确参考系 | 二维轨迹保证三维运动、关节表演、碰撞正确；所有视频API都支持其输入 |
| [PhysDreamer 项目](https://physdreamer.github.io/) / [代码](https://github.com/a1600012888/PhysDreamer) | 静态3D对象的材料场估计及受外力后的动力学响应；仓库要求场景、优化速度和材料字段 | 动作需考虑驱动力、材料、作用部位、约束和响应，而非只写运动方向 | 单张图足以测出物理真值，或该项目可直接解决整幅复杂场景/人物表演 |
| [Motion Canvas 开源仓库](https://github.com/motion-canvas/motion-canvas) / [flow 文档](https://motion-canvas.io/api/core/flow/) | all并行，chain串行，sequence按延迟错峰启动，waitFor/waitUntil等待 | 用明确时序表达独立过程、事件依赖与停后保持；错峰可以重叠 | 其动画调度语义等于生成模型的逐秒硬控制；2D动效能代替物理预演 |

本次没有采纳无法获取的 Blender 页面或不存在的仓库链接为证据。后续遇到明确知识缺口才读相关源，不每次遍历全部项目。

## 参考视频的动作解析（2026-10-14归档）

用户已同意把视频动作解构研究保存为本地学习资料，见 [视频动作解析](video-motion-analysis.md)。包含Qwen3-VL、MMPose/RTMPose、CoTracker3、Kinovea、GVHMR、SAM 3D Body和PySceneDetect的一手来源、用途、限制、许可注意事项及验证顺序。仅资料归档；未安装、未下载权重、未运行、未上传视频。需要分析参考片时才加载，不把候选工具当成已具备的执行能力。

## 与用户已有经验合并

- 已确认：全图是相互作用系统；各主体可动可静但都需有理由；刚性与固定位置不同；活体生命感需在相应组织体现；一次动作要有停止与保持。
- 保留出处：`motion-systems.md`、`../../../../../references/subject-intent-motion-review.md`。
- 历史反例：静态平面运镜后Edit不能凭提示词创造缺失动作。参考 `历史复盘笔记/20260930-005500-seedance-motion-mode-lessons.md`；此为历史记录，未在本轮重跑。真实微小平移不一定有显著视差，不能套用旧资料的绝对表述。
- 待验证：本次方法在新的静态图上的覆盖、可读性和生成可实现性；下一张实际图用于校准，不将文字用例冒充成片验收。
