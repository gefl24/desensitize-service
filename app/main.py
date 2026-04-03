import json
import uuid
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile, BackgroundTasks
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
DEFAULT_PROFILE = "light"

# 【优化 1】：使用 LRU 缓存避免每次请求重新加载规则和构建引擎树
@lru_cache(maxsize=4)
def build_dispatcher(profile: str = DEFAULT_PROFILE) -> FileDispatcher:
    logger.info(f"Initializing MaskingEngine for profile: {profile}")
    engine = MaskingEngine(CONFIG_DIR, profile=profile)
    return FileDispatcher(engine)

app = FastAPI(title="Document Desensitizer MVP", version="1.0.1")
templates = Jinja2Templates(directory=str(STATIC_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/v1/desensitize")
async def desensitize(
    background_tasks: BackgroundTasks, # 【优化 2】：引入后台任务
    file: UploadFile = File(...),
    profile: str = Query(DEFAULT_PROFILE, description="规则配置：light / strict"),
    _: bool = Depends(require_api_key),
):
    # 将清理任务放入后台执行，避免阻塞当前上传请求的响应
    background_tasks.add_task(cleanup_expired_files, UPLOAD_DIR, OUTPUT_DIR, ttl_hours=24)

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
        # 这里的 build_dispatcher 会直接命中缓存，速度极快
        current_dispatcher = build_dispatcher(profile=profile)
        masked_file_path, details = current_dispatcher.dispatch(input_path, output_path)
        
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

    hit_summary = {}
    for detail in details:
        hit_summary[detail.rule_type] = hit_summary.get(detail.rule_type, 0) + 1

    return JSONResponse({
        "task_id": task_id,
        "status": "success",
        "profile": profile,
        "output_file": f"/api/v1/files/{masked_file_path.name}",
        "report_file": f"/api/v1/reports/{report_path.name}",
        "bundle_file": f"/api/v1/bundles/{zip_path.name}",
        "download_bundle_api": f"/api/v1/desensitize/download/{task_id}",
        "total_hits": len(details),
        "hit_summary": hit_summary,
        "details": [detail.model_dump() if hasattr(detail, "model_dump") else detail.dict() for detail in details],
    })

# ... （以下下载接口代码保持不变）...
