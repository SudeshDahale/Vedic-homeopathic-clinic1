import os
import uuid

from supabase import create_client

from app.config import settings


# =====================================================
# SUPABASE CLIENT
# =====================================================

client = create_client(

    settings.SUPABASE_URL,

    settings.SUPABASE_KEY
)


# =====================================================
# UPLOAD PDF
# =====================================================

def upload_pdf(
    local_path: str,
    folder: str = "receipts"
) -> str:

    # Generate unique filename
    filename = (
        f"{folder}_"
        f"{uuid.uuid4().hex[:8]}.pdf"
    )

    storage_path = (
        f"{folder}/{filename}"
    )

    # Read file
    with open(local_path, "rb") as f:

        file_data = f.read()

    # Upload to Supabase Storage
    client.storage.from_(

        "clinic-files"

    ).upload(

        path=storage_path,

        file=file_data,

        file_options={
            "content-type":
                "application/pdf"
        }
    )

    # Generate public URL
    public_url = client.storage.from_(

        "clinic-files"

    ).get_public_url(storage_path)

    # Delete local temp file
    if os.path.exists(local_path):

        os.remove(local_path)

    return public_url