<div align="center">

# 🔍 SoSkill

**Skill 搜索与聚合引擎 | Skill Search & Aggregation Engine**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/AIPMAndy/soskill?style=social)](https://github.com/AIPMAndy/soskill)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://python.org)

[English](#english) | [简体中文](#中文)

</div>

---

<a name="english"></a>

## 🎯 What is SoSkill?

SoSkill is an open-source Skill search and aggregation engine that:

- 🔄 **Auto-fetches** skills from multiple sources (official + community)
- 📊 **Unifies** structure (name, description, source, link, path)
- ⏰ **Auto-updates** via GitHub Actions (scheduled + manual trigger)
- 📁 **Outputs** reusable data files (JSON/CSV/Markdown)

## ✨ Current Data Sources

| Source | Type |
|--------|------|
| `openai/skills` | Official (`.curated` + `.system`) |
| `VoltAgent/awesome-openclaw-skills` | Community |
| `AIPMAndy/awesome-openclaw-skills-CN` | Community (Chinese) |

> Sources are configured in `config/sources.json` — easily extensible.

## ⚡ Quick Start

```bash
# Clone the repo
git clone https://github.com/AIPMAndy/soskill.git
cd soskill

# Run fetch
python3 scripts/fetch_skills.py

# Or use make
make refresh
```

For higher API rate limits:

```bash
export GITHUB_TOKEN=<your_token>
make refresh
```

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
- 📁 **输出文件**（JSON/CSV/Markdown）

## ✨ 当前数据源

| 来源 | 类型 |
|------|------|
| `openai/skills` | 官方（`.curated` + `.system`） |
| `VoltAgent/awesome-openclaw-skills` | 社区 |
| `AIPMAndy/awesome-openclaw-skills-CN` | 社区（中文） |

> 数据源配置在 `config/sources.json`，可自由扩展。

## ⚡ 快速开始

```bash
# 克隆仓库
git clone https://github.com/AIPMAndy/soskill.git
cd soskill

# 运行抓取
python3 scripts/fetch_skills.py

# 或使用 make
make refresh
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
```

## 📦 输出文件

| 文件 | 说明 |
|------|------|
| `data/skills.json` | 完整聚合数据 |
| `data/skills.csv` | 便于筛选分析 |
| `docs/latest.md` | 最新抓取摘要 |
| `data/collections.json` | 结构化集合数据 |

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
│   ├── organize_collections.py
│   └── bootstrap_collections.py
├── data/
│   ├── skills.json           # 聚合数据
│   └── skills.csv
├── docs/
│   ├── latest.md             # 最新摘要
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
