#!/usr/bin/env python3
"""Fast deterministic intake-state commands for local product capture."""

from __future__ import annotations

import argparse
import copy
import json
import mimetypes
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


ALLOWED_STATES = {"COLLECTING_PRODUCTS", "READY_TO_UPLOAD"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".3gp"}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
PENDING_DOWNLOAD_STATUSES = {"RECEIVED", "DOWNLOADING"}
PRODUCT_INTAKE_SCOPES = [
    "base:field:read",
    "base:table:read",
    "base:record:create",
    "base:record:update",
    "base:record:read",
    "docs:document.media:upload",
]
SHANGHAI_TZ = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(SHANGHAI_TZ).isoformat(timespec="seconds")


def load_task(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as task_file:
        task = json.load(task_file)
    if task.get("status") not in ALLOWED_STATES:
        raise IntakeError(f"当前任务状态是 {task.get('status')}，脚本只处理 COLLECTING_PRODUCTS 或 READY_TO_UPLOAD。")
    return task


def save_task(path: Path, task: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as temp_file:
            json.dump(task, temp_file, ensure_ascii=False, indent=2)
            temp_file.write("\n")
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


class IntakeError(Exception):
    pass


def require_collecting(task: dict[str, Any]) -> None:
    if task.get("status") != "COLLECTING_PRODUCTS":
        raise IntakeError(f"当前任务状态是 {task.get('status')}，只有 COLLECTING_PRODUCTS 可继续录入。")


def make_product(local_id: str) -> dict[str, Any]:
    return {
        "local_id": local_id,
        "status": "EMPTY_DRAFT",
        "raw_description": "",
        "text_snippets": [],
        "parsed_fields": {},
        "media": [],
        "base_record_id": None,
        "upload_status": "PENDING",
    }


def product_number(local_id: str) -> int:
    digits = "".join(char for char in local_id if char.isdigit())
    return int(digits or "0")


def next_product_id(task: dict[str, Any]) -> str:
    products = task.get("products") or []
    current = task.get("current_product")
    max_number = 0
    for product in products:
        max_number = max(max_number, product_number(product.get("local_id", "")))
    if current:
        max_number = max(max_number, product_number(current.get("local_id", "")))
    return f"p{max_number + 1:03d}"


def ensure_current_product(task: dict[str, Any]) -> dict[str, Any]:
    current = task.get("current_product")
    if current is None:
        current = make_product(next_product_id(task))
        task["current_product"] = current
    current.setdefault("text_snippets", [])
    current.setdefault("media", [])
    current.setdefault("parsed_fields", {})
    current.setdefault("base_record_id", None)
    current.setdefault("upload_status", "PENDING")
    current.setdefault("raw_description", "")
    current.setdefault("status", "EMPTY_DRAFT")
    return current


def is_non_empty(product: dict[str, Any] | None) -> bool:
    if not product:
        return False
    if product.get("raw_description", "").strip():
        return True
    if product.get("text_snippets"):
        return True
    return bool(product.get("media"))


def media_counts(product: dict[str, Any] | None) -> tuple[int, int, int]:
    media = (product or {}).get("media") or []
    images = sum(1 for item in media if item.get("type") == "image")
    videos = sum(1 for item in media if item.get("type") == "video")
    pending = sum(1 for item in media if item.get("download_status") in PENDING_DOWNLOAD_STATUSES)
    return images, videos, pending


def batch_counts(task: dict[str, Any]) -> tuple[int, int, int, int]:
    products = task.get("products") or []
    image_count = 0
    video_count = 0
    pending_count = 0
    for product in products:
        images, videos, pending = media_counts(product)
        image_count += images
        video_count += videos
        pending_count += pending
    return len(products), image_count, video_count, pending_count


def seal_current_product(task: dict[str, Any]) -> bool:
    current = task.get("current_product")
    if not is_non_empty(current):
        return False
    sealed = copy.deepcopy(current)
    sealed["status"] = "SEALED"
    task.setdefault("products", []).append(sealed)
    return True


def append_ack(task: dict[str, Any]) -> str:
    current = task.get("current_product")
    if current is None:
        product_count, image_count, video_count, pending_count = batch_counts(task)
        return f"本批次共 {product_count} 个商品，图片 {image_count} 张，视频 {video_count} 个，待处理素材 {pending_count} 个。"
    images, videos, pending = media_counts(current)
    text_count = len(current.get("text_snippets") or [])
    return (
        f"当前商品 {current.get('local_id')}：说明 {text_count} 条，"
        f"图片 {images} 张，视频 {videos} 个，待处理素材 {pending} 个。"
    )


def command_add_text(args: argparse.Namespace) -> str:
    task_path = Path(args.task)
    task = load_task(task_path)
    require_collecting(task)
    current = ensure_current_product(task)
    current["text_snippets"].append(args.text)
    current["raw_description"] = "\n".join(current["text_snippets"])
    current["status"] = "DRAFT"
    task["updated_at"] = now_iso()
    save_task(task_path, task)
    return append_ack(task)


def media_type_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    raise IntakeError(f"不支持的素材类型：{path}")


def cache_root_for(task_path: Path, task_id: str, product_id: str) -> Path:
    return task_base_dir(task_path) / "cache" / task_id / product_id


def relative_cache_path(task_id: str, product_id: str, filename: str) -> str:
    return Path("cache", task_id, product_id, filename).as_posix()


def all_products(task: dict[str, Any]) -> list[dict[str, Any]]:
    products = list(task.get("products") or [])
    current = task.get("current_product")
    if current:
        products.append(current)
    return products


def registered_cache_paths(task: dict[str, Any]) -> set[str]:
    paths: set[str] = set()
    for product in all_products(task):
        for item in product.get("media") or []:
            cache_path = str(item.get("cache_path") or "")
            if cache_path:
                paths.add(Path(cache_path).as_posix())
    return paths


def task_base_dir(task_path: Path) -> Path:
    return task_path.parent.parent if task_path.parent.name == "intake-tasks" else Path.cwd()


def find_unregistered_media(task_path: Path, task: dict[str, Any]) -> list[str]:
    cache_root = task_base_dir(task_path) / "cache" / str(task.get("task_id", ""))
    if not cache_root.is_dir():
        return []
    registered = registered_cache_paths(task)
    unregistered: list[str] = []
    for path in sorted(cache_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in MEDIA_EXTENSIONS:
            continue
        rel = path.relative_to(task_base_dir(task_path)).as_posix()
        if rel not in registered:
            unregistered.append(rel)
    return unregistered


def collect_upload_blockers(task_path: Path, task: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for product in task.get("products") or []:
        product_id = product.get("local_id") or "<unknown>"
        if not str(product.get("raw_description") or "").strip():
            blockers.append(f"{product_id} 缺少产品说明")
        pending = [
            item for item in product.get("media") or []
            if item.get("download_status") in PENDING_DOWNLOAD_STATUSES
        ]
        if pending:
            seqs = ", ".join(str(item.get("sequence")) for item in pending)
            blockers.append(f"{product_id} 仍有待下载素材：{seqs}")
    unregistered = find_unregistered_media(task_path, task)
    if unregistered:
        blockers.append("cache 中存在未登记素材：" + ", ".join(unregistered))
    return blockers


def command_add_media(args: argparse.Namespace) -> str:
    task_path = Path(args.task)
    task = load_task(task_path)
    require_collecting(task)
    current = ensure_current_product(task)
    task_id = task["task_id"]
    product_id = current["local_id"]
    cache_dir = cache_root_for(task_path, task_id, product_id)
    cache_dir.mkdir(parents=True, exist_ok=True)
    media = current.setdefault("media", [])
    next_sequence = max((int(item.get("sequence", 0)) for item in media), default=0) + 1
    received_at = now_iso()

    for file_name in args.files:
        source = Path(file_name)
        if not source.exists():
            raise IntakeError(f"素材文件不存在：{source}")
        item_type = media_type_for(source)
        sequence = next_sequence
        next_sequence += 1
        suffix = source.suffix.lower()
        cache_name = f"{sequence:03d}{suffix}"
        destination = cache_dir / cache_name
        shutil.copy2(source, destination)
        mime_type, _ = mimetypes.guess_type(str(destination))
        media.append(
            {
                "sequence": sequence,
                "message_id": f"local_{item_type}_{product_id}_{sequence:03d}",
                "resource_key": source.name,
                "type": item_type,
                "mime_type": mime_type or "application/octet-stream",
                "original_name": source.name,
                "cache_path": relative_cache_path(task_id, product_id, cache_name),
                "received_at": received_at,
                "download_status": "DOWNLOADED",
                "upload_status": "PENDING",
                "error": None,
            }
        )

    if media:
        current["status"] = "DRAFT"
    task["updated_at"] = now_iso()
    save_task(task_path, task)
    return append_ack(task)


def command_next(args: argparse.Namespace) -> str:
    task_path = Path(args.task)
    task = load_task(task_path)
    require_collecting(task)
    sealed = seal_current_product(task)
    if sealed:
        task["current_product"] = make_product(next_product_id(task))
        message = f"已封存上一个商品。{append_ack(task)}"
    else:
        task["current_product"] = ensure_current_product(task)
        message = f"当前商品为空，未创建新记录。{append_ack(task)}"
    task["updated_at"] = now_iso()
    save_task(task_path, task)
    return message


def command_finish(args: argparse.Namespace) -> str:
    task_path = Path(args.task)
    task = load_task(task_path)
    if task.get("status") == "COLLECTING_PRODUCTS":
        seal_current_product(task)
        task["current_product"] = None
        task["status"] = "READY_TO_UPLOAD"
        task.setdefault("upload", {}).setdefault("status", "NOT_STARTED")
    product_count, image_count, video_count, pending_count = batch_counts(task)
    blockers = collect_upload_blockers(task_path, task)
    task.setdefault("upload", {})["preflight_blockers"] = blockers
    task["updated_at"] = now_iso()
    save_task(task_path, task)
    suffix = "发送“确认上传”后才会写入飞书表。"
    if blockers:
        suffix = "上传前需处理：" + "；".join(blockers)
    return (
        f"本批次共 {product_count} 个商品，图片 {image_count} 张，"
        f"视频 {video_count} 个，待处理素材 {pending_count} 个。{suffix}"
    )


def command_preflight(args: argparse.Namespace) -> str:
    task_path = Path(args.task)
    task = load_task(task_path)
    blockers = collect_upload_blockers(task_path, task)
    task.setdefault("upload", {})["preflight_blockers"] = blockers
    task["updated_at"] = now_iso()
    save_task(task_path, task)
    if blockers:
        raise IntakeError("上传前检查未通过：" + "；".join(blockers))
    product_count, image_count, video_count, pending_count = batch_counts(task)
    return f"上传前检查通过：{product_count} 个商品，图片 {image_count} 张，视频 {video_count} 个，待处理素材 {pending_count} 个。"


def command_auth_scopes(args: argparse.Namespace) -> str:
    scopes = " ".join(PRODUCT_INTAKE_SCOPES)
    if args.command_only:
        return f'lark-cli auth login --scope "{scopes}" --no-wait --json'
    return (
        "产品录入推荐一次性授权权限包：\n"
        f"{scopes}\n"
        "用于读取表字段、创建记录、上传附件、上传后读取核验。\n"
        f'授权命令：lark-cli auth login --scope "{scopes}" --no-wait --json'
    )


def command_status(args: argparse.Namespace) -> str:
    task = load_task(Path(args.task))
    return f"任务状态 {task.get('status')}。{append_ack(task)}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fast local product intake state updater")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_text = subparsers.add_parser("add-text", help="append text to the current product")
    add_text.add_argument("--task", required=True)
    add_text.add_argument("--text", required=True)
    add_text.set_defaults(handler=command_add_text)

    add_media = subparsers.add_parser("add-media", help="append media files to the current product")
    add_media.add_argument("--task", required=True)
    add_media.add_argument("--files", nargs="+", required=True)
    add_media.set_defaults(handler=command_add_media)

    next_command = subparsers.add_parser("next", help="seal current product and start the next product")
    next_command.add_argument("--task", required=True)
    next_command.set_defaults(handler=command_next)

    finish = subparsers.add_parser("finish", help="finish collection and summarize the batch")
    finish.add_argument("--task", required=True)
    finish.set_defaults(handler=command_finish)

    preflight = subparsers.add_parser("preflight", help="validate the batch before uploading")
    preflight.add_argument("--task", required=True)
    preflight.set_defaults(handler=command_preflight)

    auth_scopes = subparsers.add_parser("auth-scopes", help="print recommended one-shot Lark auth scopes")
    auth_scopes.add_argument("--command-only", action="store_true")
    auth_scopes.set_defaults(handler=command_auth_scopes)

    status = subparsers.add_parser("status", help="show current intake status")
    status.add_argument("--task", required=True)
    status.set_defaults(handler=command_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        print(args.handler(args))
    except IntakeError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
