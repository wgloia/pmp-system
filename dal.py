"""
知识库访问层 — kwiki-cli 子进程封装
所有对 WPS 知识库的读写操作通过此模块统一调用。
"""
import subprocess
import json
import os
import re
from typing import Optional

from db import KWIKI_CLI, KWIKI_AUTH, PMP_KUID


def _run(*args: str, timeout: int = 120, max_retries: int = 2) -> dict:
    """执行 kwiki-cli 命令并返回 JSON 解析结果，失败自动重试"""
    env = os.environ.copy()
    env["X_KWIKI_AUTH"] = KWIKI_AUTH
    npm_bin = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "npm")
    path = env.get("PATH", "")
    if npm_bin not in path:
        env["PATH"] = npm_bin + os.pathsep + path
    cmd = [KWIKI_CLI, *args, "--format", "json"]

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
                env=env, encoding="utf-8",
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"kwiki-cli exit {result.returncode}: {result.stderr[-300:]}"
                )
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {"raw": result.stdout}
        except (subprocess.TimeoutExpired, RuntimeError) as e:
            last_error = e
            if attempt < max_retries:
                import time
                time.sleep(2)
                continue
    raise RuntimeError(f"kwiki-cli failed after {max_retries + 1} attempts: {last_error}")


def ask_knowledge_base(
    question: str,
    kuid: str = PMP_KUID,
    *,
    web_search: bool = False,
    deep_think: bool = False,
    stream: bool = False,
) -> str:
    """
    对知识库进行智能问答。
    返回拼接后的完整答案文本（默认），stream=True 返回原始 SSE。
    当知识库检索不到内容时自动缩短 prompt 重试。
    """
    args = [
        "kwiki", "knowledge-view-ask",
        "--input", question,
        "--kuid", kuid,
    ]
    if web_search:
        args.append("--web-search")
    if deep_think:
        args.append("--switch-thinking")
    if stream:
        args.append("--stream")

    result = _run(*args, timeout=180)

    # 检测知识库检索失败（code 100200 = 未找到相关内容）
    code = result.get("code", 0)
    if code == 100200 and len(question) > 200:
        # 缩短 prompt 重试：太长导致检索无结果
        short_q = question[:200] + "\n请基于上述资料回答问题。"
        result = _run("kwiki", "knowledge-view-ask",
                      "--input", short_q, "--kuid", kuid, "--format", "json",
                      timeout=180)

    if stream:
        return result.get("raw", "")

    # 默认聚合模式：提取 answer_citations[0].text
    citations = result.get("answer_citations", [])
    if citations:
        return citations[0].get("text", "")

    # 如果是错误响应，抛出异常而不是返回错误 JSON
    caution = result.get("caution", "")
    if caution:
        raise RuntimeError(f"知识库返回错误(code={code}): {caution[:200]}")

    return json.dumps(result, ensure_ascii=False, indent=2)


def list_files(kuid: str = PMP_KUID) -> list[dict]:
    """列出知识库/文件夹中的文件"""
    return _run("kwiki", "file-list", "--kuid", kuid).get("list", [])


def get_knowledge_base_info(kuid: str = PMP_KUID) -> dict:
    """获取知识库详情"""
    return _run("kwiki", "knowledge-view-get", "--kuid", kuid)


def upload_file(file_path: str, drive_id: str) -> dict:
    """上传本地文件到知识库"""
    return _run(
        "kwiki", "file-upload",
        "--drive-id", drive_id,
        "--file", file_path,
        timeout=300,
    )


def extract_chapter_topics() -> list[str]:
    """
    从知识库中提取章节/知识点主题列表。
    利用 AI 问答能力自动从 PDF 资料中识别知识领域划分。
    """
    prompt = (
        "请分析PMP备考资料中的章节结构。"
        "列出所有主要的知识领域/章节名称，每个一行，只返回列表，不要额外解释。"
        "格式示例：\n整合管理\n范围管理\n..."
    )
    text = ask_knowledge_base(prompt, deep_think=False)
    lines = [line.strip().lstrip("0123456789.、- ") for line in text.split("\n") if line.strip()]
    # 过滤掉非章节行（长度过短或过长的）
    return [l for l in lines if 3 < len(l) < 30][:20]
