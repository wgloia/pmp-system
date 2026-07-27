"""
本地知识索引 — 下载 WPS 知识库 PDF → 解析 → 向量化 → 本地检索
首次运行会下载 PDF 并建索引（耗时约 3-5 分钟），之后秒级检索。
"""
import os
import json
import base64
import re
from pathlib import Path

import fitz  # PyMuPDF
import chromadb
from chromadb.config import Settings

from db import PMP_KUID
from dal import _run  # kwiki-cli 子进程封装

# 文件存储路径
DATA_DIR = Path(__file__).parent / "local_data"
PDF_DIR = DATA_DIR / "pdfs"
INDEX_DIR = DATA_DIR / "chroma_index"

# ChromaDB 客户端（持久化）
_client = None
_collection = None


def _get_collection():
    """获取或创建 ChromaDB collection（懒加载）"""
    global _client, _collection
    if _collection is None:
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(INDEX_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        try:
            _collection = _client.get_collection("pmp_knowledge")
        except Exception:
            _collection = _client.create_collection("pmp_knowledge")
    return _collection


# ──────────── 第 1 步：下载 PDF ────────────

def download_all_pdfs(force: bool = False) -> list[Path]:
    """下载知识库中所有 PDF 到本地"""
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    result = _run("kwiki", "file-list", "--kuid", PMP_KUID)
    files = result.get("list", [])
    pdf_files = [f for f in files if f.get("doc_origin_type") == "pdf"]

    downloaded = []
    for f in pdf_files:
        local_path = PDF_DIR / f"{f['kuid']}.pdf"
        if local_path.exists() and not force:
            downloaded.append(local_path)
            continue

        print(f"  下载: {f['title'][:50]}...")
        result = _run(
            "kwiki", "file-download",
            "--kuid", f["kuid"],
            "--response-type", "file_base64",
            timeout=300,
        )
        b64 = result.get("file_base64", "")
        if b64:
            pdf_bytes = base64.b64decode(b64)
            local_path.write_bytes(pdf_bytes)
            downloaded.append(local_path)
            print(f"    完成: {len(pdf_bytes) // 1024} KB")

    return downloaded


# ──────────── 第 2 步：解析 PDF 文本 ────────────

def parse_pdf_to_text(pdf_path: Path) -> str:
    """用 PyMuPDF 提取 PDF 文本"""
    doc = fitz.open(str(pdf_path))
    pages = []
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            pages.append(text.strip())
    doc.close()
    return "\n\n".join(pages)


def _clean_text(text: str) -> str:
    """清理文本：去页码、页眉、多余空行"""
    # 去独立数字行（页码）
    text = re.sub(r"\n\d{1,4}\n", "\n", text)
    # 多个空行合并
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


# ──────────── 第 3 步：文本分块 ────────────

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """
    将长文本切分为重叠块。
    优先按段落切分，段落过长时按句子切分。
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 20]
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) <= chunk_size:
            current += para + "\n\n"
        else:
            if current:
                chunks.append(current.strip())
            # 段落本身过长时，按句子切
            if len(para) > chunk_size:
                sentences = re.split(r"(?<=[。！？])", para)
                sub = ""
                for s in sentences:
                    if len(sub) + len(s) <= chunk_size:
                        sub += s
                    else:
                        if sub:
                            chunks.append(sub.strip())
                        sub = s
                if sub:
                    current = sub + "\n\n"
                else:
                    current = ""
            else:
                current = para + "\n\n"

    if current.strip():
        chunks.append(current.strip())

    # 加入重叠
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-overlap:] if len(chunks[i - 1]) > overlap else chunks[i - 1]
            overlapped.append(prev_tail + "\n" + chunks[i])
        chunks = overlapped

    return chunks


# ──────────── 第 4 步：构建向量索引 ────────────

def rebuild_index(pdf_paths=None):  # list[Path] or None
    """重建本地知识索引（删除旧索引，解析 PDF，分块，向量化）"""
    collection = _get_collection()

    # 清空旧数据
    try:
        existing = collection.get()
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    if pdf_paths is None:
        pdf_paths = list(PDF_DIR.glob("*.pdf"))

    all_chunks = []
    all_metadatas = []
    all_ids = []
    chunk_id = 0

    for pdf_path in pdf_paths:
        fname = pdf_path.stem  # kuid as identifier
        print(f"  解析: {fname}")
        text = parse_pdf_to_text(pdf_path)
        text = _clean_text(text)
        chunks = chunk_text(text)

        for c in chunks:
            all_chunks.append(c)
            all_metadatas.append({"source": fname, "filename": pdf_path.name})
            all_ids.append(f"chunk_{chunk_id}")
            chunk_id += 1

        print(f"    → {len(chunks)} 个文本块")

    if not all_chunks:
        return 0

    # 批量写入（ChromaDB 自动调用 embedding 模型向量化）
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        end = min(i + batch_size, len(all_chunks))
        collection.add(
            documents=all_chunks[i:end],
            metadatas=all_metadatas[i:end],
            ids=all_ids[i:end],
        )

    return len(all_chunks)


# ──────────── 第 5 步：本地检索 ────────────

def search(query: str, top_k: int = 5) -> list[dict]:
    """本地语义检索，返回 top_k 个最相关的文本块"""
    collection = _get_collection()
    try:
        results = collection.query(query_texts=[query], n_results=top_k)
    except Exception:
        return []

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0] if results.get("distances") else [0] * len(docs)

    output = []
    for i, doc in enumerate(docs):
        output.append({
            "text": doc,
            "source": metas[i].get("source", "") if i < len(metas) else "",
            "relevance": round(1 - distances[i], 3) if i < len(distances) else 0,
        })

    return output


def search_as_context(query: str, top_k: int = 5, max_chars: int = 3000) -> str:
    """检索并拼接为上下文字符串，用于喂给 LLM"""
    results = search(query, top_k)
    context_parts = []
    total = 0
    for r in results:
        if total + len(r["text"]) > max_chars:
            break
        context_parts.append(r["text"])
        total += len(r["text"])
    return "\n\n---\n\n".join(context_parts)


# ──────────── 一键初始化 ────────────

def ensure_index():
    """确保本地索引可用（首次运行自动下载+建索引）"""
    if PDF_DIR.glob("*.pdf"):
        # 已有 PDF 但无索引（第一次 run 或索引损坏）
        collection = _get_collection()
        try:
            existing = collection.get()
            if existing["ids"]:
                return  # 索引已存在，跳过
        except Exception:
            pass

    print("\n[ 初始化本地知识索引（首次运行，需 3-5 分钟）...")
    print("  第 1 步：下载 PDF 文件...")
    paths = download_all_pdfs()
    if not paths:
        print("  ! 未找到可下载的 PDF")
        return

    print(f"\n  第 2 步：解析 {len(paths)} 个 PDF 并建索引...")
    total = rebuild_index(paths)
    print(f"\n  OK 完成！共 {total} 个文本块已索引\n")


if __name__ == "__main__":
    ensure_index()
