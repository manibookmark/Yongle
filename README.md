# 永乐 · Yongle

**永乐**是一款基于明代公版《永乐大典》留存抄本笔意打造、免费开源可商用的简体中文字体（SIL OFL 1.1 协议）。

简体常用版保留明初官修台阁体的横细竖粗、微扛肩与圆润折肩顿笔，同时针对现代简体字结构、连续横排阅读与中英数字混排做了系统性字重与基线校准。本仓库同时开源了造字过程中提炼的通用 AI 中文字体设计 Skill **`cjk-ai-font-design`**（MIT 协议），方便大家借助自己的 AI Agent 打造属于自己的中文字体。

> 字体目前仍在持续打磨完善中，如果你在使用或在线试排时发现任何错字、字形瑕疵或中英标点排版问题，欢迎随时提 [Issue](https://github.com/manibookmark/Yongle/issues) 反馈！

## 在线试排

**[打开永乐在线试排页](https://manibookmark.github.io/Yongle/)**。可输入任意中文、英文、数字与标点实时预览，支持切换字号，超出字库的字符会自动提示。

![永乐简体常用版实机渲染样张](docs/specimens/chinese.png)

## 下载与安装

| 字体 | 适用场景 | 下载 |
| --- | --- | --- |
| 永乐 简体常用版 | 中文标题、正文与中英数字混排。**v1.0.5**，覆盖 3,500 个一级汉字及 132 个永乐笔意配套字符（英数及中英文双标点）。 | [简体常用版 ZIP（v1.0.5）](https://github.com/manibookmark/Yongle/releases/download/v1.0.5/Yongle-SCCommon-v1.0.5.zip) |
| Yongle Latin | 英文标题。覆盖 99 个字符，包括 A–Z、a–z、数字、空格和常用标点。 | [英文版 ZIP](https://github.com/manibookmark/Yongle/releases/download/latin-v1.0.0/Yongle-Latin-v1.0.0.zip) |

解压后安装 TTF，在软件的字体列表里选择对应名称即可。

### v1.0.5 主要更新

- **全 3,500 汉字 100% 统一至新流程**：重做并校准全部 817 个早期粗笔轮廓字，全库正文灰度统一；
- **结构审计与双参考错字清零**：对照国标楷体筛查并精修 11 处隐形错字（`赣、禀、搀、粱、鬓、凿、孵、姊、兜、壁、匆`）；
- **132 个配套英数与中英文双标点成套重造**：按《永乐大典》台阁体笔意重画直立书刊风英文（`A–Z`、`a–z`）、直立数字（`0–9`）、32 个英文比例标点与 30 个中文全角成对标点，补齐中文弯引号 `“”‘’` 与无缝连贯破折号 `——`，并统一校准中英光学基线。

## 开源通用造字 Skill：`cjk-ai-font-design`

想用自己的 AI Agent（**Codex、Antigravity、Claude Code、Cursor** 等）设计一套属于自己的中文字体？这套 Skill 已经打包在本仓库 [`skills/cjk-ai-font-design/`](skills/cjk-ai-font-design/) 目录下（MIT 协议）。

### 一句话安装（推荐）

不用手动建目录，也不用提前敲命令。**直接复制下面这句话发给你的 AI Agent**，它会自动把 Skill 装到全局目录并安装所需 Python 依赖：

> 帮我安装这个开源技能：`https://github.com/manibookmark/Yongle/tree/main/skills/cjk-ai-font-design`，放到当前 Agent 的全局 skills 目录，并运行 `scripts/setup_env.py --install` 检查安装所需 Python 依赖。

命令行备选：

```bash
npx -y skills@latest add manibookmark/Yongle --skill cjk-ai-font-design -g -y
```

详细用法与脚本说明见 [`skills/cjk-ai-font-design/README.md`](skills/cjk-ai-font-design/README.md)。

## 许可证

- **字体本体**（`Yongle-SCCommon` / `Yongle-Latin`）：采用 [`OFL.txt`](OFL.txt)（SIL Open Font License 1.1），可免费用于个人与商业设计、嵌入与修改；分发字体文件时请附上版权声明与许可证，不得单独出售字体文件。
- **造字 Skill 与配套脚本**（`skills/cjk-ai-font-design/`）：采用 [`MIT License`](skills/cjk-ai-font-design/LICENSE)。
