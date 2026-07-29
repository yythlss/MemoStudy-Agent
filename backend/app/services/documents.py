from io import BytesIO

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader


async def extract_upload(file: UploadFile) -> tuple[str, str]:
    data = await file.read()
    filename = file.filename or "未命名资料"
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else "txt"
    if suffix == "pdf":
        try:
            reader = PdfReader(BytesIO(data))
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="PDF 解析失败") from exc
    elif suffix in {"txt", "md", "markdown", "csv", "json"}:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = data.decode("gb18030", errors="replace")
    else:
        raise HTTPException(status_code=400, detail="当前支持 PDF、TXT、Markdown、CSV 和 JSON")
    if not text.strip():
        raise HTTPException(status_code=400, detail="没有从文件中读取到文本")
    return filename, text

