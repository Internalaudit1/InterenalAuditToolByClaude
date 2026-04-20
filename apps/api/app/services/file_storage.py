from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ValidationException


class LocalFileStorage:
    allowed_types = {
        "application/pdf",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "image/png",
        "image/jpeg",
        "text/csv",
    }

    def __init__(self) -> None:
        self.root = Path(settings.storage_root)
        self.root.mkdir(parents=True, exist_ok=True)

    async def save(self, file: UploadFile) -> tuple[str, int]:
        content = await file.read()
        size = len(content)
        if size > settings.max_upload_size_mb * 1024 * 1024:
            raise ValidationException(f"File exceeds {settings.max_upload_size_mb} MB limit.")
        if file.content_type not in self.allowed_types:
            raise ValidationException(f"File type {file.content_type} is not allowed.")

        extension = Path(file.filename or "upload.bin").suffix
        stored_name = f"{uuid4().hex}{extension}"
        target = self.root / stored_name
        target.write_bytes(content)
        await file.seek(0)
        return stored_name, size


file_storage = LocalFileStorage()
