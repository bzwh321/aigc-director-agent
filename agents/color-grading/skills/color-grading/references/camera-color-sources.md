# 相机色彩、LUT与风格来源

核对日期2026-10-13。以下只借鉴方法，没有下载、分发或认证厂家LUT，没有在实际视频验证风格。品牌名说明参考方向，不代表合作或授权。

## 三种东西分开

1. **技术转换**：解释真实编码/色域，例如LogC4/AWG4到工作/显示空间。必须有相匹配的输入。
2. **创意Look**：改变已正确解释画面的明暗与色彩关系，不能凭名称冒充相机物理响应。
3. **完整成像系统**：传感器光谱响应、曝光、镜头、光源、编码与色彩管理共同影响结果。现成AI视频无法靠一个LUT恢复真实相机RAW信息或已经丢失的动态范围。

| 一手来源 | 已核对内容 | 本库如何用 |
|---|---|---|
| [DaVinci Color](https://www.blackmagicdesign.com/products/davinciresolve/color) / [Training](https://www.blackmagicdesign.com/products/davinciresolve/training) | 支持色彩管理、输入/时间线/输出变换、示波器与节点式调色 | 管理→校色→匹配→风格→输出，具体节点组织为我们的建议 |
| [ARRI Log C](https://www.arri.com/en/learn/camera-systems/image-science/log-c) / [REVEAL](https://www.arri.com/en/learn/camera-systems/image-science/reveal-color-science) | REVEAL包含相机处理链、AWG4与LogC4，不是一个通用滤镜 | 已知相机素材才用匹配技术变换；AI视频只用审美参考 |
| [ARRI Image Quality](https://www.arri.com/en/learn/arri-camera-technology/best-overall-image-quality) | 重视自然色彩、色彩分离及高光处理；完整成像链参与 | 柔顺亮部与自然色彩分离作为创意目标，不声称获得其动态范围 |
| [Sony S-Cinetone白皮书](https://pro.sony/s3/2020/03/24095333/S-Cinetone-whitepaper_v2.pdf) | S-Cinetone重视自然肤色/中间色调，亮部对比较柔和 | 人像观感参考；不要把已经烘焙的S-Cinetone当S-Log3再套还原LUT |
| [FUJIFILM ETERNA](https://www.fujifilm-x.com/en-gb/products/film-simulation/eterna/) | ETERNA电影模拟具有相对平缓的调子和克制色彩 | 克制饱和与柔和层次的审美参考；不是原厂精确复制，也不是ETERNA BLEACH BYPASS |

## LUT 使用前四问

- 它是输入转换、输出显示变换，还是创意Look？
- 它期望的输入gamma/gamut是什么，输出又是什么？当前节点处的信号是否匹配？
- 已经在RCM、CST、相机或导出中应用过等价处理吗？
- 来源、许可、版本、文件hash和作用强度是否记录？

任一技术条件不明，不直接烘焙。品牌LUT名称或网盘文件名不是能力证明；默认不下载不明来源LUT、不购买插件。选风格不会自动改变输入解释。
