# DeerFlow 沙箱挂载目录总览

> 生成时间：2026-08-30（2026-09-09 更新）
> 配置来源：`config.yaml` → `sandbox.mounts`
> 挂载总数：**24 个**（全部可读写）

## 一、速查总表

| #  | 沙箱内路径                        | 宿主机路径                                                                   | 内容 / 用途           | 文件数 |
| -- | ---------------------------- | ----------------------------------------------------------------------- | ----------------- | --- |
| 1  | `/mnt/brave-sea`             | `~/Documents/software/knowledge/all/勇者之海`                               | 游戏《勇者之海》项目资料库     | 147 |
| 2  | `/mnt/girl-a-plan`           | `~/Documents/software/knowledge/all/少女A计划`                              | 游戏《少女A计划》项目资料库    | 31  |
| 3  | `/mnt/casual-games`          | `~/Documents/software/knowledge/all/休闲游戏事业部`                            | 休闲游戏事业部知识库        | 41  |
| 4  | `/mnt/android-lead`          | `~/Documents/software/knowledge/all/安卓主管`                               | 安卓主管岗位资料库         | 63  |
| 5  | `/mnt/casual-games-cn`       | `~/Documents/software/resume/youdaonote-pull/幕布备份/游禧科技/休闲游戏国内事业部`       | 国内事业部幕布备份（当前为空）   | 0   |
| 6  | `/mnt/casual-games-overseas` | `~/Documents/software/resume/youdaonote-pull/幕布备份/休闲游戏事业部海外业务`          | 海外业务幕布备份（当前为空）    | 0   |
| 7  | `/mnt/android-tech`          | `~/Documents/software/knowledge/all/安卓技术`                               | 安卓技术资料            | 35  |
| 8  | `/mnt/platform-ops`          | `~/Documents/software/knowledge/all/平台运营/原始文件`                          | 平台运营资料            | 90  |
| 9  | `/mnt/arc-docs`              | `~/Documents/software/aiagent/cossistant/docs/arc`                      | cossistant 项目架构文档 | 8   |
| 10 | `/mnt/arc-new-docs`          | `~/Documents/software/aiagent/cossistant/docs/arc-new`                  | cossistant 新版架构文档 | 9   |
| 11 | `/mnt/summary-res`           | `~/Documents/software/workspace/summary/output/res`                     | 总结输出资源目录（当前为空）    | 0   |
| 12 | `/mnt/data-analysis-arc`     | `~/Documents/software/aiagent/Data-Analysis-Agent/docs/arc`             | 数据分析 Agent 架构文档   | 7   |
| 13 | `/mnt/project-requirements`  | `~/Documents/software/zhaopin/项目/项目需求`                                  | 招聘项目需求（当前为空）      | 0   |
| 14 | `/mnt/ai-core-arguments`     | `~/Documents/software/workspace/summary/output/topic_summaries/AI/核心论点` | AI 主题核心论点汇总       | 31  |
| 15 | `/mnt/resume-experience`     | `~/Documents/software/autoup/简历整理`                                      | 工作经历整理（简历素材）      | 9   |
| 16 | `/mnt/ai-learn-docs`         | `~/Documents/ai_learn/docs`                                             | AI 学习文档库          | 161 |
| 17 | `/mnt/daily-summaries`       | `~/Documents/software/workspace/summary/output/daily/一句话总结`             | 每日一句话总结           | 29  |
| 18 | `/mnt/bettafish-reports`     | `~/Documents/software/aiengine/bettafish/reports`                       | 自媒体分析报告           | 12  |
| 19 | `/mnt/media-summaries`       | `~/Documents/software/workspace/summary/output/汇总_media`                | 自媒体资料汇总           | 11+ |
| 20 | `/mnt/hardware-core-arguments` | `~/Documents/software/workspace/summary/output/topic_summaries/硬件/核心论点` | 硬件主题核心论点汇总       | 39  |
| 21 | `/mnt/company-core-arguments` | `~/Documents/software/workspace/summary/output/topic_summaries/公司运作/核心论点` | 公司运作主题核心论点汇总     | 29  |
| 22 | `/mnt/server-core-arguments`  | `~/Documents/software/workspace/summary/output/topic_summaries/服务器/核心论点` | 服务器主题核心论点汇总       | 39  |
| 23 | `/mnt/storage-core-arguments` | `~/Documents/software/workspace/summary/output/topic_summaries/存储/核心论点` | 存储主题核心论点汇总        | 28  |
| 24 | `/mnt/planning-docs`         | `~/Documents/software/workspace/summary/output/规划文档汇总`                  | 国家各地区"十五五"规划文档     | 384 |

***

## 二、目录详细说明

### 1. `/mnt/brave-sea` — 游戏《勇者之海》资料库

游戏项目运营/产品资料，包含版本更新内容、7 日活动分析、用户信息（如未付款用户）、竞品内容相似度排查、产品参数表、IG 对接物料等。

典型文件：`7.10 版本内容更新.md`、`7日活动分析.md`、`Ahoy, Matey! Pirates' Fortress与勇者之海内容相似度排查.md`、`Cap.Jack 产品参数表.md`

### 2. `/mnt/girl-a-plan` — 游戏《少女A计划》资料库

游戏项目运营/测试资料，包含删档测试公告与反馈、版本更新方案、活动排行奖励补发、兑换码、商业点、商品配置清单等。

典型文件：`《少女A计划》删档测试公告.md`、`先行服验收反馈.md`、`双端版本更新方案.md`、`商业点.md`

### 3. `/mnt/casual-games` — 休闲游戏事业部知识库

事业部级知识库，包含多款产品档案（Family Farm Adventure、Stumble Guys、Survivor!.io、X-HERO 等）、上架流程、产研流程、业务理解、复盘模板、iOS 归因复盘等。

典型文件：`Family Farm Adventure.md`、`上架流程.md`、`产研流程.md`、`iOS归因问题复盘.md`

### 4. `/mnt/android-lead` — 安卓主管资料库

安卓管理岗资料，包含小组制度、编码规范、代码审查制度、事故/业务处理流程、公共库开发流程、会议纪要、工作交接计划等。

典型文件：`Android编码规范.md`、`代码审查制度0.md`、`事故处理流程.md`、`7.26会议.md`

### 5-6. `/mnt/casual-games-cn` / `/mnt/casual-games-overseas` — 幕布备份

国内事业部 / 海外业务的有道云笔记幕布备份目录，**当前为空**，待后续备份数据放入。

### 7. `/mnt/android-tech` — 安卓技术资料

安卓技术专题资料，包含 H5 微端出包流程/功能文档/瘦身方案、SDK 构建基础库方案、打包流程、17k 接入评估等。

典型文件：`H5微端出包流程文档.md`、`sdk构建基础库方案.md`、`17k接入评估.md`、`h5打包流程.md`

### 8. `/mnt/platform-ops` — 平台运营资料

平台运营原始文件，包含 KOL 后台投后数据、KOL 回收数据模型、星图账号授权、OCPC 配置与验收、口令红包申请、直播/短视频推广 PRD 等。

典型文件：`KOL回收数据模型.md`、`OCPC配置.md`、`【PRD_2025.12.16】获取直播及短视频推广游戏需求.md`

### 9. `/mnt/arc-docs` — cossistant 架构文档

cossistant（AI 客服助手）项目架构文档：AI 对话架构、计费架构、知识架构、实时架构、访客追踪架构、产品需求设计文档。

典型文件：`AI_CONVERSATION_ARCHITECTURE.md`、`BILLING_ARCHITECTURE.md`、`产品需求设计文档.md`

### 10. `/mnt/arc-new-docs` — cossistant 新版架构文档

cossistant 新版架构（编号体系 00-10）：系统总览、实时消息、AI 对话、知识库、访客追踪、计费、数据模型、技术栈。

典型文件：`01-SYSTEM-OVERVIEW.md`、`04-AI-CONVERSATION.md`、`05-KNOWLEDGE-BASE.md`、`10-TECH-STACK.md`

### 11. `/mnt/summary-res` — 总结输出资源

总结输出资源目录，**当前为空**，供后续存放生成的总结资源文件。

### 12. `/mnt/data-analysis-arc` — 数据分析 Agent 架构文档

Data-Analysis-Agent 项目架构文档：Agent 架构、分析架构、API 架构、数据层架构、知识架构、输出架构。

典型文件：`AGENT_ARCHITECTURE.md`、`ANALYSIS_ARCHITECTURE.md`、`DATA_LAYER_ARCHITECTURE.md`

### 13. `/mnt/project-requirements` — 招聘项目需求

招聘项目需求目录，**当前为空**（仅含 `.DS_Store`），待放入项目需求文档。

### 14. `/mnt/ai-core-arguments` — AI 核心论点汇总

按日期汇总的 AI 主题核心论点文档，用于跟踪 AI 行业讨论的核心观点演进。

典型文件：`AI_核心论点汇总_20260602.md`、`AI_核心论点汇总_20260714.md` …（按日期递增）

### 15. `/mnt/resume-experience` — 简历经历整理

按工作阶段/项目整理的简历素材（9 份），覆盖历段经历。

典型文件：`休闲游戏国内事业部工作 - 202109 - 202211.md`、`勇者之海 - 202403-202511.md`、`安卓主管工作经历 - 202102-202109.md`、`平台运营工作 - 2026.01-2026.03.md`

### 16. `/mnt/ai-learn-docs` — AI 学习文档库

个人 AI 学习资料库（161 项）：agent-express、agentscope、ai-agent、ai-memory、agentic-design-patterns、ai-engineering-from-scratch、ai-infra-guard 等主题。

### 17. `/mnt/daily-summaries` — 每日一句话总结

按日期汇总的各行业文档一句话总结（29 份），格式 `summary_list_YYYYMMDD.md`。

### 18. `/mnt/bettafish-reports` — 自媒体分析报告

自媒体（bettafish 项目）深度分析报告（12 项）：抖音/小红书/快手平台运动健身内容热度与舆情分析、跑步人群关注点分析等，含 `deep_search_report_*.md` 报告与 `state_*.json` 数据。

典型文件：`deep_search_report_抖音小红书快手平台上跑步人群的关注点与舆情分析_20260830_130113.md`、`跑步人群关注点综合分析_20260830.md`

### 19. `/mnt/media-summaries` — 自媒体资料汇总

自媒体行业资料汇总目录，按时间批次组织（如 `2026090616`、`2026090713`、`2026090715`、`2026090717`），每个批次含该时段的媒体内容分析/总结素材，供自媒体运营分析使用。

典型文件：各批次目录内的时间戳内容文件（`.DS_Store` 除外）

### 20. `/mnt/hardware-core-arguments` — 硬件主题核心论点汇总

按日期汇总的硬件主题核心论点文档（39 份），用于跟踪硬件行业讨论的核心观点演进，与 `/mnt/ai-core-arguments`（AI 主题）同系列。

### 21. `/mnt/company-core-arguments` — 公司运作主题核心论点汇总

按日期汇总的公司运作主题核心论点文档（29 份），涵盖公司治理、运营管理等讨论的核心观点。

### 22. `/mnt/server-core-arguments` — 服务器主题核心论点汇总

按日期汇总的服务器主题核心论点文档（39 份），涵盖服务器行业相关讨论的核心观点。

### 23. `/mnt/storage-core-arguments` — 存储主题核心论点汇总

按日期汇总的存储主题核心论点文档（28 份），涵盖存储行业相关讨论的核心观点。

### 24. `/mnt/planning-docs` — 国家各地区"十五五"规划文档

国家及各地"十五五"规划文档汇总（192 份原文 + 192 份摘要），按 `原文/`（`_hybrid.md` / `_doc.md` 原始规划文档）与 `摘要/`（`_summary.md` 摘要）两个子目录组织，覆盖国务院/各部委及各省市（如福建、塔城、北京、海南等）的十五五规划。

典型文件：`原文/2026国务院和各部委十五五能源相关规划汇编-339页_hybrid.md`、`摘要/“十五五”数字福建规划_summary.md`

***

## 三、使用说明

* **沙箱内访问**：agent 在沙箱中通过 `/mnt/xxx` 路径读取/写入这些目录，与宿主机路径实时同步。

* **修改挂载**：编辑 `config.yaml` → `sandbox.mounts`（新增/删除条目），然后重启服务生效。

* **空目录提示**：序号 5、6、11、13 当前为空，属正常状态，数据放入后即可被沙箱读取。

* **服务入口**：<http://localhost:2026（launchd> 服务 `com.deerflow.dev` 托管）。

