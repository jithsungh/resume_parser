"""
Utility functions for the API
"""
import os
import mimetypes
from pathlib import Path
from typing import Optional


def get_file_extension(filename: str) -> str:
    """Get file extension"""
    return Path(filename).suffix.lower()


def is_supported_file(filename: str) -> bool:
    """Check if file type is supported"""
    supported_extensions = ['.pdf', '.docx', '.doc', '.txt']
    return get_file_extension(filename) in supported_extensions


def format_file_size(size_bytes: int) -> str:
    """Format file size to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal"""
    return os.path.basename(filename)


def validate_file_size(file_size: int, max_size_mb: int = 10) -> bool:
    """Validate file size"""
    max_size_bytes = max_size_mb * 1024 * 1024
    return file_size <= max_size_bytes


def extract_filename_from_path(file_path: str) -> str:
    """Extract filename from path"""
    return Path(file_path).name


def get_mime_type(filename: str) -> Optional[str]:
    """Get MIME type of file"""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type
