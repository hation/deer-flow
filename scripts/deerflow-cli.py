#!/usr/bin/env python3
"""DeerFlow CLI —— 通过 Gateway REST API 在本机执行任务。

功能：
1. 创建新会话（thread）并输入任务，实时打印执行进度（SSE 流式）
2. 任务成功后自动把产出文件下载到本地目录，并打印文件清单
3. 任务被中断（需要澄清 / 断线取消）时，自动发送"继续"恢复，
   循环直到拿到任务结果；连续自动继续超过上限则暂停询问用户
4. Gateway 未启动时自动拉起服务（launchd com.deerflow.dev 优先，
   回退 serve.sh --daemon），等待就绪后再执行任务

用法示例：
    python3 scripts/deerflow-cli.py "分析 /mnt/bettafish-reports 下的报告并输出总结"
    python3 scripts/deerflow-cli.py "任务..." --output-dir ~/my-outputs --max-continue 3

仅依赖 Python 标准库（urllib），无需安装额外依赖。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_GATEWAY = "http://127.0.0.1:8001"
DEFAULT_OUTPUT_DIR = str(Path.home() / "Downloads" / "deerflow")
DEFAULT_MAX_CONTINUE = 3
DEFAULT_CONTINUE_TEXT = "继续"
DEFAULT_TIMEOUT = 3600  # 任务最长等待（秒），与沙箱 bash 超时对齐

# 每次提交任务时自动附加的质量约束：坚持"详细准确"原则，
# 防止模型为了速度自行降级到 flash/lite 等快速或精简模式。
QUALITY_INSTRUCTION = (
    "\n\n[质量要求]\n"
    "本任务要求结果详细、全面、准确，请严格遵守：\n"
    "1. 使用完整/深度模式进行研究，严禁为了速度降级到 flash、lite 等快速或精简模式；\n"
    "2. 若子代理或研究过程因回合预算/资源上限被截断，应继续或重试原任务，不得改用较弱的模型或简化研究范围；\n"
    "3. 所有结论必须基于真实检索到的来源（web_search / web_fetch），并标注出处；\n"
    "4. 信息不足时明确说明不确定性，不要臆造。"
)

# 大文件写入协议：参考 Web 端 write_file 的 append=True 追加设计
# （后端 SIZE POLICY issue #3189 + read-before-write 门控 issue #3857），
# 长文档必须分批追加写入，避免单次超大写入触发流式 chunk-gap 截断。
WRITE_PROTOCOL = (
    "\n\n[大文件写入协议]\n"
    "预计产出超过约 3KB 的文档时，必须按下述方式分批追加写入，严禁一次性写入超长全文：\n"
    "1. 动笔前先规划好章节结构；\n"
    "2. 首次使用 write_file(append=False) 创建文件（含标题与第一个章节）；\n"
    "3. 后续每批使用 write_file(append=True) 追加 1-2 个章节，每批 content 控制在 1500 字以内；\n"
    "4. 若 write_file 被 blocked（提示文件已存在且未读取当前版本），先 read_file 该文件末尾"
    "（如最后 20-30 行）确认当前内容，再重试追加；\n"
    "5. 全部写完后 read_file 核对文件完整性（章节齐全、无截断、结尾完整），再调用 present_files 交付。"
)

# 每次提交任务时自动附加的固定工作习惯与交付偏好
# （对应 Web 端全局 Correction）：联网搜索类任务必须输出
# 《联网搜索记录.md》并随主结果一起交付，便于自动下载。
WORK_HABITS_INSTRUCTION = (
    "\n\n[固定工作习惯与交付偏好]\n"
    "1. 每次联网搜索任务完成后，必须默认输出《联网搜索记录.md》，"
    "内容含任务概述/搜索过程明细/结论验证/剔除说明，随主结果一起交付；\n"
    "2. 执行前先读取规则文件 /mnt/ai-learn-docs/固定工作规则/联网搜索透明化_固定工作规则.md，"
    "格式与三级数据标注严格按该文件及其关联模板执行；\n"
    "3. 数据可信度沿用三级标注体系：已核实 / 区间估算 / 经验判断；\n"
    "4. 在主文档末尾附简短搜索摘要；\n"
    "5. 将《联网搜索记录.md》写入 /mnt/user-data/outputs/ 并调用 present_files 交付，"
    "确保它能被自动下载到本地。"
)

# run 被 guardrail 强制收尾（终态 cap）时的 stop_reason → 中文说明。
# 这类停止后 run 以"完成+标记"终结（非 interrupted），agent 通常会在
# 回复里引导"回复「继续」"以继续剩余工作。
STOP_REASON_LABELS = {
    "loop_capped": "循环检测（重复调用同一工具被识别）",
    "token_capped": "token 预算上限",
    "safety_capped": "安全终止",
    "subagent_limit_capped": "子代理数量上限",
    "model_length_capped": "模型输出长度上限",
}


class CliError(Exception):
    pass


def api(gateway: str, method: str, path: str, body: dict | None = None,
        timeout: int = 60, raw: bool = False):
    """调用 Gateway REST API。返回解析后的 JSON；raw=True 时返回 (status, bytes)。"""
    url = f"{gateway.rstrip('/')}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            if raw:
                return resp.status, content
            if not content:
                return {}
            return json.loads(content)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        raise CliError(f"API {method} {path} 失败: HTTP {exc.code} - {detail}") from exc
    except urllib.error.URLError as exc:
        raise CliError(
            f"无法连接 Gateway ({gateway}): {exc.reason}\n"
            "请确认 DeerFlow 服务已启动（http://localhost:2026 可访问）"
        ) from exc


def create_thread(gateway: str, assistant_id: str | None = None) -> str:
    body: dict = {}
    if assistant_id:
        body["assistant_id"] = assistant_id
    resp = api(gateway, "POST", "/api/threads", body)
    thread_id = resp.get("thread_id")
    if not thread_id:
        raise CliError(f"创建会话失败，响应: {resp}")
    return thread_id


def thread_status(gateway: str, thread_id: str) -> str:
    resp = api(gateway, "GET", f"/api/threads/{thread_id}")
    return resp.get("status", "unknown")


def run_stream(gateway: str, thread_id: str, *, body: dict, timeout: int,
               progress: bool) -> tuple[str, dict | None]:
    """发起一次 run 并通过 SSE 流式读取。返回 (run_id, 最后一个 values 状态)。

    返回前已按 event: values 逐帧解析；SSE 结束表示本次 run 已结束
    （completed / interrupted / error 由线程状态决定）。

    Gateway 的 SSE 在无数据时定期发送 ": heartbeat" 注释行保活；
    据此在长时间无新进度时打印"仍在执行中"提示，避免被误判为卡死。
    """
    path = f"/api/threads/{thread_id}/runs/stream"
    url = f"{gateway.rstrip('/')}{path}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    run_id = None
    last_values: dict | None = None
    seen_msg_ids: set[str] = set()
    seen_deleg: set[str] = set()
    last_activity_ts = time.time()   # 最近一次收到 values 的时间
    last_silent_hint_ts = 0.0        # 最近一次打印静默提示的时间
    silent_hint_interval = 30        # 静默超过 30s 开始提示
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            event = None
            for raw_line in resp:
                line = raw_line.decode(errors="replace").rstrip("\r\n")
                if line.startswith(":"):
                    # SSE 心跳注释行：连接仍存活，只是暂无新进度
                    if progress:
                        now = time.time()
                        idle = now - last_activity_ts
                        if idle > silent_hint_interval and now - last_silent_hint_ts >= silent_hint_interval:
                            m, s = divmod(int(idle), 60)
                            print(f"  · ⏳ 仍在执行中…（已 {m}分{s}秒无新进度，任务未卡死）")
                            last_silent_hint_ts = now
                    continue
                if not line:
                    continue
                if line.startswith("event:"):
                    event = line[len("event:"):].strip()
                    continue
                if line.startswith("data:"):
                    payload = line[len("data:"):].strip()
                    if not payload:
                        continue
                    try:
                        data = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    if event == "metadata":
                        run_id = data.get("run_id") or run_id
                    elif event == "values":
                        last_values = data
                        last_activity_ts = time.time()
                        last_silent_hint_ts = time.time()
                        if progress:
                            print_progress(data, seen_msg_ids, seen_deleg)
                    elif event == "end":
                        # Gateway 显式发送的 run 结束信号
                        break
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        raise CliError(f"发起 run 失败: HTTP {exc.code} - {detail}") from exc
    except urllib.error.URLError as exc:
        # on_disconnect=continue 时 Gateway 会继续执行任务；
        # 连接断开 ≠ 任务失败，交由主循环查询线程状态决定后续动作。
        print(f"  · ⚠ 流式连接中断（{exc.reason}），任务可能仍在后台执行，继续查询状态…")
        return run_id, last_values
    return run_id, last_values


def print_progress(values: dict, seen: set[str], seen_deleg: set[str] | None = None) -> None:
    """从 values 状态的 messages 中提取可读进度行（去重）。

    seen_deleg 用于对线程 state 里的子任务委托（delegations）按 (id, 状态)
    去重，状态变化时打印子代理完成情况。
    """
    messages = values.get("messages") or []
    for msg in messages:
        msg_id = msg.get("id")
        if not msg_id or msg_id in seen:
            continue
        mtype = msg.get("type", "")
        kwargs = msg.get("additional_kwargs") or {}
        if kwargs.get("hide_from_ui"):
            seen.add(msg_id)
            continue
        content = msg.get("content") or ""
        if mtype == "human":
            # 普通用户消息不重复打印；带澄清请求的另行处理
            if kwargs.get("human_input_request") or _find_human_input(msg):
                seen.add(msg_id)
                continue
            if not kwargs.get("run_id"):
                seen.add(msg_id)
                continue
            seen.add(msg_id)
        elif mtype == "ai":
            seen.add(msg_id)
            reasoning = kwargs.get("reasoning_content")
            if reasoning:
                print(f"  · 思考: {_trim(reasoning, 200)}")
            if content:
                print(f"  · {_trim(str(content), 600)}")
        elif mtype == "tool":
            seen.add(msg_id)
            name = msg.get("name") or "tool"
            status = "成功" if str(msg.get("status", "")).lower() in ("success", "ok", "completed") else "执行"
            print(f"  ⚙ [{name}] {status}" + (f": {_trim(str(content), 120)}" if content else ""))
        elif mtype == "system":
            seen.add(msg_id)

    # ── 子任务（delegations）状态 ─────────────────────────────────
    # 每个通过 task 工具委托的子代理占一条：id / subagent_type / status /
    # result_brief。按 (id, status) 去重，状态变化时打印。
    deleg_icons = {
        "completed": "✅",
        "failed": "❌",
        "cancelled": "⏹",
        "timed_out": "⏱",
        "polling_timed_out": "⏱",
    }
    for d in values.get("delegations") or []:
        did = d.get("id")
        if not did:
            continue
        st = str(d.get("status") or "in_progress")
        key = f"{did}:{st}"
        if seen_deleg is not None:
            if key in seen_deleg:
                continue
            seen_deleg.add(key)
        dtype = str(d.get("subagent_type") or "subagent")
        icon = deleg_icons.get(st, "🧩")
        line = f"  {icon} [子任务] {dtype} → {st}"
        brief = str(d.get("result_brief") or "").strip()
        if brief and st in ("completed", "failed"):
            line += f": {_trim(brief, 120)}"
        print(line)


def _find_human_input(msg: dict) -> dict | None:
    """在消息的 artifact / additional_kwargs 中查找 human_input_request 载荷。"""
    artifact = msg.get("artifact")
    if isinstance(artifact, dict):
        hi = artifact.get("human_input") or artifact.get("human_input_request")
        if isinstance(hi, dict) and hi.get("kind") == "human_input_request":
            return hi
    kwargs = msg.get("additional_kwargs") or {}
    hi = kwargs.get("human_input_request")
    if isinstance(hi, dict) and hi.get("kind") == "human_input_request":
        return hi
    return None


def _normalize_message(m):
    """messages 接口返回的元素可能是包装结构：真正的消息在 content 字段的 dict 里。"""
    if isinstance(m, dict) and not m.get("type") and isinstance(m.get("content"), dict):
        return m["content"]
    return m


def extract_clarification_question(gateway: str, thread_id: str) -> str | None:
    """线程被中断后，从消息中提取 agent 的澄清提问文本。"""
    try:
        resp = api(gateway, "GET", f"/api/threads/{thread_id}/messages")
    except CliError:
        return None
    messages = resp.get("messages", resp) if isinstance(resp, dict) else resp
    if not isinstance(messages, list):
        return None
    for raw in reversed(messages):
        msg = _normalize_message(raw)
        hi = _find_human_input(msg)
        if hi:
            question = hi.get("question") or hi.get("prompt") or msg.get("content")
            return str(question) if question else None
    return None


def latest_ai_reply(gateway: str, thread_id: str) -> str | None:
    """取线程最后一条可见 AI 回复内容。"""
    try:
        resp = api(gateway, "GET", f"/api/threads/{thread_id}/messages")
    except CliError:
        return None
    messages = resp.get("messages", resp) if isinstance(resp, dict) else resp
    if not isinstance(messages, list):
        return None
    for raw in reversed(messages):
        msg = _normalize_message(raw)
        if msg.get("type") == "ai" and msg.get("content"):
            kwargs = msg.get("additional_kwargs") or {}
            if not kwargs.get("hide_from_ui"):
                return str(msg["content"])
    return None


def pending_clarification_question(gateway: str, thread_id: str) -> str | None:
    """判断线程是否处于"等待用户澄清回复"状态（线程状态为 idle 但最后一条
    消息是未回复的 ask_clarification 请求）。返回澄清问题文本，或 None。

    ask_clarification 由 ClarificationMiddleware 拦截中断，但线程状态是 idle
    （非 interrupted），澄清请求只体现在 messages 的 artifact.human_input 里，
    因此 idle 分支必须额外检查，否则会被误判为"任务完成"。
    """
    try:
        resp = api(gateway, "GET", f"/api/threads/{thread_id}/messages")
    except CliError:
        return None
    messages = resp.get("messages", resp) if isinstance(resp, dict) else resp
    if not isinstance(messages, list) or not messages:
        return None
    last = _normalize_message(messages[-1])
    hi = _find_human_input(last)
    if hi:
        question = hi.get("question") or hi.get("prompt") or last.get("content")
        if question:
            return str(question)
    return None


def get_run_status(gateway: str, thread_id: str, run_id: str | None) -> tuple[str, str | None, int, int]:
    """取最近一次 run 的状态、stop_reason、模型调用数与消息数。

    runs 接口按最新优先排列；优先匹配 run_id，找不到则取最新一条。
    返回 (status, stop_reason, llm_call_count, message_count)。
    注意：run 以 error 终止后线程状态也会回到 idle，仅靠 thread_status
    无法区分"成功完成"与"执行出错"，必须查 run 自身的 status。
    """
    try:
        runs = api(gateway, "GET", f"/api/threads/{thread_id}/runs")
    except CliError:
        return "unknown", None, 0, 0
    if not isinstance(runs, list) or not runs:
        return "unknown", None, 0, 0
    target: dict | None = None
    if run_id:
        for r in runs:
            if r.get("run_id") == run_id:
                target = r
                break
    if target is None:
        target = runs[0]
    if not isinstance(target, dict):
        return "unknown", None, 0, 0
    return (target.get("status") or "unknown",
            target.get("stop_reason"),
            target.get("llm_call_count") or 0,
            target.get("message_count") or 0)


def collect_workspace_files(gateway: str, thread_id: str) -> list[dict]:
    """列出线程最近一次产生文件的 run 的产出清单（runs 接口按最新优先排列）。"""
    try:
        runs = api(gateway, "GET", f"/api/threads/{thread_id}/runs")
    except CliError:
        return []
    if not isinstance(runs, list) or not runs:
        return []
    for run in runs:  # 最新在前
        run_id = run.get("run_id")
        if not run_id:
            continue
        try:
            wc = api(gateway, "GET", f"/api/threads/{thread_id}/runs/{run_id}/workspace-changes")
        except CliError:
            continue
        files = wc.get("files", []) if isinstance(wc, dict) else []
        files = [f for f in files if f.get("status") in ("created", "modified")]
        if files:
            return files
    return []


def download_artifact(gateway: str, thread_id: str, virtual_path: str,
                      local_outputs_dir: str | None, dest: Path) -> bool:
    """下载一个产出文件到 dest。优先走 artifacts API，失败则回退本机路径。"""
    rel = virtual_path.lstrip("/")
    try:
        status, content = api(gateway, "GET",
                              f"/api/threads/{thread_id}/artifacts/{urllib.parse.quote(rel)}",
                              timeout=120, raw=True)
        if status == 200 and content is not None:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
            return True
    except CliError:
        pass
    # 回退：本地沙箱时文件直接在本机 outputs 目录
    if local_outputs_dir:
        marker = "/mnt/user-data/outputs/"
        if marker in virtual_path:
            rel_local = virtual_path.split(marker, 1)[1]
            src = Path(local_outputs_dir) / rel_local
            if src.is_file():
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(src.read_bytes())
                return True
    return False


def _trim(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[:limit] + "…"


def _gateway_ready(gateway: str, timeout: int = 5) -> bool:
    """探测 Gateway 是否可服务（GET /api/threads 返回任何合理状态码即可）。"""
    url = f"{gateway.rstrip('/')}/api/threads"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status < 500
    except urllib.error.HTTPError as exc:
        return exc.code in (200, 401, 403, 404, 405)
    except OSError:
        return False


def _auto_start_gateway() -> str | None:
    """尝试自动启动 DeerFlow 服务。

    优先复用 launchd 托管服务（com.deerflow.dev），未加载则 bootstrap；
    都没有时回退到仓库内的 serve.sh --daemon 后台启动。
    返回启动方式描述；全部失败返回 None。
    """
    import subprocess

    uid = os.getuid()
    plist = Path.home() / "Library" / "LaunchAgents" / "com.deerflow.dev.plist"
    if plist.is_file():
        for args in (
            ["launchctl", "kickstart", "-k", f"gui/{uid}/com.deerflow.dev"],
            ["launchctl", "bootstrap", f"gui/{uid}", str(plist)],
        ):
            try:
                if subprocess.run(args, capture_output=True).returncode == 0:
                    return "launchd (com.deerflow.dev)"
            except FileNotFoundError:
                break  # 无 launchctl，直接尝试 serve.sh
    repo_root = Path(__file__).resolve().parent.parent
    serve = repo_root / "scripts" / "serve.sh"
    if serve.is_file():
        try:
            subprocess.Popen(
                ["/bin/zsh", str(serve), "--daemon", "--skip-install"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return f"serve.sh --daemon ({serve})"
        except FileNotFoundError:
            pass
    return None


def ensure_gateway_ready(gateway: str, *, auto_start: bool = True,
                         wait_timeout: int = 180) -> None:
    """确保 Gateway 可用；未启动时按 auto_start 决定是否自动拉起并等待就绪。"""
    if _gateway_ready(gateway):
        return
    if not auto_start:
        raise CliError(f"无法连接 Gateway ({gateway})。请先启动 DeerFlow 服务")
    print(f"⚠ Gateway 未启动（{gateway}），正在自动启动服务…")
    via = _auto_start_gateway()
    if via is None:
        raise CliError(
            "未找到可用的自动启动方式（无 launchd 服务、无 serve.sh）。\n"
            "请手动在仓库根目录执行: make dev 或 make start"
        )
    print(f"  已触发启动: {via}，等待服务就绪（最长 {wait_timeout}s）…")
    deadline = time.time() + wait_timeout
    while time.time() < deadline:
        if _gateway_ready(gateway):
            print("  ✅ Gateway 已就绪")
            return
        time.sleep(3)
    raise CliError(
        f"Gateway 在 {wait_timeout}s 内未就绪。请手动执行: make dev\n"
        f"（日志: /tmp/deerflow-dev.log 或 logs/gateway.log）"
    )


def run_task(args: argparse.Namespace) -> int:
    gateway = args.gateway
    auto_reply = args.continue_text

    # 确定会话：新建，或复用（--thread-id）
    if args.thread_id:
        thread_id = args.thread_id
        initial_status = thread_status(gateway, thread_id)
        print(f"📝 复用会话: {thread_id}（状态: {initial_status}）")
        # 复用已中断会话，或处于"等待澄清回复"状态（idle 但最后一条是
        # 未回复的 ask_clarification）的会话时，直接进入继续流程，不再重复提交任务
        resume_first = initial_status == "interrupted" or (
            initial_status == "idle"
            and pending_clarification_question(gateway, thread_id) is not None
        )
    else:
        thread_id = create_thread(gateway, args.assistant_id)
        print(f"📝 会话 ID: {thread_id}")
        resume_first = False

    attempt = 0
    auto_count = 0
    local_outputs_dir: str | None = None
    run_id: str | None = None
    last_busy_hint_ts = 0.0  # busy 状态提示节流
    capped_count = 0         # cap 类自动继续计数
    retry_by_submit = False  # error/空转后改为"重新提交任务"而非 resume

    while True:
        if attempt == 0 and not resume_first:
            task_text = f"{args.task}\n{QUALITY_INSTRUCTION}\n{WRITE_PROTOCOL}\n{WORK_HABITS_INSTRUCTION}"
            body: dict = {
                "input": {"messages": [{"role": "user", "content": task_text}]},
                "on_disconnect": "continue",
            }
            if args.assistant_id:
                body["assistant_id"] = args.assistant_id
            print(f"🚀 提交任务: {args.task[:100]}{'…' if len(args.task) > 100 else ''}")
        elif retry_by_submit:
            # error/空转后对线程发 resume 会产生空转 run，改为重新提交任务，
            # 让 agent 基于 /mnt/user-data/outputs/ 下已生成的文件继续补齐。
            retry_by_submit = False
            task_text = (
                "【上次执行被中断，请继续完成当前任务，不要重新开始】\n"
                f"原始任务：{args.task}\n"
                "请先检查 /mnt/user-data/outputs/ 下已生成的文件，"
                "基于已有内容补齐剩余部分，然后调用 present_files 交付。\n"
                f"{QUALITY_INSTRUCTION}\n{WRITE_PROTOCOL}\n{WORK_HABITS_INSTRUCTION}"
            )
            body = {
                "input": {"messages": [{"role": "user", "content": task_text}]},
                "on_disconnect": "continue",
            }
            if args.assistant_id:
                body["assistant_id"] = args.assistant_id
            print(f"🔄 重新提交任务继续执行（{auto_count + 1}/{args.max_continue}）…")
        else:
            body = {"command": {"resume": auto_reply}, "on_disconnect": "continue"}
            print(f"🔄 自动继续({auto_count + 1}/{args.max_continue}): 「{auto_reply}」")
        attempt += 1
        auto_count += 1 if (attempt > 1 or resume_first) else 0

        run_id, last_values = run_stream(gateway, thread_id, body=body,
                                         timeout=args.timeout, progress=not args.no_stream)
        if last_values:
            td = last_values.get("thread_data") or {}
            local_outputs_dir = td.get("outputs_path") or local_outputs_dir

        status = thread_status(gateway, thread_id)
        if status == "idle":
            # run 以 success / error / cap 标记终结时线程都会回到 idle。
            # 先区分 run 是否异常终止，再判断澄清 / cap / 正常完成。
            run_status, stop_reason, llm_calls, msg_count = get_run_status(gateway, thread_id, run_id)
            if run_status == "error":
                # run 执行出错（模型调用失败/输出被截断等）：resume 可能空转，
                # 改用重新提交任务恢复，超限转人工，避免把 error 误报成完成。
                if auto_count < args.max_continue:
                    retry_by_submit = True
                    print(f"⚠ run 异常终止（执行出错/输出被截断）。重新提交任务继续（{auto_count + 1}/{args.max_continue}）…")
                    continue
                print("❌ run 异常终止，且已达自动继续上限，停止等待人工处理。")
                print(f"   之后用以下命令继续: deerflowcli --thread-id {thread_id} \"继续\"")
                return 1
            if run_status == "success" and not stop_reason and llm_calls == 0 and msg_count == 0:
                # 空转 run：resume 未真正执行（如对 error 线程继续后空跑），
                # 不能当完成，改用重新提交任务再试，超限转人工。
                if auto_count < args.max_continue:
                    retry_by_submit = True
                    print(f"⚠ 本轮继续为空转（未执行实际工作）。重新提交任务继续（{auto_count + 1}/{args.max_continue}）…")
                    continue
                print("⚠ 任务未真正完成（多次空转未执行实际工作），停止等待人工处理。")
                print(f"   之后用以下命令继续: deerflowcli --thread-id {thread_id} \"继续\"")
                return 2
            pending_q = pending_clarification_question(gateway, thread_id)
            if pending_q is not None:
                # HITL 澄清：agent 主动停下等你回复（线程状态 idle 但最后一条
                # 消息是未回复的 ask_clarification），需要手动回复才能继续
                print("⏸ agent 需要澄清，等待你的回复：")
                print(f"   ❓ {_trim(str(pending_q), 400)}")
                try:
                    reply = input("   你的回复（回车发送「继续」）: ").strip()
                except EOFError:
                    reply = ""
                if not reply and auto_count >= args.max_continue:
                    print("\n⏹ 已连续自动回复多次仍未完成澄清，停止等待人工处理。")
                    print(f"   之后用以下命令继续: deerflowcli --thread-id {thread_id}")
                    return 130
                auto_reply = reply or args.continue_text
                continue
            # 终态 cap 检测：run 以"完成+标记"终结（如循环检测强制收尾）。
            # 默认只提示不自动继续；--auto-resume-capped 开启时自动发「继续」，
            # 连续 cap 达上限后强制停止，防止真正陷入循环的 agent 无限烧 token。
            if stop_reason:
                label = STOP_REASON_LABELS.get(stop_reason, stop_reason)
                if args.auto_resume_capped and capped_count < args.capped_resume_limit:
                    capped_count += 1
                    auto_reply = args.continue_text
                    print(f"⚠ 本次执行被强制收尾（{label}）。自动继续（{capped_count}/{args.capped_resume_limit}）…")
                    continue
                print(f"⚠ 注意：本次执行被强制收尾（{label}），任务可能未全部完成。")
                print(f"   已交付当前成果；如需继续剩余工作，执行: deerflowcli --thread-id {thread_id} \"继续\"")
            print("✅ 任务完成")
            break
        if status == "interrupted":
            if auto_count >= args.max_continue:
                question = extract_clarification_question(gateway, thread_id)
                print("⏸ agent 需要澄清（已连续自动继续超限，等待你的回复）：")
                if question:
                    print(f"   ❓ {_trim(question, 400)}")
                try:
                    reply = input("   你的回复（回车发送「继续」）: ").strip()
                except EOFError:
                    reply = ""
                auto_reply = reply or args.continue_text
                continue
            # 自动继续
            continue
        if status == "error":
            print("❌ 任务执行失败（线程状态 error）")
            return 1
        # busy / 其他：短暂等待后重查（每 15s 提示一次，避免误判卡死）
        now = time.time()
        if now - last_busy_hint_ts >= 15:
            print(f"  · ⏳ 任务仍在后台执行（线程状态: {status}）…")
            last_busy_hint_ts = now
        time.sleep(3)

    # ── 子任务汇总 ─────────────────────────────────────────────────
    delegs = (last_values or {}).get("delegations") or []
    if delegs:
        ok = sum(1 for d in delegs if d.get("status") == "completed")
        fail = sum(1 for d in delegs if d.get("status") in ("failed", "cancelled", "timed_out", "polling_timed_out"))
        print(f"🧩 子任务汇总: 共 {len(delegs)} 个，完成 {ok}，失败/中断 {fail}")

    # ── 产出文件下载 ──────────────────────────────────────────────
    out_root = Path(args.output_dir) / thread_id
    # 优先下载 agent 用 present_files 交付的文件（线程 state.artifacts，
    # 均为 /mnt/user-data/outputs/* 下的虚拟路径）
    delivered = (last_values or {}).get("artifacts") or []
    delivered_paths: list[str] = []
    for item in delivered:
        path = item if isinstance(item, str) else (item.get("path") if isinstance(item, dict) else None)
        if isinstance(path, str) and path.startswith("/mnt/user-data/outputs/"):
            delivered_paths.append(path)
    files: list[dict]
    if delivered_paths:
        files = [{"path": p} for p in dict.fromkeys(delivered_paths)]
    else:
        # 兜底：未调用 present_files 时，仅取 outputs 目录下的产出文件，
        # 过滤掉 workspace 里的中间产物
        files = [
            f for f in collect_workspace_files(gateway, thread_id)
            if f.get("path", "").startswith("/mnt/user-data/outputs/")
        ]
    if files:
        print(f"\n📦 产出文件 {len(files)} 个，下载到: {out_root}")
        for f in files:
            vpath = f.get("path", "")
            if not vpath:
                continue
            fname = os.path.basename(vpath)
            dest = out_root / fname
            if download_artifact(gateway, thread_id, vpath, local_outputs_dir, dest):
                size = dest.stat().st_size
                print(f"  ✔ {vpath}  ({size} B)")
            else:
                print(f"  ⚠ 下载失败: {vpath}")
    else:
        print("\n📦 未检测到产出文件（任务可能未生成文件）")

    reply = latest_ai_reply(gateway, thread_id)
    print("\n💬 最终回复:")
    print(f"  {reply if reply else '(无文本回复)'}")

    print(f"\n🔗 会话入口: {gateway}/threads/{thread_id}")
    return 0


def main() -> int:
    # 实时刷新输出：非 TTY 管道下 print 默认全缓冲，导致任务进行中的
    # 进度（思考/工具调用/心跳提示）要等命令结束才一次性显示，用户会
    # 误以为任务卡死。开启行缓冲让每行立即输出，中途即可判断任务状态。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(line_buffering=True)
        except Exception:
            pass
    parser = argparse.ArgumentParser(
        prog="deerflowcli",
        description=(
            "DeerFlow 命令行任务执行（本机 Gateway，无需 Docker）。\n"
            "自动附加[质量要求][固定工作习惯]约束 · 中断自动继续 · 产出文件自动下载 · Gateway 未启动时自动拉起"
        ),
        epilog=(
            "\n常用示例:\n"
            "  deerflowcli \"分析 /mnt/planning-docs 下的规划文档并输出总结\"   # 新建会话执行任务\n"
            "  deerflowcli --thread-id <会话ID>                                # 复用已中断会话，自动继续\n"
            "  deerflowcli \"任务\" --output-dir ~/Documents/reports           # 指定下载目录\n"
            "  deerflowcli \"任务\" --max-continue 5                           # 调整自动继续上限\n"
            "  deerflowcli \"任务\" --no-stream                                # 不打印流式进度\n"
            "  deerflowcli \"联网核实：搜索后用 web_fetch 打开链接核实内容\"    # 联网搜索+抓取任务\n"
            "\n功能说明:\n"
            "  · 任务会自动附带[质量要求][大文件写入协议]约束：禁止 agent 降级到\n"
            "    flash/lite 等快速模式；长文档按 write_file(append=True) 分批追加写入避免截断\n"
            "  · 任务自动附带[固定工作习惯]：联网搜索类任务必须输出《联网搜索记录.md》\n"
            "    （含任务概述/过程明细/结论验证/剔除说明）并随主结果一起交付\n"
            "  · 任务被中断时自动发送「继续」恢复，直到拿到结果；超过上限转人工询问\n"
            "  · 执行过程实时输出进度（思考/工具调用/心跳提示逐行刷新），\n"
            "    中途即可判断任务是否正常执行；run 异常终止/空转时自动重新提交任务恢复\n"
            "  · 联网功能走 Tavily（web_search 搜索 + web_fetch 抓取），无需 Jina\n"
             "  · cap 类强制收尾（loop_capped 等）默认自动「继续」直到完成\n"
             "    （--capped-resume-limit 控制上限，默认 3 次）；可用 --no-auto-resume-capped 关闭\n"
             "  · 产出文件自动下载到本地（默认 ~/Downloads/<会话ID>/），只下载\n"
            "    present_files 交付的文件及 outputs 目录下的产物，不含工作区中间文件\n"
            "  · Gateway 未启动时自动拉起服务（launchd com.deerflow.dev → serve.sh --daemon），\n"
            "    可用 --no-auto-start 关闭\n"
            "  · 提示词写法与 Web 端一致；引用资料用沙箱挂载路径 /mnt/xxx；\n"
            "    需联网核实链接时让 agent 用 web_fetch 打开完整 URL；\n"
            "    让 agent 把结果写到 /mnt/user-data/outputs/ 并调用 present_files 交付"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("task", nargs="?", default="",
                        help="任务描述（可用双引号包裹多行文本；--thread-id 复用中断会话时可不填）")
    parser.add_argument("--gateway", default=os.environ.get("DEERFLOW_GATEWAY_URL", DEFAULT_GATEWAY),
                        help=f"Gateway 地址（默认 {DEFAULT_GATEWAY}）")
    parser.add_argument("--output-dir", default=os.environ.get("DEERFLOW_OUTPUT_DIR", DEFAULT_OUTPUT_DIR),
                        help=f"产出文件下载目录（默认 {DEFAULT_OUTPUT_DIR}）")
    parser.add_argument("--max-continue", type=int, default=DEFAULT_MAX_CONTINUE,
                        help=f"中断时最大自动继续次数，超限转人工（默认 {DEFAULT_MAX_CONTINUE}）")
    parser.add_argument("--continue-text", default=DEFAULT_CONTINUE_TEXT,
                        help=f"自动继续时发送的文字（默认「{DEFAULT_CONTINUE_TEXT}」）")
    parser.add_argument("--thread-id", default=None,
                        help="复用已有会话（如之前中断未完成的会话），缺省则新建")
    parser.add_argument("--assistant-id", default=None, help="指定 assistant（缺省用默认）")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"单次任务最长等待秒数（默认 {DEFAULT_TIMEOUT}）")
    parser.add_argument("--no-stream", action="store_true", help="不打印流式进度")
    parser.add_argument("--auto-resume-capped", action=argparse.BooleanOptionalAction,
                        default=True,
                        help="cap 类停止（如 loop_capped）时自动发送「继续」继续任务（默认开启；"
                             "可用 --no-auto-resume-capped 关闭，关闭后只提示不自动继续）")
    parser.add_argument("--capped-resume-limit", type=int, default=3,
                        help="cap 类自动继续的最大次数，超限停止并提示（默认 3）")
    parser.add_argument("--no-auto-start", action="store_true",
                        help="Gateway 未启动时不自动拉起，直接报错退出")
    parser.add_argument("--wait-timeout", type=int, default=180,
                        help="自动启动后等待 Gateway 就绪的最长秒数（默认 180）")
    parser.add_argument("--verbose", action="store_true", help="打印调试信息")
    args = parser.parse_args()

    if not args.task.strip() and not args.thread_id:
        print("错误：任务描述不能为空（除非用 --thread-id 复用已中断的会话）", file=sys.stderr)
        return 2

    try:
        ensure_gateway_ready(args.gateway, auto_start=not args.no_auto_start,
                             wait_timeout=args.wait_timeout)
        code = run_task(args)
    except CliError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已中断（Ctrl+C）。会话保留，可用 --thread-id 重新继续。", file=sys.stderr)
        return 130
    return code


if __name__ == "__main__":
    sys.exit(main())
