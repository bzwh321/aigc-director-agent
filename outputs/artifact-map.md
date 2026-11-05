# Artifact Map

| 产物 | 位置 | 生命周期 | 可见性 |
|---|---|---|---|
| 导演问题单 | `outputs/<project>/<unit>/director-intake.md` | 项目期间 | 用户可见 |
| 镜头设计合同 | `outputs/<project>/<unit>/shot-contract.md` | 长期 | 用户可见 |
| 工作流设计包 | `outputs/<project>/<unit>/workflow-design.md` | 长期 | 用户可见 |
| 付费门禁 | `outputs/<project>/<unit>/budget-gate.md` | 长期证据 | 用户可见 |
| 审核报告 | `outputs/<project>/<unit>/qa-review.md` | 长期证据 | 用户可见 |
| 导演制作合同/导演制作合同.html | `<项目>/导演制作合同/` | 主合同（整片），由 contract_html.py 生成，不手工编辑 | 用户可见 |
| 导演制作合同/导演制作合同-镜头S01.html | `<项目>/导演制作合同/` | 单镜视频制作合同，被拒版本改名带 -rejected 并在面板隐藏 | 用户可见 |
| 导演制作合同/导演制作合同-vNNN.html | `<项目>/导演制作合同/` | 主合同历史归档，保留不删 | 用户可见 |

媒体文件不进入本Agent目录；只记录路径、哈希和用途。
