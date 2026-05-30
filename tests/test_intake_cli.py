import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "intake_cli.py"


def write_task(path: Path, *, status: str = "COLLECTING_PRODUCTS", current_product=None) -> None:
    task = {
        "task_id": "pi_test_001",
        "status": status,
        "created_at": "2026-05-30T12:00:00+08:00",
        "updated_at": "2026-05-30T12:00:00+08:00",
        "operator": {"open_id": None, "display_name": None},
        "target": {
            "base_token": "base_xxx",
            "table_id": "tbl_xxx",
            "view_id": None,
            "source_url": None,
        },
        "field_mapping": {},
        "products": [],
        "current_product": current_product,
        "upload": {"status": "NOT_STARTED", "errors": []},
    }
    path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")


def read_task(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class IntakeCliTests(unittest.TestCase):
    def run_cli(self, *args: str, cwd: Path):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=cwd,
            text=True,
            capture_output=True,
        )

    def test_add_text_creates_current_product_and_appends_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            task_path = cwd / "task.json"
            write_task(task_path)

            result = self.run_cli(
                "add-text",
                "--task",
                str(task_path),
                "--text",
                "白水晶，12mm，12克价",
                cwd=cwd,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            task = read_task(task_path)
            self.assertEqual(task["current_product"]["local_id"], "p001")
            self.assertEqual(task["current_product"]["status"], "DRAFT")
            self.assertEqual(task["current_product"]["raw_description"], "白水晶，12mm，12克价")
            self.assertEqual(task["current_product"]["text_snippets"], ["白水晶，12mm，12克价"])
            self.assertIn("当前商品 p001", result.stdout)

    def test_add_media_copies_files_with_sequence_and_preserves_chinese_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            task_path = cwd / "task.json"
            write_task(
                task_path,
                current_product={
                    "local_id": "p001",
                    "status": "DRAFT",
                    "raw_description": "紫水晶 12mm 5克价",
                    "text_snippets": ["紫水晶 12mm 5克价"],
                    "parsed_fields": {},
                    "media": [],
                    "base_record_id": None,
                    "upload_status": "PENDING",
                },
            )
            source_dir = cwd / "sources"
            source_dir.mkdir()
            files = [
                source_dir / "图片一.jpg",
                source_dir / "image-two.webp",
                source_dir / "video-three.mp4",
            ]
            for index, file_path in enumerate(files, start=1):
                file_path.write_bytes(f"file-{index}".encode("ascii"))

            result = self.run_cli(
                "add-media",
                "--task",
                str(task_path),
                "--files",
                *(str(file_path) for file_path in files),
                cwd=cwd,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            task = read_task(task_path)
            media = task["current_product"]["media"]
            self.assertEqual([item["sequence"] for item in media], [1, 2, 3])
            self.assertEqual([item["type"] for item in media], ["image", "image", "video"])
            self.assertEqual(media[0]["original_name"], "图片一.jpg")
            self.assertEqual(media[0]["cache_path"], "cache/pi_test_001/p001/001.jpg")
            self.assertEqual(media[2]["cache_path"], "cache/pi_test_001/p001/003.mp4")
            self.assertTrue((cwd / media[0]["cache_path"]).exists())
            self.assertTrue((cwd / media[1]["cache_path"]).exists())
            self.assertTrue((cwd / media[2]["cache_path"]).exists())

    def test_next_seals_non_empty_product_and_creates_empty_next_product(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            task_path = cwd / "task.json"
            write_task(
                task_path,
                current_product={
                    "local_id": "p001",
                    "status": "DRAFT",
                    "raw_description": "白水晶",
                    "text_snippets": ["白水晶"],
                    "parsed_fields": {},
                    "media": [],
                    "base_record_id": None,
                    "upload_status": "PENDING",
                },
            )

            result = self.run_cli("next", "--task", str(task_path), cwd=cwd)

            self.assertEqual(result.returncode, 0, result.stderr)
            task = read_task(task_path)
            self.assertEqual(len(task["products"]), 1)
            self.assertEqual(task["products"][0]["local_id"], "p001")
            self.assertEqual(task["products"][0]["status"], "SEALED")
            self.assertEqual(task["current_product"]["local_id"], "p002")
            self.assertEqual(task["current_product"]["status"], "EMPTY_DRAFT")

    def test_next_on_empty_product_does_not_create_empty_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            task_path = cwd / "task.json"
            write_task(
                task_path,
                current_product={
                    "local_id": "p001",
                    "status": "EMPTY_DRAFT",
                    "raw_description": "",
                    "text_snippets": [],
                    "parsed_fields": {},
                    "media": [],
                    "base_record_id": None,
                    "upload_status": "PENDING",
                },
            )

            result = self.run_cli("next", "--task", str(task_path), cwd=cwd)

            self.assertEqual(result.returncode, 0, result.stderr)
            task = read_task(task_path)
            self.assertEqual(task["products"], [])
            self.assertEqual(task["current_product"]["local_id"], "p001")
            self.assertEqual(task["current_product"]["status"], "EMPTY_DRAFT")

    def test_finish_seals_current_product_and_reports_summary_without_uploading(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            task_path = cwd / "task.json"
            write_task(
                task_path,
                current_product={
                    "local_id": "p001",
                    "status": "DRAFT",
                    "raw_description": "白水晶",
                    "text_snippets": ["白水晶"],
                    "parsed_fields": {},
                    "media": [
                        {
                            "sequence": 1,
                            "message_id": "local_image_p001_001",
                            "resource_key": "one.jpg",
                            "type": "image",
                            "mime_type": "image/jpeg",
                            "original_name": "one.jpg",
                            "cache_path": "cache/pi_test_001/p001/001.jpg",
                            "received_at": "2026-05-30T12:00:00+08:00",
                            "download_status": "DOWNLOADED",
                            "upload_status": "PENDING",
                            "error": None,
                        }
                    ],
                    "base_record_id": None,
                    "upload_status": "PENDING",
                },
            )

            result = self.run_cli("finish", "--task", str(task_path), cwd=cwd)

            self.assertEqual(result.returncode, 0, result.stderr)
            task = read_task(task_path)
            self.assertEqual(task["status"], "READY_TO_UPLOAD")
            self.assertEqual(task["upload"]["status"], "NOT_STARTED")
            self.assertIsNone(task["current_product"])
            self.assertEqual(len(task["products"]), 1)
            self.assertEqual(task["products"][0]["status"], "SEALED")
            self.assertIn("本批次共 1 个商品，图片 1 张，视频 0 个", result.stdout)


if __name__ == "__main__":
    unittest.main()
