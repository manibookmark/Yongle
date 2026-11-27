# CJK AI Font Design Skill (`cjk-ai-font-design`)

一套从 **3,500 字《永乐大典》台阁体简体常用版（[Yongle](https://github.com/manibookmark/Yongle)）** 250+ 批次实战中提炼出的开源 AI 中文字体设计 Skill，采用标准 `SKILL.md` 格式，兼容 **Codex、Antigravity、Claude Code、Cursor** 等主流 AI Agent 工具。

## 一句话安装（推荐）

不用手动建目录，也不用提前敲命令。**直接复制下面这句话发给你的 AI Agent**（Codex / Antigravity / Claude Code / Cursor 均可），它会自动把 Skill 装进对应全局技能目录并补齐 Python 依赖：

> 帮我安装这个开源技能：`https://github.com/manibookmark/Yongle/tree/main/skills/cjk-ai-font-design`，放到当前 Agent 的全局 skills 目录，并运行 `scripts/setup_env.py --install` 检查安装所需 Python 依赖。

如果你习惯用命令行，也可以一行装好：

```bash
npx -y skills@latest add manibookmark/Yongle --skill cjk-ai-font-design -g -y
```

## 它解决了什么痛点？

要做一套真正有毛笔或手写韵味的**数千字原创中文字体**，几乎都会遇到四道坎：

1. **字重漂移与“减细即变电脑楷体”**：单生几个字、或者整图塞满少笔画字，再下达“把字减细”指令，字形会立刻漂成僵直的普通电脑楷体。
2. **肉眼扫图必漏的隐形错字**：AI 生汉字极易少一点（`孵→卯+孚`、`搀→挽`）、少一横（`禀` 缺内口、`算` 少一横）、换错偏旁（`粱→梁`、`姊` 右成 `市`）或结构错位（`赣`）。
3. **中英数字标点混排脱节**：汉字精修变清秀后，配套英文字母与标点容易显得偏粗过宽，数字易带斜度，混排时视觉割裂。
4. **工程失控**：逐字拉伸轮廓导致「一、二、小」撑满字格；自动扫描目录误把废弃实验批合进正式字体。

本 Skill 把上述经验固化为一套**可复现、可审计、跨 Agent 通用**的 6 阶段工作流与开箱即用的 Python 工具脚本。

## 目录结构

```text
cjk-ai-font-design/
├── SKILL.md                        # Agent 完整工作流与避坑硬约束
├── LICENSE                         # MIT License（Skill 代码与提示词）
├── scripts/
│   ├── setup_env.py                # 一键检查并自动安装 Python 依赖
│   ├── plan_batches.py             # 疏密混排 4×4 满 16 字批次规划器
│   ├── trace_batch.py              # 留白切格 + vtracer 矢量化 + keep_sheet_scale 建库
│   ├── audit_glyphs.py             # 孔洞数+像素差异错字审计 + 笔宽监控 + 国标结构参考条生成
│   └── merge_release.py            # 冻结底本 + 白名单安全合入 + 全量 TTF/WOFF2 校验
├── references/
│   ├── prompt-templates.md         # 母样定标 / 16字批量生图 / 双参考错字精修提示词
│   └── qa-checklist.md             # 四道硬验收门禁清单
└── templates/
    └── specimen.html               # 离线交互试排器（含横排 & 古籍朱丝栏竖排）
```

## 装完怎么开始？

安装完成后，直接把下面这句话按你想要的风格改几个字发给 Agent，先从一个 160 字小范围 MVP 起步即可：

> 用 `cjk-ai-font-design` 技能，帮我设计一套带手写行楷韵味的简体中文字体。先用 16 个控制字定标母样图，我确认笔形和字重后，按疏密混排的 16 字批次先做出 160 个高频常用字，并用 `audit_glyphs.py` 对照系统楷体做并排错字核查。

## 开源许可说明

- 本 Skill（`SKILL.md`、Python 工具脚本、提示词模板与试排器）：采用 **MIT License** 开源。
- 永乐字体本体（`Yongle-SCCommon`）：采用 **SIL Open Font License 1.1（OFL 1.1）** 开源，可免费用于个人与商业设计。
