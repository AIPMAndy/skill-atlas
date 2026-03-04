# SoSkill

SoSkill 是开源的 Skill 搜索与聚合项目：支持手动/定时触发抓取最新 Skill，并自动聚合为统一索引。

## 项目目标

- 聚合多生态 Skill（官方 + 社区）
- 统一结构（名称、描述、来源、链接、路径）
- 自动更新（GitHub Actions 定时 + 手动触发）
- 产出可二次利用的数据文件（JSON/CSV/Markdown）

## 当前数据源

- `openai/skills`（`.curated` + `.system`）
- `VoltAgent/awesome-openclaw-skills`（从 README 中提取 Skill 链接）
- `AIPMAndy/awesome-openclaw-skills-CN`（从 README 中提取 Skill 链接）

数据源配置在 `config/sources.json`，可自由扩展。

## 快速开始

```bash
cd projects/soskill
python3 scripts/fetch_skills.py
```

或使用封装脚本：

```bash
cd projects/soskill
bash scripts/refresh.sh
```

常用参数：

```bash
python3 scripts/fetch_skills.py \
  --config config/sources.json \
  --output data/skills.json \
  --csv data/skills.csv \
  --markdown docs/latest.md
```

如需更高 API 额度（推荐）：

```bash
export GITHUB_TOKEN=<your_token>
python3 scripts/fetch_skills.py
```

> 注：未配置 `GITHUB_TOKEN` 时，GitHub API 源（如 `openai/skills`）可能触发速率限制；脚本会自动降级并继续处理其他来源。

## 常用命令

```bash
# 全量抓取
make refresh

# 快速抓取（本地调试）
make refresh-fast

# 查看统计摘要
make stats

# 不依赖在线抓取，直接整理开源集合
make organize

# 结合本地已克隆仓库做离线扫描整理
make organize-local LOCAL_ROOT=/path/to/cloned/repos

# 自动 clone/pull 集合仓库（先预演）
make bootstrap-collections-dry

# 自动 clone/pull 后直接产出离线整理报告
make offline-local
```

## 抓取失败时的直接整理模式

如果你当前环境抓取不稳定（比如 API 限流、网络波动），可以直接使用已维护的开源集合清单进行整理：

- 清单配置：`config/collections.seed.json`
- 本地拉取脚本：`scripts/bootstrap_collections.py`
- 整理脚本：`scripts/organize_collections.py`
- 产出结果：`data/collections.json` + `docs/collections.md`
- 可选本地扫描：`--local-root`（扫描本地仓库里的 `SKILL.md`）

运行方式：

```bash
cd projects/soskill
make organize

# 如果你已 clone 多个开源集合仓库
make organize-local LOCAL_ROOT=/Users/andy/projects

# 先自动拉取/更新开源集合，再离线整理
make offline-local
```

默认 `make organize` 不访问网络，只会基于当前本地 `data/skills.json` 进行集合归类。
如果传入 `--local-root`，会额外扫描本地仓库目录中的 `SKILL.md`，把未接入索引的集合也先纳入整理报告。
`make offline-local` 会先执行 bootstrap（clone/pull），再执行 organize-local，形成闭环。

## 自动触发抓取

工作流文件：`.github/workflows/refresh-skills.yml`

- `workflow_dispatch`：手动触发
- `repository_dispatch`（`refresh-skills`）：外部触发
- `schedule`：每 6 小时自动抓取

抓取后会自动提交更新到仓库（仅当数据有变化时）。

### 外部触发示例（跨仓库/Webhook）

```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer <PAT_WITH_REPO_SCOPE>" \
  https://api.github.com/repos/<owner>/soskill/dispatches \
  -d '{"event_type":"refresh-skills"}'
```

## 输出文件

- `data/skills.json`：完整聚合数据
- `data/skills.csv`：便于筛选分析
- `docs/latest.md`：最新抓取摘要
- `data/collections.json`：开源集合清单的结构化整理结果
- `docs/collections.md`：开源集合整理报告
- `data/collections.bootstrap.json`：本地集合仓库 bootstrap 执行清单

架构说明见：`docs/ARCHITECTURE.md`

## 数据结构（skills.json）

核心字段：

- `generated_at`：生成时间（UTC）
- `total`：去重后 Skill 数量
- `sources[]`：每个来源抓取统计与错误信息
- `skills[]`：每条 Skill 的统一结构（`name`、`description`、`repo`、`path`、`html_url` 等）

## 开源协作

- 欢迎提交新数据源、解析器和评分逻辑
- 欢迎提交质量审计和风险标签规则
- 先提 Issue 再提 PR 会更高效

## 许可证

MIT
