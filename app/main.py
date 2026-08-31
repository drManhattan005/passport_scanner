from typing import List

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.pipeline import extract_passport_info
from app.schemas import BatchResponse, FileResult

app = FastAPI(title="MRZ Passport Batch Extractor", version="0.1.0")
templates = Jinja2Templates(directory="app/templates")

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
MAX_FILES = 5


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"max_files": MAX_FILES},
    )


@app.post("/api/extract", response_model=BatchResponse)
async def extract_batch(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Please upload at least one image.")

    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"You can upload up to {MAX_FILES} passport images at once.",
        )

    results: list[FileResult] = []

    for file in files:
        filename = file.filename or "unknown"

        try:
            if file.content_type not in ALLOWED_TYPES:
                results.append(
                    FileResult(
                        filename=filename,
                        status="failed",
                        error=f"Unsupported file type: {file.content_type}",
                        data=None,
                    )
                )
                continue

            content = await file.read()
            if not content:
                results.append(
                    FileResult(
                        filename=filename,
                        status="failed",
                        error="Empty file uploaded",
                        data=None,
                    )
                )
                continue

            extracted = extract_passport_info(content=content, filename=filename)

            results.append(
                FileResult(
                    filename=filename,
                    status="success",
                    error=None,
                    data=extracted,
                )
            )

        except Exception as exc:
            results.append(
                FileResult(
                    filename=filename,
                    status="failed",
                    error=str(exc),
                    data=None,
                )
            )

    return BatchResponse(
        total_uploaded=len(files),
        total_processed=len(results),
        results=results,
    )
