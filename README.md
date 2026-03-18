[English](README_EN.md) | **简体中文**

<div align="center">

# 🔍 SoSkill

**AI Agent 技能市场的"安全搜索引擎"**

> 自动聚合 · 风险审核 · 一键可用
>
> 从源头解决"这个 Skill 能不能装"的问题

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/AIPMAndy/soskill?style=social)](https://github.com/AIPMAndy/soskill)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://python.org)
[![Skill Audit](https://img.shields.io/badge/Security%20Audit-Enabled-success)](docs/skills-audit.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

</div>

---

## 💡 为什么需要 SoSkill

AI Agent 生态里 Skill 越来越多，但你敢随便装吗？

- 社区 Skill **没有统一的安全审核**
- 有的 Skill 藏着 `curl | bash`、`rm -rf`、凭据窃取
- 越狱 / 提示词覆盖攻击隐藏在长文本里，人工很难发现
- 散落在多个 repo，**找都找不全**

**SoSkill = 聚合 + 审核 + 输出**，一条命令搞定。

---

## ⚡ 30 秒快速开始

```bash
git clone https://github.com/AIPMAndy/soskill.git
cd soskill

# 一条命令：抓取 + 统计 + 安全审核
python3 scripts/run_workflow.py --mode secure-refresh --out-dir data
```

完成后查看：
- `data/skills.json` — 全量聚合数据
- `docs/skills-audit.md` — 安全审核报告
- `docs/latest.md` — 最新抓取摘要

---

## 🛡️ 安全审核（核心亮点）

这是 SoSkill 区别于"普通 awesome list"的关键能力。

| 检测项 | 示例 |
|--------|------|
| 🔴 危险命令 | `rm -rf /`、`git reset --hard`、`git clean -fdx` |
| 🔴 远程执行管道 | `curl \| bash`、`wget \| sh` |
| 🟡 越狱 / 提示词覆盖 | 隐藏的 system prompt 覆盖指令 |
| 🟡 凭据泄露 | token / secret / password 收集迹象 |

```bash
make audit          # 快速审核（离线，基于元数据）
make audit-deep     # 深度审核（联网拉取 SKILL.md 内容）
```

**风险等级：**

| 等级 | 建议 |
|------|------|
| `critical` | ⛔ 立即阻断，人工复核 |
| `high` | 🔒 隔离并重点审核 |
| `medium` | ⚠️ 上线前复审 |
| `low` | 👀 持续观察 |
| `clean` | ✅ 未命中规则（仍建议业务层复核） |

---

## 🆚 跟手动找 Skill 有什么不同？

| 维度 | 手动查找 | SoSkill |
|------|---------|---------|
| **来源覆盖** | 一个个翻 repo | 多源自动聚合 |
| **安全判断** | 靠肉眼看代码 | 规则扫描 + 分级报告 |
| **数据格式** | 各 repo 各不同 | 统一 JSON / CSV / Markdown |
| **持续更新** | 记得才去看 | GitHub Actions 每 6 小时刷新 |
| **上线决策** | 主观判断 | 结构化审计证据 |

---

## 📊 当前数据源（v2.0）

| 来源 | 类型 | 状态 |
|------|------|------|
| `openai/skills` | 官方（`.curated` + `.system`） | ✅ 活跃 |
| `anthropics/skills` | Anthropic 官方 | ✅ 新增 |
| `VoltAgent/awesome-openclaw-skills` | 社区 | ✅ 活跃 |
| `AIPMAndy/awesome-openclaw-skills-CN` | 社区（中文） | ✅ 活跃 |
| `AIPMAndy/repos` | AIPMAndy 的 18 个项目 | ✅ 新增 |
| GitHub Topics (openclaw/codex) | 自动发现 | ✅ 新增 |
| PyPI/NPM Registry | 包管理器 | ⏳ 待启用 |

**总计**: 6+ 数据源，自动聚合，增量更新

---

## 🚀 v2.0 新特性

### 增量更新（ETag 缓存）
```bash
# 只抓取变更的数据，节省 API 配额
python3 scripts/fetcher_v2.py --config config/sources_v2.json
```

### 质量评分系统
每个 Skill 自动计算质量分：
- ⭐ Stars × 权重
- 🍴 Forks × 权重
- 📅 更新新鲜度
- 🧪 是否有测试
- 📖 是否有文档
- 🛡️ 安全审核结果

### GitHub 项目推荐
```bash
# 基于 AIPMAndy 的 GitHub 项目智能推荐
python3 scripts/recommender.py
```

---

## 📈 项目统计

| 指标 | 数值 |
|------|------|
| 数据源 | 6+ |
| 代码行数 | 4800+ |
| 测试覆盖 | 2 个测试文件 |
| 自动更新 | 每 6 小时 |
| 安全规则 | 10+ 条 |

---

## 🗺️ Roadmap

- [x] 多源聚合 + 统一结构
- [x] 安全审核引擎（规则扫描 + 分级）
- [x] GitHub Actions 自动刷新
- [x] Codex Skill 安装包
- [x] 增量更新 + 缓存
- [x] 质量评分系统
- [x] GitHub 项目推荐
- [ ] Web UI 搜索界面
- [ ] AI 驱动的语义搜索
- [ ] Skill 相似度去重

---

## 📊 历史数据源

> 配置在 `config/sources.json`，可自由扩展。

---

## 📦 输出文件

| 文件 | 说明 |
|------|------|
| `data/skills.json` | 完整聚合数据 |
| `data/skills.csv` | 便于筛选分析 |
| `data/skills.audit.json` | 风险审核结构化结果 |
| `data/collections.json` | 结构化集合数据 |
| `docs/latest.md` | 最新抓取摘要 |
| `docs/skills-audit.md` | 安全审核报告 |

---

## 🧩 作为 Codex Skill 安装

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo AIPMAndy/soskill \
  --path skills/public/soskill
```

安装后重启 Codex 即可使用。

---

<details>
<summary>🛠 <b>完整命令参考</b>（点击展开）</summary>

### Makefile 快捷方式

```bash
make refresh          # 全量抓取
make audit            # 快速风险审核
make audit-deep       # 深度风险审核
make workflow         # 一键：抓取 + 统计 + 审核
make workflow-full    # 一键：抓取 + 统计 + 审核 + 整理
make test             # 运行测试
make check-bundle-sync # 检查脚本与技能包是否同步
```

### 工作流模式

```bash
python3 scripts/run_workflow.py --mode refresh --out-dir data          # 抓取 + 统计
python3 scripts/run_workflow.py --mode secure-refresh --out-dir data   # 抓取 + 统计 + 审核
python3 scripts/run_workflow.py --mode full --out-dir data             # 全流程
python3 scripts/run_workflow.py --mode offline --out-dir data --skills-input data/skills.json  # 离线
```

### 高级选项

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

</details>

---

## 📁 项目结构

```
soskill/
├── skills/public/soskill/    # 可安装的 Codex Skill 包
├── config/                   # 数据源 & 集合配置
├── scripts/                  # 核心脚本（抓取/审核/工作流）
├── tests/                    # 自动化测试
├── data/                     # 输出数据（JSON/CSV）
├── docs/                     # 输出文档（审核报告/摘要）
└── .github/workflows/        # CI + 定时刷新
```

---

## 🗺️ Roadmap

- [x] 多源聚合 + 统一结构
- [x] 安全审核引擎（规则扫描 + 分级）
- [x] GitHub Actions 自动刷新
- [x] Codex Skill 安装包
- [ ] 更多数据源接入
- [ ] Web UI 搜索界面
- [ ] AI 驱动的语义搜索
- [ ] Skill 相似度去重

---

## 🌟 谁在用

> 如果你在用 SoSkill，欢迎加 ⭐ 并告诉我！

- [AIPMAndy](https://github.com/AIPMAndy) - 作者自用
- [DNA Memory](https://github.com/AIPMAndy/dna-memory) - 集成 Skill 安全审核
- [KnowMe](https://github.com/AIPMAndy/KnowMe) - 推荐 Skill 给用户

---

## 📈 Star 历史

[![Star History Chart](https://api.star-history.com/svg?repos=AIPMAndy/soskill&type=Date)](https://star-history.com/#AIPMAndy/soskill&Date)

---

## 🤝 贡献

欢迎提交新数据源、审核规则、Bug 修复。建议先提 Issue 再提 PR。

## 👨‍💻 作者

**AI酋长Andy** — 前腾讯/百度 AI 产品专家 · AI 商业战略顾问

微信 `AIPMAndy` · GitHub [@AIPMAndy](https://github.com/AIPMAndy)

## 📄 License

[Apache-2.0](LICENSE)

---

<div align="center">

**觉得有用？给个 ⭐ Star，让更多人发现安全的 Skill**

</div>
