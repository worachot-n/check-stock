import os

UPLOAD_BASE = os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads')

ALLOWED_REQUISITION = {'.pdf', '.png', '.jpg', '.jpeg'}
ALLOWED_IMAGE = {'.png', '.jpg', '.jpeg', '.webp'}


def save_file(file_obj, folder: str, seq_no: int) -> str | None:
    """Save an uploaded file to static/uploads/<folder>/ and return the filename."""
    if not file_obj or not file_obj.filename:
        return None

    ext = os.path.splitext(file_obj.filename)[1].lower()
    allowed = ALLOWED_REQUISITION if folder == 'requisitions' else ALLOWED_IMAGE
    if ext not in allowed:
        return None

    dest_dir = os.path.join(UPLOAD_BASE, folder)
    os.makedirs(dest_dir, exist_ok=True)

    prefix = 'req' if folder == 'requisitions' else 'item'
    filename = f'{prefix}_{seq_no}{ext}'
    file_obj.save(os.path.join(dest_dir, filename))
    return filename


def delete_file(filename: str, folder: str):
    """Delete an uploaded file if it exists."""
    if not filename:
        return
    path = os.path.join(UPLOAD_BASE, folder, filename)
    if os.path.exists(path):
        os.remove(path)


def file_url(filename: str, folder: str) -> str | None:
    if not filename:
        return None
    return f'/static/uploads/{folder}/{filename}'
