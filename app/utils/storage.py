"""
storage.py
──────────
Supabase Storage helper.
Replaces local file saving for receipts + prescriptions.
Every PDF gets a permanent public URL — survives Railway restarts.
"""

import os
import uuid
from supabase import create_client, Client
from app.config import settings


def _get_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def upload_pdf(local_path: str, folder: str = "receipts") -> str:
    """
    Upload a PDF file to Supabase Storage.
    Returns permanent public URL.

    folder: "receipts" | "prescriptions"
    """
    client = _get_client()

    filename  = os.path.basename(local_path)
    dest_path = f"{folder}/{filename}"

    with open(local_path, "rb") as f:
        client.storage.from_("clinic-files").upload(
            path          = dest_path,
            file          = f,
            file_options  = {"content-type": "application/pdf"}
        )

    # Get permanent public URL
    url = client.storage.from_("clinic-files").get_public_url(dest_path)

    # Clean up local temp file
    try:
        os.remove(local_path)
    except Exception:
        pass

    return url


def delete_pdf(public_url: str) -> None:
    """Delete a PDF from Supabase Storage by its public URL."""
    client = _get_client()

    # Extract path from URL
    # URL format: https://xxx.supabase.co/storage/v1/object/public/clinic-files/receipts/file.pdf
    parts = public_url.split("/clinic-files/")
    if len(parts) < 2:
        return

    file_path = parts[1]
    client.storage.from_("clinic-files").remove([file_path])