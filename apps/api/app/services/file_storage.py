from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ValidationException


@dataclass(frozen=True)
class StoredFile:
    stored_name: str
    size: int
    storage_path: str


class LocalFileStorage:
    allowed_types = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "image/png",
        "image/jpeg",
        "text/csv",
        "text/plain",
    }

    def __init__(self) -> None:
        self.root = Path(settings.storage_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def safe_segment(self, value: object, fallback: str = "unknown") -> str:
        raw = str(value or "").strip()
        if not raw:
            raw = fallback
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", raw)
        safe = re.sub(r"-{2,}", "-", safe).strip("-. _")
        return safe[:120] or fallback

    def relative_dir(self, *segments: object) -> Path:
        safe_segments = [self.safe_segment(segment) for segment in segments if segment not in (None, "")]
        return Path(*safe_segments) if safe_segments else Path()

    async def save(self, file: UploadFile, relative_dir: str | Path | None = None) -> tuple[str, int]:
        stored = await self.save_with_path(file, relative_dir=relative_dir)
        return stored.stored_name, stored.size

    async def save_with_path(self, file: UploadFile, relative_dir: str | Path | None = None) -> StoredFile:
        content = await file.read()
        size = len(content)
        if size > settings.max_upload_size_mb * 1024 * 1024:
            raise ValidationException(f"File exceeds {settings.max_upload_size_mb} MB limit.")
        if file.content_type not in self.allowed_types:
            raise ValidationException(f"File type {file.content_type} is not allowed.")

        extension = Path(file.filename or "upload.bin").suffix
        stored_name = f"{uuid4().hex}{extension}"
        target_dir = self.root / relative_dir if relative_dir else self.root
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / stored_name
        target.write_bytes(content)
        await file.seek(0)
        return StoredFile(stored_name=stored_name, size=size, storage_path=str(target.resolve()))

    async def save_for_context(self, file: UploadFile, *segments: object) -> StoredFile:
        return await self.save_with_path(file, relative_dir=self.relative_dir(*segments))

    async def save_to_staging(self, file: UploadFile) -> StoredFile:
        return await self.save_for_context(file, "_staging")

    def move_to_context(self, source_path: str, *segments: object, stored_name: str | None = None) -> str:
        source = Path(source_path)
        if not source.exists():
            raise ValidationException("Stored document file not found for repository move.")
        target_dir = self.root / self.relative_dir(*segments)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_name = self.safe_segment(stored_name or source.name, fallback=source.name)
        target = target_dir / target_name
        if source.resolve() == target.resolve():
            return str(target.resolve())
        if target.exists():
            target = target_dir / f"{target.stem}-{uuid4().hex[:8]}{target.suffix}"
        shutil.move(str(source), str(target))
        return str(target.resolve())

    def path_for(self, stored_name: str, relative_dir: str | Path | None = None) -> str:
        base = self.root / relative_dir if relative_dir else self.root
        return str((base / stored_name).resolve())


file_storage = LocalFileStorage()
