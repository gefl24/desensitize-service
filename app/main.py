import json
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import FileDispatcher
from app.engine.masker import MaskingEngine
from app.models.report import Report
from app.utils.archive import build_result_zip
from app.utils.auth import require_api_key
from app.utils.file_guard import MAX_FILE_SIZE, is_allowed_filename, resolve_writable_dir, safe_suffix
from app.utils.cleanup import cleanup_expired_files, ensure_dir
from app.utils.logger import get_logger
from app.utils.mime_guard import validate_file_signature

BASE_DIR = Path("/app") if Path("/app").exists() else Path(__file__).resolve().parents[1]
UPLOAD_DIR = resolve_writable_dir(BASE_DIR / "uploads", "uploads")
OUTPUT_DIR = resolve_writable_dir(BASE_DIR / "outputs", "outputs")
LOG_DIR = resolve_writable_dir(BASE_DIR / "logs", "logs")
CONFIG_DIR = BASE_DIR / "config"
STATIC_DIR = Path(__file__).resolve().parent / "static"

for directory in (UPLOAD_DIR, OUTPUT_DIR, LOG_DIR, CONFIG_DIR):
    ensure_dir(directory)

logger = get_logger(LOG_DIR)
engine = MaskingEngine(CONFIG_DIR)
dispatcher = FileDispatcher(engine)

app = FastAPI(title="Document Desensitizer MVP", version="1.0.0")
templates = Jinja2Templates(directory=str(STATIC_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/v1/desensitize")
async def desensitize(file: UploadFile = File(...), _: bool = Depends(require_api_key)):
    cleanup_expired_files(UPLOAD_DIR, OUTPUT_DIR, ttl_hours=24)

    if not file.filename or not is_allowed_filename(file.filename):
        raise HTTPException(status_code=400, detail="unsupported file type")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="file too large")

    task_id = str(uuid.uuid4())
    suffix = safe_suffix(file.filename)
    input_path = UPLOAD_DIR / f"{task_id}{suffix}"
    output_path = OUTPUT_DIR / f"{task_id}_masked{suffix}"
    report_path = OUTPUT_DIR / f"{task_id}_report.json"
    zip_path = OUTPUT_DIR / f"{task_id}_bundle.zip"

    input_path.write_bytes(content)

    if not validate_file_signature(input_path):
        input_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="file signature validation failed")

    try:
        masked_file_path, details = dispatcher.dispatch(input_path, output_path)
        report = Report(
            task_id=task_id,
            original_file=file.filename,
            output_file=masked_file_path.name,
            status="success",
            total_hits=len(details),
            details=details,
        )
        report_payload = report.model_dump() if hasattr(report, "model_dump") else report.dict()
        report_path.write_text(json.dumps(report_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        build_result_zip(zip_path, masked_file_path, report_path)
        logger.info("desensitize success task_id=%s file=%s hits=%s", task_id, file.filename, len(details))
    except Exception as exc:
        logger.exception("desensitize failed task_id=%s file=%s", task_id, file.filename)
        raise HTTPException(status_code=500, detail=f"processing failed: {exc}") from exc

    return JSONResponse({
        "task_id": task_id,
        "status": "success",
        "output_file": f"/api/v1/files/{masked_file_path.name}",
        "report_file": f"/api/v1/reports/{report_path.name}",
        "bundle_file": f"/api/v1/bundles/{zip_path.name}",
        "download_bundle_api": f"/api/v1/desensitize/download/{task_id}",
        "total_hits": len(details),
    })


@app.get("/api/v1/files/{filename}")
def download_file(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path)


@app.get("/api/v1/reports/{filename}")
def download_report(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="report not found")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return JSONResponse(payload)


@app.get("/api/v1/bundles/{filename}")
def download_bundle(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="bundle not found")
    return FileResponse(path, media_type="application/zip", filename=filename)


@app.get("/api/v1/desensitize/download/{task_id}")
def download_bundle_by_task(task_id: str):
    path = OUTPUT_DIR / f"{task_id}_bundle.zip"
    if not path.exists():
        raise HTTPException(status_code=404, detail="bundle not found")
    return FileResponse(path, media_type="application/zip", filename=path.name)
