# deerflowcli 使用备忘

DeerFlow 的命令行任务执行工具，可在任意项目目录直接调用（全局命令），无需 Docker，本机 Gateway 驱动。

## 快速开始

```bash
# 新建会话执行任务
deerflowcli "分析 /mnt/planning-docs 下的规划文档并输出总结"

# 联网搜索 + 抓取核实
deerflowcli "联网核实：搜索后用 web_fetch 打开链接核实内容"

# 复用已中断的会话继续
deerflowcli --thread-id <会话ID>

# 指定下载目录
deerflowcli "任务" --output-dir ~/Documents/reports
```

## 提示词写法（跨项目关键）

与 Web 端一致，无需区分 CLI / Web 写法，几点约定：

- **引用资料用沙箱挂载路径** `/mnt/xxx`（不是本地路径）。可用挂载：`/mnt/ai-learn-docs`、`/mnt/planning-docs`、`/mnt/user-data/outputs` 等。
- **联网核实链接**：给 agent 完整 URL，让它用 `web_fetch` 打开核实。
- **交付要求**：让 agent 把结果写到 `/mnt/user-data/outputs/` 并调用 `present_files` 交付，CLI 才会自动下载。
- 任务会被自动附加 3 组约束（见下），无需自己写。

## 自动附加的约束

每次提交任务时 CLI 自动附带：

1. **[质量要求]**：禁止降级到 flash/lite 等快速模式；结论必须基于真实检索来源；信息不足要说明。
2. **[大文件写入协议]**：长文档按 `write_file(append=True)` 分批追加写入，避免单次超大输出被截断；被 blocked 时先 `read_file` 再写。
3. **[固定工作习惯与交付偏好]**：联网搜索类任务必须输出《联网搜索记录.md》（任务概述/搜索过程明细/结论验证/剔除说明 + 三级标注：✅已核实 / 🔶区间估算 / ⚠️经验判断），并随主结果一起交付。格式依据：`/mnt/ai-learn-docs/固定工作规则/联网搜索透明化_固定工作规则.md`。

## 自动化机制

- **中断自动继续**：任务被中断时自动发「继续」恢复，直到拿到结果；超上限转人工询问（`--max-continue`，默认 3）。
- **cap 类强制收尾自动继续**：`loop_capped` 等 guardrail 收尾默认自动继续（`--auto-resume-capped` 默认开启，`--capped-resume-limit` 默认 3，可用 `--no-auto-resume-capped` 关闭）。
- **run 异常/空转自动恢复**：run 执行出错或恢复空转（未实际执行）时，自动重新提交任务继续，超限提示人工用 `--thread-id` 手动继续。
- **实时进度输出**：思考/工具调用/心跳提示逐行实时刷新，任务中途即可判断是否正常执行：
  - 持续出现「思考/⚙ 工具调用」→ 正常推进
  - 每 30s 出现「⏳ 仍在执行中…（任务未卡死）」→ 后台运行中、连接存活
  - 长时间完全无输出 → 可按 Ctrl+C，会话保留可用 `--thread-id` 恢复
- **服务自动拉起**：Gateway 未启动时自动拉起（launchd `com.deerflow.dev` → serve.sh --daemon），可用 `--no-auto-start` 关闭。

## 参数速查

| 参数 | 说明 | 默认 |
|---|---|---|
| `task` | 任务描述（双引号包裹多行文本） | — |
| `--gateway` | Gateway 地址 | `http://127.0.0.1:8001` |
| `--output-dir` | 产出文件下载目录 | `~/Downloads/deerflow` |
| `--max-continue` | 中断最大自动继续次数 | 3 |
| `--continue-text` | 自动继续文字 | 「继续」 |
| `--thread-id` | 复用已有会话 | 缺省新建 |
| `--assistant-id` | 指定 assistant | 默认 |
| `--timeout` | 单次任务最长等待秒数（socket 静默超时，心跳保活可更久） | 3600 |
| `--no-stream` | 不打印流式进度 | 关 |
| `--auto-resume-capped` | cap 类自动继续 | 开（`--no-...` 关闭） |
| `--capped-resume-limit` | cap 自动继续上限 | 3 |
| `--no-auto-start` | 不自动拉起 Gateway | 关 |
| `--wait-timeout` | 自动启动后等待就绪秒数 | 180 |
| `--verbose` | 调试信息 | 关 |

## 输出与下载

- 产出文件自动下载到 `~/Downloads/deerflow/<会话ID>/`。
- 只下载 `present_files` 交付的文件及 `/mnt/user-data/outputs/` 下产物，不含工作区中间文件。

## 联网配置

- `web_search` / `web_fetch` 均走 **Tavily**（`.env` 的 `TAVILY_API_KEY`），无需 Jina。
- 若搜索/抓取异常，先确认 Gateway 进程已重启加载了新 `.env`（`launchctl kickstart -k com.deerflow.dev`）。

## 排错

| 现象 | 处理 |
|---|---|
| 任务长时间无输出 | 属正常静默（agent 在长生成），30s 后会有心跳提示；超 1 分钟完全无输出可按 Ctrl+C |
| 输出「run 异常终止」「空转」 | CLI 会自动恢复；若多次失败会提示用 `--thread-id` 手动继续 |
| 想中途停止 | Ctrl+C，会话保留，之后 `deerflowcli --thread-id <会话ID> "继续"` |
| 输出目录不对 | `--output-dir` 临时指定，或改 CLI 的 `DEFAULT_OUTPUT_DIR` |
