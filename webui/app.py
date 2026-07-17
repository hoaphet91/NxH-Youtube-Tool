"""
WEB UI cho pipeline sinh video tự động — điều khiển/chạy từ xa qua trình
duyệt (máy tính hoặc điện thoại).

QUAN TRỌNG: File này KHÔNG sửa đổi bất kỳ module nào trong modules/ hay
main.py của pipeline gốc. Nó chỉ bao bọc bên ngoài, gọi main.py bằng
subprocess (giống hệt cách chạy tay "python main.py --script ..."), rồi:
  - Quản lý ảnh/video/audio đầu vào qua upload (ghi vào đúng thư mục
    config.INPUT_IMAGES_DIR / INPUT_VIDEOS_DIR / LOCAL_AUDIO_DIR)
  - Sửa cấu hình runtime qua form web, ghi thẳng vào file .env
  - Nhận kịch bản qua textarea hoặc upload file .txt/.md
  - Stream log thời gian thực qua WebSocket trong lúc pipeline chạy
  - Liệt kê + tải kết quả (video/srt/report) sau khi xong

Chạy:
    pip install -r webui/requirements_web.txt
    python -m uvicorn webui.app:app --host 0.0.0.0 --port 8000

Truy cập từ điện thoại (cùng Wi-Fi với máy chạy server):
    http://<địa-chỉ-IP-LAN-của-máy-tính>:8000
"""
import os
import re
import sys
import json
import secrets
import asyncio
import datetime
from pathlib import Path
from typing import Optional

from fastapi import (
    FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form,
    Request, HTTPException,
)
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import TimestampSigner, BadSignature

# ============================================================
# VÁ LỖI NHIỄU LOG TRÊN WINDOWS: ConnectionResetError (WinError 10054) từ
# asyncio ProactorEventLoop khi trình duyệt đóng tab / mất kết nối WebSocket
# đột ngột (hoặc reset kết nối HTTP keep-alive). Đây LÀ HÀNH VI BÌNH THƯỜNG
# (client đóng kết nối trước khi server kịp dọn dẹp), KHÔNG PHẢI LỖI THẬT --
# nhưng _ProactorBasePipeTransport._call_connection_lost gọi socket.shutdown()
# trên socket đã bị phía kia đóng, ném ConnectionResetError ra ngoài callback
# của event loop -> in traceback gây nhiễu console dù không ảnh hưởng chức
# năng nào (job vẫn chạy bình thường, WebSocket khác vẫn hoạt động). KHÔNG
# đổi sang SelectorEventLoop vì asyncio.create_subprocess_exec (dùng để chạy
# main.py, xem _run_job) CHỈ được hỗ trợ trên ProactorEventLoop ở Windows.
if sys.platform == "win32":
    from asyncio.proactor_events import _ProactorBasePipeTransport

    _orig_call_connection_lost = _ProactorBasePipeTransport._call_connection_lost

    def _silent_call_connection_lost(self, exc):
        try:
            _orig_call_connection_lost(self, exc)
        except ConnectionResetError:
            pass  # Client đã đóng kết nối trước -- bỏ qua, không phải lỗi cần xử lý.

    _ProactorBasePipeTransport._call_connection_lost = _silent_call_connection_lost

# ============================================================
# ĐƯỜNG DẪN
# ============================================================
WEBUI_DIR = Path(__file__).resolve().parent
BASE_DIR = WEBUI_DIR.parent  # thư mục gốc project, nơi có main.py/config.py
STATIC_DIR = WEBUI_DIR / "static"
DATA_DIR = WEBUI_DIR / "data"
SCRIPT_PATH = DATA_DIR / "current_script.txt"
JOBS_FILE = DATA_DIR / "jobs_history.json"
ENV_PATH = BASE_DIR / ".env"

DATA_DIR.mkdir(parents=True, exist_ok=True)

INPUT_IMAGES_DIR = BASE_DIR / "input_images"
INPUT_VIDEOS_DIR = BASE_DIR / "input_videos"
INPUT_AUDIO_DIR = BASE_DIR / "input_audio"
OUTPUT_DIR = BASE_DIR / "output"
for _d in (INPUT_IMAGES_DIR, INPUT_VIDEOS_DIR, INPUT_AUDIO_DIR, OUTPUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}

app = FastAPI(title="Pipeline Sinh Video — Web UI")

# ============================================================
# ĐĂNG NHẬP (mật khẩu WEBUI_PASSWORD đặt trong .env, mục Cấu hình)
# ============================================================
# SECRET_KEY random mỗi lần khởi động server -> restart server sẽ đăng xuất
# mọi phiên cũ (chấp nhận được, vì đây không phải hệ thống nhiều người dùng).
_SECRET_KEY = secrets.token_hex(32)
_signer = TimestampSigner(_SECRET_KEY)
COOKIE_NAME = "webui_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 ngày
PUBLIC_PATHS = {"/login", "/api/login", "/favicon.ico"}


def read_env() -> dict:
    """Đọc toàn bộ key=value trong .env (bỏ qua comment/dòng trống)."""
    result = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            result[k.strip()] = v.strip()
    return result


def write_env(updates: dict) -> None:
    """Ghi đè các key có trong 'updates' vào .env, GIỮ NGUYÊN comment/format
    của các dòng khác. Key chưa tồn tại sẽ được thêm mới ở cuối file."""
    lines = []
    seen = set()
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            core = line.strip()
            if core and not core.startswith("#") and "=" in core:
                key = core.split("=", 1)[0].strip()
                if key in updates:
                    lines.append(f"{key}={updates[key]}")
                    seen.add(key)
                    continue
            lines.append(line)
    for k, v in updates.items():
        if k not in seen:
            lines.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _get_password() -> str:
    return read_env().get("WEBUI_PASSWORD", "")


def _valid_cookie_value(cookie: Optional[str]) -> bool:
    if not cookie:
        return False
    try:
        _signer.unsign(cookie, max_age=COOKIE_MAX_AGE)
        return True
    except BadSignature:
        return False


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if path in PUBLIC_PATHS or path.startswith("/static/"):
        return await call_next(request)
    password = _get_password()
    if not password:
        # Chưa đặt mật khẩu trong Cấu hình -> bỏ qua xác thực. CHỈ AN TOÀN
        # trong mạng nội bộ tin cậy (Wi-Fi nhà riêng). Nếu mở ra Internet
        # (Tailscale/Cloudflare Tunnel...), BẮT BUỘC đặt WEBUI_PASSWORD trước.
        return await call_next(request)
    if not _valid_cookie_value(request.cookies.get(COOKIE_NAME)):
        if path.startswith("/api/") or path.startswith("/ws"):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return RedirectResponse("/login")
    return await call_next(request)


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return (STATIC_DIR / "login.html").read_text(encoding="utf-8")


@app.post("/api/login")
async def do_login(payload: dict):
    password = str(payload.get("password", ""))
    real = _get_password()
    if not real or password != real:
        raise HTTPException(401, "Sai mật khẩu.")
    token = _signer.sign(secrets.token_hex(16).encode()).decode()
    resp = JSONResponse({"ok": True})
    resp.set_cookie(COOKIE_NAME, token, max_age=COOKIE_MAX_AGE, httponly=True, samesite="lax")
    return resp


@app.post("/api/logout")
async def do_logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE_NAME)
    return resp


@app.get("/api/auth/status")
async def auth_status(request: Request):
    password_set = bool(_get_password())
    logged_in = (not password_set) or _valid_cookie_value(request.cookies.get(COOKIE_NAME))
    return {"password_set": password_set, "logged_in": logged_in}


# ============================================================
# TRANG CHÍNH + STATIC
# ============================================================
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


# ============================================================
# CẤU HÌNH (.env)
# ============================================================
@app.get("/api/config")
async def get_config():
    return read_env()


@app.post("/api/config")
async def update_config(payload: dict):
    clean = {str(k): str(v) for k, v in payload.items() if k}
    write_env(clean)
    return {"ok": True}


# ============================================================
# KỊCH BẢN (textarea hoặc upload .txt/.md)
# ============================================================
_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*\n(.*?)\n```\s*$", re.DOTALL)


def _extract_script_text(raw: str) -> str:
    """Nếu người dùng upload nguyên văn 1 khối Markdown code-fence (đúng định
    dạng Phase 7 Export của skill viết kịch bản), tự động bóc phần script bên
    trong ra, bỏ dòng tiêu đề dạng '--- ten-file.txt ---' nếu có."""
    text = raw.strip()
    m = _FENCE_RE.match(text)
    if not m:
        return text
    inner = m.group(1)
    lines = inner.split("\n")
    if lines and lines[0].strip().startswith("---") and lines[0].strip().endswith("---"):
        inner = "\n".join(lines[1:])
    return inner.strip()


@app.get("/api/script")
async def get_script():
    if SCRIPT_PATH.exists():
        return {"content": SCRIPT_PATH.read_text(encoding="utf-8")}
    return {"content": ""}


@app.post("/api/script")
async def save_script_text(payload: dict):
    content = str(payload.get("content", ""))
    if not content.strip():
        raise HTTPException(400, "Nội dung kịch bản đang trống.")
    SCRIPT_PATH.write_text(content, encoding="utf-8")
    return {"ok": True}


@app.post("/api/script/upload")
async def upload_script_file(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".txt", ".md"):
        raise HTTPException(400, "Chỉ chấp nhận file .txt hoặc .md")
    raw = (await file.read()).decode("utf-8", errors="replace")
    content = _extract_script_text(raw)
    if not content.strip():
        raise HTTPException(400, "File tải lên rỗng sau khi xử lý.")
    SCRIPT_PATH.write_text(content, encoding="utf-8")
    return {"content": content}


# ============================================================
# ẢNH / VIDEO / AUDIO ĐẦU VÀO
# ============================================================
async def _save_ordered(files: list[UploadFile], target_dir: Path, valid_ext: set[str],
                         clear_existing: bool) -> list[str]:
    """Lưu file THEO ĐÚNG THỨ TỰ xuất hiện trong 'files' — quan trọng vì
    modules/image_sync.py (và audio tương ứng) sắp xếp lại theo THỜI GIAN
    TẠO FILE. Ghi TUẦN TỰ (không song song) + chờ 1 khoảng ngắn giữa mỗi file
    để đảm bảo timestamp tăng dần rõ ràng trên mọi hệ điều hành/hệ tập tin."""
    if clear_existing:
        for f in target_dir.iterdir():
            if f.is_file():
                f.unlink()
    saved = []
    for idx, uf in enumerate(files):
        ext = Path(uf.filename or "").suffix.lower()
        if valid_ext and ext not in valid_ext:
            continue
        dest = target_dir / f"upload_{idx:04d}{ext}"
        content = await uf.read()
        dest.write_bytes(content)
        saved.append(dest.name)
        # asyncio.sleep (KHÔNG PHẢI time.sleep) -- time.sleep chặn cứng toàn
        # bộ event loop, làm đứng WebSocket log của job khác đang chạy song
        # song trong lúc upload nhiều ảnh.
        await asyncio.sleep(0.15)
    return saved


@app.get("/api/images")
async def list_images():
    files = sorted((f for f in INPUT_IMAGES_DIR.iterdir() if f.is_file()), key=lambda p: p.stat().st_mtime)
    return {"files": [f.name for f in files]}


@app.post("/api/images")
async def upload_images(files: list[UploadFile] = File(...), clear_existing: bool = Form(True)):
    saved = await _save_ordered(files, INPUT_IMAGES_DIR, IMAGE_EXTENSIONS, clear_existing)
    return {"saved": saved, "count": len(saved)}


@app.delete("/api/images")
async def clear_images():
    for f in INPUT_IMAGES_DIR.iterdir():
        if f.is_file():
            f.unlink()
    return {"ok": True}


@app.get("/api/audio")
async def list_audio():
    files = sorted((f for f in INPUT_AUDIO_DIR.iterdir() if f.is_file()), key=lambda p: p.stat().st_mtime)
    return {"files": [f.name for f in files]}


@app.post("/api/audio")
async def upload_audio(files: list[UploadFile] = File(...), clear_existing: bool = Form(True)):
    saved = await _save_ordered(files, INPUT_AUDIO_DIR, AUDIO_EXTENSIONS, clear_existing)
    return {"saved": saved, "count": len(saved)}


@app.delete("/api/audio")
async def clear_audio():
    for f in INPUT_AUDIO_DIR.iterdir():
        if f.is_file():
            f.unlink()
    return {"ok": True}


@app.get("/api/videos")
async def list_videos():
    return {"files": sorted(f.name for f in INPUT_VIDEOS_DIR.iterdir() if f.is_file())}


@app.post("/api/videos")
async def upload_videos(files: list[UploadFile] = File(...)):
    saved = []
    for uf in files:
        name = Path(uf.filename or "unnamed").name  # chống path traversal
        dest = INPUT_VIDEOS_DIR / name
        dest.write_bytes(await uf.read())
        saved.append(name)
    return {"saved": saved}


@app.delete("/api/videos/{filename}")
async def delete_video(filename: str):
    target = INPUT_VIDEOS_DIR / Path(filename).name
    if target.exists():
        target.unlink()
    return {"ok": True}


# ============================================================
# CHẠY PIPELINE (subprocess main.py) + LOG REAL-TIME QUA WEBSOCKET
# ============================================================
class JobState:
    def __init__(self):
        self.running = False
        self.status = "idle"  # idle | running | success | error
        self.title: Optional[str] = None
        self.output_name: Optional[str] = None
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None
        self.log_lines: list[str] = []
        self.process: Optional[asyncio.subprocess.Process] = None
        self.websockets: list[WebSocket] = []


job = JobState()


async def _broadcast(line: str) -> None:
    job.log_lines.append(line)
    job.log_lines = job.log_lines[-2000:]  # giới hạn bộ nhớ log
    dead = []
    for ws in job.websockets:
        try:
            await ws.send_text(line)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in job.websockets:
            job.websockets.remove(ws)


def _load_history() -> list[dict]:
    if JOBS_FILE.exists():
        try:
            return json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_history_entry() -> None:
    history = _load_history()
    history.insert(0, {
        "title": job.title,
        "output_name": job.output_name,
        "status": job.status,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    })
    JOBS_FILE.write_text(json.dumps(history[:50], ensure_ascii=False, indent=2), encoding="utf-8")


async def _run_job(title: str, output_name: str) -> None:
    job.running = True
    job.status = "running"
    job.started_at = datetime.datetime.now().isoformat()
    job.finished_at = None
    job.title = title
    job.output_name = output_name
    job.log_lines = []
    await _broadcast(f"=== BẮT ĐẦU: {title} ===")

    if not SCRIPT_PATH.exists() or not SCRIPT_PATH.read_text(encoding="utf-8").strip():
        job.status = "error"
        job.running = False
        await _broadcast("[LỖI] Chưa có kịch bản. Vào tab Kịch bản để nhập/upload trước khi chạy.")
        _save_history_entry()
        return

    cmd = [sys.executable, "-u", str(BASE_DIR / "main.py"),
           "--script", str(SCRIPT_PATH), "--title", title, "--output", output_name]
    # Ép subprocess con dùng UTF-8 cho stdout/stderr, bất kể codepage console
    # Windows là gì -- phòng vệ lớp 2 bên cạnh reconfigure() đã thêm trong
    # chính main.py (xem nhật ký PROJECT_MEMORY.md [2026-07-13] "Sửa
    # UnicodeEncodeError log tiếng Việt trên Windows"). Không set 2 biến này
    # thì trên 1 số máy Windows, tiến trình con vẫn có thể dùng codepage
    # cp1252 mặc định của hệ điều hành cho I/O, không phải UTF-8.
    run_env = os.environ.copy()
    run_env["PYTHONIOENCODING"] = "utf-8"
    run_env["PYTHONUTF8"] = "1"
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, cwd=str(BASE_DIR), env=run_env,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        job.process = process
        assert process.stdout is not None
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            await _broadcast(line.decode("utf-8", errors="replace").rstrip("\n"))
        returncode = await process.wait()
        job.status = "success" if returncode == 0 else "error"
        await _broadcast(f"=== KẾT THÚC (mã thoát: {returncode}) ===")
    except Exception as e:
        job.status = "error"
        await _broadcast(f"[LỖI] Không chạy được pipeline: {e}")
    finally:
        job.running = False
        job.process = None
        job.finished_at = datetime.datetime.now().isoformat()
        _save_history_entry()


@app.post("/api/run")
async def start_run(payload: dict):
    if job.running:
        raise HTTPException(409, "Đang có 1 tiến trình chạy, vui lòng đợi hoàn tất hoặc huỷ trước.")
    title = str(payload.get("title", "")).strip()
    output_name = str(payload.get("output_name", "")).strip() or "final_video.mp4"
    if not title:
        raise HTTPException(400, "Thiếu tiêu đề video.")
    if not output_name.lower().endswith(".mp4"):
        output_name += ".mp4"
    asyncio.create_task(_run_job(title, output_name))
    return {"ok": True}


@app.post("/api/run/cancel")
async def cancel_run():
    if job.process and job.running:
        job.process.terminate()
        await _broadcast("[HUỶ] Người dùng yêu cầu dừng tiến trình. (Có thể mất vài giây để dừng hẳn.)")
        return {"ok": True}
    return {"ok": False, "message": "Không có tiến trình nào đang chạy."}


@app.get("/api/run/status")
async def run_status():
    return {
        "running": job.running,
        "status": job.status,
        "title": job.title,
        "output_name": job.output_name,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


@app.get("/api/history")
async def get_history():
    return {"jobs": _load_history()}


@app.websocket("/ws/log")
async def ws_log(websocket: WebSocket):
    password = _get_password()
    if password and not _valid_cookie_value(websocket.cookies.get(COOKIE_NAME)):
        await websocket.close(code=4401)
        return
    await websocket.accept()
    for line in job.log_lines:
        await websocket.send_text(line)
    job.websockets.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in job.websockets:
            job.websockets.remove(websocket)


# ============================================================
# KẾT QUẢ (output/)
# ============================================================
@app.get("/api/outputs")
async def list_outputs():
    files = []
    for f in OUTPUT_DIR.iterdir():
        if f.is_file():
            files.append({"name": f.name, "size": f.stat().st_size, "mtime": f.stat().st_mtime})
    files.sort(key=lambda x: x["mtime"], reverse=True)
    return {"files": files}


@app.get("/api/outputs/{filename}")
async def download_output(filename: str, request: Request):
    target = OUTPUT_DIR / Path(filename).name
    if not target.exists():
        raise HTTPException(404, "Không tìm thấy file.")
    return FileResponse(target, filename=target.name)


@app.delete("/api/outputs/{filename}")
async def delete_output(filename: str):
    target = OUTPUT_DIR / Path(filename).name
    if target.exists():
        target.unlink()
    return {"ok": True}
