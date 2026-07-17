import os
import sys


def _enable_vt_processing_on_windows() -> bool:
    if os.name != "nt":
        return True
    if not sys.stdout.isatty():
        return False
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            return bool(kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING))
    except Exception:
        return False
    return False


USE_ANSI = sys.stdout.isatty() and _enable_vt_processing_on_windows()
RESET = "\x1b[0m" if USE_ANSI else ""
BOLD = "\x1b[1m" if USE_ANSI else ""
DIM = "\x1b[2m" if USE_ANSI else ""
FG_CYAN = "\x1b[96m" if USE_ANSI else ""
FG_BLUE = "\x1b[94m" if USE_ANSI else ""
FG_GREEN = "\x1b[92m" if USE_ANSI else ""
FG_MAGENTA = "\x1b[95m" if USE_ANSI else ""
FG_YELLOW = "\x1b[93m" if USE_ANSI else ""
FG_WHITE = "\x1b[97m" if USE_ANSI else ""
FG_GREY = "\x1b[90m" if USE_ANSI else ""


def _color(text: str, color_code: str) -> str:
    return f"{color_code}{text}{RESET}" if USE_ANSI else text


def progress_bar(percent: int, width: int = 30) -> str:
    filled = max(0, min(width, int(width * percent / 100)))
    empty = width - filled
    if USE_ANSI:
        return f"{FG_CYAN}{'█' * filled}{RESET}{FG_GREY}{'░' * empty}{RESET}"
    return "#" * filled + "-" * empty


def progress_line(tag: str, done: int, total: int, label: str,
                  extra: str | None = None, width: int = 32) -> str:
    percent = int(done / max(total, 1) * 100)
    bar = progress_bar(percent, width=width)
    tag_text = _color(tag, BOLD + FG_WHITE) if USE_ANSI else tag
    percent_text = _color(f"{percent:3d}%", BOLD + FG_GREEN) if USE_ANSI else f"{percent:3d}%"
    extra_text = f" | {extra}" if extra else ""
    return f"\r[{tag_text}] {bar} {percent_text} | {label}{extra_text}"


def write_progress(tag: str, done: int, total: int, label: str,
                   extra: str | None = None, width: int = 32) -> None:
    line = progress_line(tag, done, total, label, extra, width)
    if USE_ANSI:
        line += "\x1b[K"
    sys.stdout.write(line)
    sys.stdout.flush()
