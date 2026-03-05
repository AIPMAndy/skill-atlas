<div align="center">

# 🔍 SoSkill

**Skill 搜索与聚合引擎 | Skill Search & Aggregation Engine**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/AIPMAndy/soskill?style=social)](https://github.com/AIPMAndy/soskill)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://python.org)
[![Skill Audit](https://img.shields.io/badge/Skill%20Audit-Enabled-success)](docs/skills-audit.md)

[English](#english) | [简体中文](#中文)

</div>

---

<a name="english"></a>

## 🎯 What is SoSkill?

SoSkill is an open-source Skill search and aggregation engine that:

- 🔄 **Auto-fetches** skills from multiple sources (official + community)
- 📊 **Unifies** structure (name, description, source, link, path)
- ⏰ **Auto-updates** via GitHub Actions (scheduled + manual trigger)
- 🛡️ **Audits risk patterns** in skill metadata/content (malicious command, prompt override, credential leak hints)
- 📁 **Outputs** reusable data files (JSON/CSV/Markdown)

## ✨ Current Data Sources

| Source | Type |
|--------|------|
| `openai/skills` | Official (`.curated` + `.system`) |
| `VoltAgent/awesome-openclaw-skills` | Community |
| `AIPMAndy/awesome-openclaw-skills-CN` | Community (Chinese) |

> Sources are configured in `config/sources.json` — easily extensible.

## 🆚 Why Skill Audit Matters

| Problem | Without audit | With SoSkill audit |
|---|---|---|
| Dangerous shell patterns | Hard to detect manually at scale | Rule-based scan for `curl|bash`, destructive commands |
| Prompt override / jailbreak text | Often hidden in long docs | Pattern detection + severity levels |
| Credential leakage hints | Easy to miss in community skills | Dedicated credential-risk rules + report |
| Trust before adoption | Subjective judgement | Repeatable JSON/Markdown evidence |

## ⚡ Quick Start

```bash
# Clone the repo
git clone https://github.com/AIPMAndy/soskill.git
cd soskill

# One command (recommended): fetch + stats + security audit
python3 scripts/run_workflow.py --mode secure-refresh --out-dir data
```

For higher API rate limits:

```bash
export GITHUB_TOKEN=<your_token>
python3 scripts/fetch_skills.py
```

Optional reliability flags (recommended):

```bash
python3 scripts/fetch_skills.py \
  --config config/sources.json \
  --output data/skills.json \
  --csv data/skills.csv \
  --markdown docs/latest.md \
  --min-total 1 \
  --max-retries 2 \
  --retry-delay 1.0 \
  --timeout 30
```

Notes:
- `--max-retries`: retries for transient 403/429/5xx and network errors
- `--retry-delay`: exponential backoff base delay in seconds
- `--timeout`: per-request timeout in seconds
- `--min-total`: prevents overwriting outputs when fetched total is unexpectedly low

## 🧩 Install as a Codex Skill

This repository now includes an installable Codex Skill package at `skills/public/soskill`.

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo AIPMAndy/soskill \
  --path skills/public/soskill
```

After installation, restart Codex to pick up the new skill.

## 📦 Output Files

| File | Description |
|------|-------------|
| `data/skills.json` | Full aggregated data |
| `data/skills.csv` | For filtering & analysis |
| `docs/latest.md` | Latest fetch summary |
| `data/collections.json` | Structured collection data |
| `data/skills.audit.json` | Skill risk audit result (structured findings) |
| `docs/skills-audit.md` | Human-readable security audit report |

## 🛡️ Skill Safety Audit

```bash
# Fast local audit (metadata-only, no network fetch)
make audit

# Deep audit (fetch SKILL.md content, with retries)
make audit-deep
```

Default risk checks include:
- destructive commands (`rm -rf`, force reset/clean)
- remote execution pipes (`curl|bash`, `wget|sh`)
- prompt override / jailbreak-like instructions
- credential collection / exfiltration hints

Risk levels:

| Level | Meaning | Action |
|---|---|---|
| `critical` | likely unsafe or directly destructive | block immediately, manual review required |
| `high` | strong suspicious signals | quarantine and review |
| `medium` | risky pattern in context | review before use |
| `low` | weak signal | track and monitor |
| `clean` | no matched rules | still review for business fit |

Recommended release gate:

```bash
make refresh
make audit
# Optional deep scan for top-N skills before release
make audit-deep
```

## 🧭 One-command Workflow Modes

```bash
# fetch + stats
python3 scripts/run_workflow.py --mode refresh --out-dir data

# fetch + stats + audit (recommended)
python3 scripts/run_workflow.py --mode secure-refresh --out-dir data

# fetch + stats + audit + organize
python3 scripts/run_workflow.py --mode full --out-dir data

# bootstrap collections + local organize (requires existing skills snapshot)
python3 scripts/run_workflow.py --mode offline --out-dir data --skills-input data/skills.json

# preview offline actions without cloning/pulling
python3 scripts/run_workflow.py --mode offline --out-dir data --skills-input data/skills.json --bootstrap-dry-run --dry-run
```

## 🤝 Author

**Andy | AI Product Expert**

- 🚀 Ex-Tencent / Ex-Baidu AI Product Lead
- 🦄 LLM Unicorn VP → Startup CEO

**WeChat:** AIPMAndy | **GitHub:** [@AIPMAndy](https://github.com/AIPMAndy)

---

<a name="中文"></a>

## 🎯 SoSkill 是什么？

SoSkill 是一个开源的 Skill 搜索与聚合引擎：

- 🔄 **自动抓取** 多来源 Skill（官方 + 社区）
- 📊 **统一结构**（名称、描述、来源、链接、路径）
- ⏰ **自动更新**（GitHub Actions 定时 + 手动触发）
- 🛡️ **安全审核** Skill 文本中的风险模式（恶意命令、越权提示、凭据外传等）
- 📁 **输出文件**（JSON/CSV/Markdown）

## ✨ 当前数据源

| 来源 | 类型 |
|------|------|
| `openai/skills` | 官方（`.curated` + `.system`） |
| `VoltAgent/awesome-openclaw-skills` | 社区 |
| `AIPMAndy/awesome-openclaw-skills-CN` | 社区（中文） |

> 数据源配置在 `config/sources.json`，可自由扩展。

## 🆚 为什么需要 Skill 安全审核

| 问题 | 没有审核 | 使用 SoSkill 审核 |
|---|---|---|
| 危险命令识别 | 靠人工逐条看，成本高且易漏 | 规则扫描 `curl|bash`、破坏性命令 |
| 越狱/覆盖指令 | 隐藏在长文本中不易发现 | 模式匹配并给出风险等级 |
| 凭据泄露风险 | 社区 Skill 质量参差不齐 | 凭据相关风险规则自动标注 |
| 上线前可信度 | 主观判断 | 结构化 JSON/Markdown 审计证据 |

## ⚡ 快速开始

```bash
# 克隆仓库
git clone https://github.com/AIPMAndy/soskill.git
cd soskill

# 一条命令（推荐）：抓取 + 统计 + 安全审核
python3 scripts/run_workflow.py --mode secure-refresh --out-dir data
```

需要更高 API 额度时：

```bash
export GITHUB_TOKEN=<your_token>
make refresh
```

## 🧩 作为 Codex Skill 一键安装

仓库内已内置可安装的 Skill 包：`skills/public/soskill`。

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo AIPMAndy/soskill \
  --path skills/public/soskill
```

安装后重启 Codex 即可识别新 Skill。

## 🛠️ 常用命令

```bash
make refresh          # 全量抓取
make refresh-fast     # 快速抓取（本地调试）
make stats            # 查看统计摘要
make organize         # 整理开源集合（离线）
make offline-local    # 自动拉取 + 离线整理
make audit            # Skill 风险审核（离线元数据）
make audit-deep       # Skill 深度审核（联网拉取 SKILL.md）
make workflow         # 一键安全流程（抓取+统计+审核）
make workflow-full    # 一键全流程（抓取+统计+审核+整理）
make workflow-offline # 一键离线流程（拉取集合+本地整理）
make workflow-offline-dry # 离线流程预演（不执行 clone/pull）
```

## 📦 输出文件

| 文件 | 说明 |
|------|------|
| `data/skills.json` | 完整聚合数据 |
| `data/skills.csv` | 便于筛选分析 |
| `docs/latest.md` | 最新抓取摘要 |
| `data/collections.json` | 结构化集合数据 |
| `data/skills.audit.json` | Skill 风险审核结构化结果 |
| `docs/skills-audit.md` | Skill 风险审核报告（Markdown） |

## 🛡️ Skill 安全审核模块

```bash
# 快速审核：不联网，仅基于 skills.json 的元数据
make audit

# 深度审核：联网拉取 raw SKILL.md 内容后再审计
make audit-deep
```

默认规则会检测：
- 危险命令（如 `rm -rf`、`git reset --hard`、`git clean -fdx`）
- 远程执行管道（如 `curl|bash`、`wget|sh`）
- 提示词越狱/覆盖安全策略语句
- 敏感凭据收集与外传迹象（token/secret/password）

风险等级说明：

| 等级 | 含义 | 建议动作 |
|---|---|---|
| `critical` | 高概率恶意或直接破坏性行为 | 立即阻断并人工复核 |
| `high` | 明显可疑信号 | 隔离并重点审核 |
| `medium` | 上下文相关风险 | 上线前复审 |
| `low` | 弱风险信号 | 持续观察 |
| `clean` | 未命中规则 | 仍需业务层复核 |

推荐上线前流程：

```bash
make refresh
make audit
# 发布前可追加深度审核
make audit-deep
```

## 🧭 一键工作流模式

```bash
# 抓取 + 统计
python3 scripts/run_workflow.py --mode refresh --out-dir data

# 抓取 + 统计 + 审核（推荐）
python3 scripts/run_workflow.py --mode secure-refresh --out-dir data

# 抓取 + 统计 + 审核 + 集合整理
python3 scripts/run_workflow.py --mode full --out-dir data

# 离线模式：拉取集合仓库 + 本地整理（需已有 skills 快照）
python3 scripts/run_workflow.py --mode offline --out-dir data --skills-input data/skills.json

# 仅预演离线流程（不执行 clone/pull）
python3 scripts/run_workflow.py --mode offline --out-dir data --skills-input data/skills.json --bootstrap-dry-run --dry-run
```

## 🔄 自动更新

工作流文件：`.github/workflows/refresh-skills.yml`

- **手动触发**：`workflow_dispatch`
- **外部触发**：`repository_dispatch`（`refresh-skills`）
- **定时触发**：每 6 小时自动抓取

## 📁 项目结构

```
soskill/
├── skills/public/soskill/    # 可直接安装的 Codex Skill 包
├── config/
│   ├── sources.json         # 数据源配置
│   └── collections.seed.json # 集合清单
├── scripts/
│   ├── fetch_skills.py       # 抓取脚本
│   ├── audit_skills.py       # 风险审核脚本
│   ├── run_workflow.py       # 一键工作流脚本
│   ├── organize_collections.py
│   └── bootstrap_collections.py
├── data/
│   ├── skills.json           # 聚合数据
│   ├── skills.csv
│   └── skills.audit.json     # 审核结果
├── docs/
│   ├── latest.md             # 最新摘要
│   ├── skills-audit.md       # 审核报告
│   └── ARCHITECTURE.md       # 架构说明
└── .github/workflows/
    └── refresh-skills.yml    # 自动化工作流
```

## 🤝 贡献

欢迎提交：
- 新数据源、解析器
- 质量审计和风险标签规则
- Bug 修复和功能改进

建议先提 Issue 再提 PR。

## 作者

**AI酋长Andy** | 前腾讯/百度 AI 产品专家

- 🚀 大模型独角兽 VP → 创业 CEO
- 🎯 AI 商业战略顾问

**微信:** AIPMAndy | **GitHub:** [@AIPMAndy](https://github.com/AIPMAndy)

---

## 📄 许可证 / License

[Apache-2.0](LICENSE)

---

<p align="center">
  ⭐ If this helps, please give it a star! / 觉得有用请点个 Star！
</p>
