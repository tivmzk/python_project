"""
일본어 게임 번역기 (GUI 버전)
- 영역 설정 버튼 → 드래그로 캡처 영역 선택 → 화면에 테두리로 표시
- 번역 실행 버튼 → OCR → 파파고 번역 → 팝업 표시
"""

import asyncio
import threading
import queue
import tkinter as tk
import pyperclip
import winocr
from PIL import ImageGrab, Image
import json
import os
import time
from playwright.sync_api import sync_playwright, Page, Browser, Playwright

# ── 설정 파일 경로 ──────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "translator_config.json")

# ── 전역 상태 ───────────────────────────────────────────────
capture_region = None       # (x1, y1, x2, y2)
is_translating  = False

# ── 브라우저 전용 워커 ──────────────────────────────────────
# Playwright sync 객체는 생성한 스레드에서만 사용 가능.
# 모든 Playwright 작업(초기화·번역·종료)을 하나의 전용 스레드에서 처리한다.
_browser_queue:  queue.Queue = queue.Queue()
_browser_thread: threading.Thread = None

# ── GUI 전역 참조 ───────────────────────────────────────────
_root:    tk.Tk       = None
_overlay: tk.Toplevel = None   # 캡처 영역 테두리 오버레이

# ── GUI 위젯 참조 ───────────────────────────────────────────
_region_label:  tk.Label  = None
_status_label:  tk.Label  = None
_translate_btn: tk.Button = None
_result_popup:  object    = None   # 현재 열린 번역 결과 창 (단일 인스턴스)


# ══════════════════════════════════════════════════════════════
# 설정 저장/불러오기
# ══════════════════════════════════════════════════════════════

def load_config():
    global capture_region
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                region = data.get("capture_region")
                if region and len(region) == 4:
                    capture_region = tuple(region)
        except Exception:
            pass

def save_config():
    data = {"capture_region": list(capture_region) if capture_region else None}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════
# 브라우저 전용 워커 스레드
# ══════════════════════════════════════════════════════════════

def _browser_worker():
    """
    Playwright 전용 스레드.
    - 시작 시 브라우저 초기화
    - 큐에서 번역 요청을 받아 처리
    - None(센티넬)을 받으면 브라우저 정리 후 종료
    """
    playwright = browser = page = None

    # ── 초기화 ───────────────────────────────────────────────
    try:
        playwright = sync_playwright().start()
        # 빌드 환경에서는 Playwright 번들 Chromium이 없으므로
        # 시스템에 설치된 Chrome → Edge 순으로 fallback 시도
        browser = None
        for channel in ("chrome", "msedge"):
            try:
                browser = playwright.chromium.launch(
                    channel=channel,
                    headless=False,
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                print(f"  ✅ {channel} 브라우저 사용")
                break
            except Exception:
                continue
        if browser is None:
            raise RuntimeError(
                "Chrome 또는 Edge가 설치되어 있지 않습니다.\n"
                "https://www.google.com/chrome 에서 Chrome을 설치해 주세요."
            )
        page = browser.new_page()
        page.goto("https://papago.naver.com/?sk=ja&tk=ko",
                  wait_until="domcontentloaded", timeout=20000)
        print("  ✅ 브라우저 준비 완료")
        if _root:
            _root.after(0, lambda: update_status_label("브라우저 준비 완료"))
    except Exception as e:
        print(f"  ❌ 브라우저 초기화 실패: {e}")
        if _root:
            _root.after(0, lambda: update_status_label(f"브라우저 초기화 실패: {e}"))

    # ── 요청 처리 루프 ────────────────────────────────────────
    while True:
        item = _browser_queue.get()

        # 종료 센티넬
        if item is None:
            break

        text, result_box, done_event = item
        try:
            # 페이지 살아있는지 확인, 죽었으면 재시작
            if page is None or page.is_closed():
                print("  🔄 브라우저 재시작 중...")
                try:
                    if page:    page.close()
                    if browser: browser.close()
                except Exception:
                    pass
                browser = None
                for channel in ("chrome", "msedge"):
                    try:
                        browser = playwright.chromium.launch(
                            channel=channel,
                            headless=False,
                            args=["--no-sandbox", "--disable-dev-shm-usage"]
                        )
                        break
                    except Exception:
                        continue
                if browser is None:
                    raise RuntimeError("Chrome 또는 Edge를 찾을 수 없습니다")
                page = browser.new_page()
                page.goto("https://papago.naver.com/?sk=ja&tk=ko",
                          wait_until="domcontentloaded", timeout=20000)

            # 파파고 홈이 아닌 경우에만 이동
            if "papago.naver.com" not in page.url:
                page.goto("https://papago.naver.com/?sk=ja&tk=ko",
                          wait_until="domcontentloaded", timeout=20000)

            # 입력창에 직접 텍스트 입력 (URL 파라미터 방식은 봇 감지에 취약)
            page.wait_for_selector("#txtSource", timeout=10000)
            page.click("#txtSource")
            # 기존 내용 전체 선택 후 교체
            page.evaluate("document.querySelector('#txtSource').value = ''")
            page.fill("#txtSource", text)

            # 번역 결과 대기
            page.wait_for_selector("#txtTarget", timeout=10000)
            time.sleep(2)

            el = page.query_selector("#txtTarget")
            if el:
                translated = el.inner_text().strip()
                if translated:
                    result_box[0] = translated
                    done_event.set()
                    continue

            result_box[0] = "번역 결과를 가져오지 못했습니다"

        except Exception as e:
            result_box[0] = f"번역 오류: {str(e)}"

        done_event.set()

    # ── 정리 (종료 센티넬 받은 후) ───────────────────────────
    print("  🔄 브라우저 종료 중...")
    try:
        if page:       page.close()
        if browser:    browser.close()
        if playwright: playwright.stop()
    except Exception as e:
        print(f"  ⚠ 브라우저 정리 중 오류(무시): {e}")
    print("  ✅ 브라우저 종료 완료")


def translate_via_queue(text: str) -> str:
    """
    번역 요청을 브라우저 워커 큐에 넣고 결과를 기다린다.
    호출은 메인 스레드가 아닌 번역 워커 스레드에서 이루어진다.
    """
    result_box = [None]
    done_event = threading.Event()
    _browser_queue.put((text, result_box, done_event))
    done_event.wait(timeout=30)
    return result_box[0] or "번역 시간 초과"


# ══════════════════════════════════════════════════════════════
# 캡처 영역 오버레이 (항상-위 테두리 창)
# ══════════════════════════════════════════════════════════════

def show_region_overlay(region: tuple):
    global _overlay
    hide_region_overlay()

    x1, y1, x2, y2 = region
    w = x2 - x1
    h = y2 - y1
    border  = 3
    label_h = 20

    _overlay = tk.Toplevel(_root)
    _overlay.overrideredirect(True)
    _overlay.attributes("-topmost", True)
    _overlay.attributes("-alpha", 0.85)
    _overlay.wm_attributes("-transparentcolor", "#010101")
    _overlay.geometry(f"{w}x{h + label_h}+{x1}+{y1 - label_h}")

    canvas = tk.Canvas(_overlay, bg="#010101", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    canvas.create_rectangle(
        0, label_h, w - 1, h + label_h - 1,
        outline="#00FF88", width=border, fill="#010101"
    )
    canvas.create_rectangle(0, 0, w - 1, label_h, fill="#00FF88", outline="")
    canvas.create_text(
        w // 2, label_h // 2,
        text=f"캡처 영역  {w}×{h}",
        fill="#1a1a2e", font=("Malgun Gothic", 8, "bold")
    )

def hide_region_overlay():
    global _overlay
    if _overlay:
        try:
            _overlay.destroy()
        except Exception:
            pass
        _overlay = None

def _withdraw_overlay():
    if _overlay:
        try: _overlay.withdraw()
        except Exception: pass

def _deiconify_overlay():
    if _overlay:
        try: _overlay.deiconify()
        except Exception: pass


# ══════════════════════════════════════════════════════════════
# 영역 선택 UI
# ══════════════════════════════════════════════════════════════

class RegionSelector:
    def __init__(self):
        self.result = None
        self.start_x = self.start_y = 0
        self.rect_id = None

        self.win = tk.Toplevel(_root)
        self.win.attributes("-fullscreen", True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.4)
        self.win.config(cursor="crosshair", bg="black")

        tk.Label(
            self.win,
            text="드래그하여 캡처 영역을 선택하세요  |  ESC: 취소",
            font=("Malgun Gothic", 14, "bold"),
            fg="white", bg="black",
        ).place(relx=0.5, rely=0.05, anchor="center")

        self.canvas = tk.Canvas(self.win, cursor="crosshair",
                                bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>",   self._on_press)
        self.canvas.bind("<B1-Motion>",        self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.win.bind("<Escape>", lambda e: self.win.destroy())

    def _on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)

    def _on_drag(self, event):
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline="#00FF88", width=2, fill="#00FF88", stipple="gray25"
        )

    def _on_release(self, event):
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)
        if x2 - x1 > 10 and y2 - y1 > 10:
            self.result = (x1, y1, x2, y2)
        self.win.destroy()

    def select(self):
        _root.wait_window(self.win)
        return self.result


def select_region():
    global capture_region
    selector = RegionSelector()
    region = selector.select()
    if region:
        capture_region = region
        save_config()
        show_region_overlay(region)
        update_region_label()
        show_toast(f"영역 설정 완료  ({region[0]}, {region[1]}) → ({region[2]}, {region[3]})")
    else:
        show_toast("영역 선택이 취소되었습니다")


# ══════════════════════════════════════════════════════════════
# OCR
# ══════════════════════════════════════════════════════════════

async def do_ocr(image: Image.Image) -> str:
    result = await winocr.recognize_pil(image, "ja")
    return result.text

def clean_text(text: str) -> str:
    import re
    text = text.replace("\n", "").replace("\r", "")
    # 일본어(히라가나·가타카나·한자·전각문자) 사이의 공백 제거
    text = re.sub(r'(?<=[　-鿿＀-￯])\s+(?=[　-鿿＀-￯])', '', text)
    return text.strip()


# ══════════════════════════════════════════════════════════════
# 팝업 결과 창
# ══════════════════════════════════════════════════════════════

class ResultPopup:
    """번역 결과 창 — 단일 인스턴스로 재사용 (update로 내용 교체)"""

    def __init__(self):
        global _result_popup
        self.win = tk.Toplevel(_root)
        self.win.title("번역 결과")
        self.win.attributes("-topmost", True)
        self.win.resizable(True, True)
        self.win.configure(bg="#1a1a2e")

        # 창 크기: 캡처 영역 기준, 최소 480×320
        if capture_region:
            x1, y1, x2, y2 = capture_region
            w = max(x2 - x1, 480)
            h = max(y2 - y1, 320)
        else:
            w, h = 480, 320

        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        px = min(sw - w - 20, sw - w)
        py = sh - h - 80
        self.win.geometry(f"{w}x{h}+{px}+{py}")
        self.win.minsize(480, 320)

        self._build_skeleton()
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)
        _result_popup = self

    def _on_close(self):
        global _result_popup
        _result_popup = None
        self.win.destroy()

    def _build_skeleton(self):
        """위젯 골격 생성 — grid로 행 비율을 명확히 분배"""
        self.win.columnconfigure(0, weight=1)
        # 행 구성: 헤더(고정) / 번역(확장) / 구분선(고정) / 원문(고정) / 버튼(고정)
        self.win.rowconfigure(0, weight=0)  # 헤더
        self.win.rowconfigure(1, weight=1)  # 번역 결과 — 남은 공간 전부
        self.win.rowconfigure(2, weight=0)  # 구분선
        self.win.rowconfigure(3, weight=0)  # 원문
        self.win.rowconfigure(4, weight=0)  # 버튼

        # ── 헤더 ─────────────────────────────────────────────────
        header = tk.Frame(self.win, bg="#16213e", pady=8)
        header.grid(row=0, column=0, sticky="ew")
        tk.Label(header, text="🎌 일본어 번역기",
                 font=("Malgun Gothic", 11, "bold"),
                 fg="#e94560", bg="#16213e").pack(side="left", padx=12)
        tk.Button(header, text="✕", command=self._on_close,
                  font=("Arial", 10, "bold"), fg="#888", bg="#16213e",
                  relief="flat", cursor="hand2", bd=0,
                  activeforeground="white", activebackground="#16213e"
                  ).pack(side="right", padx=8)

        # ── 번역 결과 (한국어) — 확장 영역 ──────────────────────
        trans_frame = tk.Frame(self.win, bg="#1a1a2e", padx=12, pady=8)
        trans_frame.grid(row=1, column=0, sticky="nsew")
        trans_frame.rowconfigure(1, weight=1)
        trans_frame.columnconfigure(0, weight=1)
        tk.Label(trans_frame, text="번역 (한국어)",
                 font=("Malgun Gothic", 8), fg="#666", bg="#1a1a2e"
                 ).grid(row=0, column=0, sticky="w")
        self._trans_text = tk.Text(trans_frame, wrap="word",
                                   font=("Malgun Gothic", 12, "bold"),
                                   fg="white", bg="#1a1a2e",
                                   relief="flat", padx=8, pady=6)
        self._trans_text.grid(row=1, column=0, sticky="nsew")

        # ── 구분선 ────────────────────────────────────────────────
        tk.Frame(self.win, bg="#0f3460", height=1
                 ).grid(row=2, column=0, sticky="ew", padx=12, pady=4)

        # ── 원문 (일본어) — 고정 3줄 ─────────────────────────────
        orig_frame = tk.Frame(self.win, bg="#1a1a2e", padx=12, pady=4)
        orig_frame.grid(row=3, column=0, sticky="ew")
        orig_frame.columnconfigure(0, weight=1)
        tk.Label(orig_frame, text="원문 (일본어)",
                 font=("Malgun Gothic", 8), fg="#666", bg="#1a1a2e"
                 ).grid(row=0, column=0, sticky="w")
        self._orig_text = tk.Text(orig_frame, height=3, wrap="word",
                                  font=("Meiryo", 10), fg="#888", bg="#0f3460",
                                  relief="flat", padx=8, pady=4)
        self._orig_text.grid(row=1, column=0, sticky="ew")

        # ── 버튼 영역 ─────────────────────────────────────────────
        btn_frame = tk.Frame(self.win, bg="#16213e", pady=6)
        btn_frame.grid(row=4, column=0, sticky="ew")
        self._copy_btn = tk.Button(btn_frame, text="📋 번역 복사",
                                   font=("Malgun Gothic", 9), fg="white", bg="#e94560",
                                   relief="flat", padx=12, pady=4, cursor="hand2",
                                   activebackground="#c73652", activeforeground="white")
        self._copy_btn.pack(side="left", padx=8)
        tk.Button(btn_frame, text="닫기", command=self._on_close,
                  font=("Malgun Gothic", 9), fg="#aaa", bg="#0f3460",
                  relief="flat", padx=12, pady=4, cursor="hand2",
                  activebackground="#1a4a8a", activeforeground="white"
                  ).pack(side="right", padx=8)

    def update(self, original: str, translated: str):
        """번역 내용 교체 — 창은 그대로 유지"""
        # 번역 결과
        self._trans_text.config(state="normal")
        self._trans_text.delete("1.0", "end")
        self._trans_text.insert("1.0", translated)
        self._trans_text.config(state="disabled")

        # 원문
        self._orig_text.config(state="normal")
        self._orig_text.delete("1.0", "end")
        self._orig_text.insert("1.0", original)
        self._orig_text.config(state="disabled")

        # 복사 버튼 커맨드 갱신
        def copy_translated():
            pyperclip.copy(translated)
            self._copy_btn.config(text="✓ 복사됨!")
            self.win.after(1500, lambda: self._copy_btn.config(text="📋 번역 복사"))

        self._copy_btn.config(command=copy_translated)

        # 창 앞으로 올림
        self.win.lift()
        self.win.focus_force()


def show_result(original: str, translated: str):
    """기존 창이 있으면 내용 교체, 없으면 새로 생성"""
    global _result_popup
    if _result_popup:
        try:
            _result_popup.update(original, translated)
            return
        except Exception:
            _result_popup = None   # 창이 이미 닫혔으면 새로 만들기
    popup = ResultPopup()
    popup.update(original, translated)


def show_toast(message: str, duration: int = 2500):
    toast = tk.Toplevel(_root)
    toast.overrideredirect(True)
    toast.attributes("-topmost", True)
    toast.attributes("-alpha", 0.88)
    toast.configure(bg="#16213e")
    tk.Label(toast, text=message, font=("Malgun Gothic", 10),
             fg="white", bg="#16213e", padx=16, pady=10).pack()
    sw = toast.winfo_screenwidth()
    sh = toast.winfo_screenheight()
    toast.update_idletasks()
    w, h = toast.winfo_reqwidth(), toast.winfo_reqheight()
    toast.geometry(f"{w}x{h}+{sw - w - 20}+{sh - h - 80}")
    toast.after(duration, toast.destroy)


# ══════════════════════════════════════════════════════════════
# 메인 번역 흐름 (번역 워커 스레드에서 실행)
# ══════════════════════════════════════════════════════════════

def run_translation():
    global is_translating
    if is_translating:
        return
    is_translating = True
    _root.after(0, lambda: set_translate_btn_state("disabled"))

    try:
        if not capture_region:
            _root.after(0, lambda: show_toast("⚠ 캡처 영역이 없습니다\n영역 설정 버튼으로 먼저 지정하세요"))
            return

        _root.after(0, lambda: show_toast("📸 캡처 & 텍스트 인식 중..."))

        # 오버레이가 스크린샷에 찍히지 않도록 잠깐 숨김
        _root.after(0, _withdraw_overlay)
        time.sleep(0.15)

        image    = ImageGrab.grab(bbox=capture_region)
        _root.after(0, _deiconify_overlay)

        raw_text = asyncio.run(do_ocr(image))

        if not raw_text.strip():
            _root.after(0, lambda: show_toast("⚠ 텍스트를 인식하지 못했습니다"))
            return

        cleaned = clean_text(raw_text)
        _root.after(0, lambda: show_toast("🌐 파파고 번역 중..."))

        # 번역은 브라우저 전용 워커 큐를 통해 요청
        translated = translate_via_queue(cleaned)

        # 결과 창은 메인 스레드에서 생성/갱신
        _root.after(0, lambda: show_result(cleaned, translated))

    except Exception as e:
        msg = str(e)[:60]
        _root.after(0, lambda: show_toast(f"오류 발생: {msg}"))
    finally:
        is_translating = False
        _root.after(0, lambda: set_translate_btn_state("normal"))


def on_translate_click():
    threading.Thread(target=run_translation, daemon=True).start()

def on_region_click():
    select_region()


# ══════════════════════════════════════════════════════════════
# 종료 처리 — 브라우저 워커가 완전히 끝날 때까지 대기
# ══════════════════════════════════════════════════════════════

def on_quit_click():
    """메인 스레드에서 호출 — tkinter 위젯 정리 후 워커 종료 대기"""
    hide_region_overlay()
    _root.withdraw()   # 창 즉시 숨김 (사용자 경험)

    # 별도 스레드에서 워커 종료 대기 후 프로세스 종료
    threading.Thread(target=_quit_sequence, daemon=True).start()

def _quit_sequence():
    """브라우저 워커에 종료 센티넬 전송 → join → 프로세스 종료"""
    _browser_queue.put(None)          # 워커에게 종료 신호
    if _browser_thread:
        _browser_thread.join(timeout=15)  # Node.js 완전 종료 대기
    os._exit(0)


# ══════════════════════════════════════════════════════════════
# GUI 상태 업데이트 헬퍼
# ══════════════════════════════════════════════════════════════

def update_region_label():
    if _region_label and capture_region:
        x1, y1, x2, y2 = capture_region
        _region_label.config(
            text=f"캡처 영역: ({x1}, {y1}) → ({x2}, {y2})  [{x2-x1}×{y2-y1}]",
            fg="#00FF88"
        )
    elif _region_label:
        _region_label.config(text="캡처 영역: 미설정", fg="#e94560")

def update_status_label(msg: str):
    if _status_label:
        _status_label.config(text=msg)

def set_translate_btn_state(state: str):
    if _translate_btn:
        _translate_btn.config(state=state)


# ══════════════════════════════════════════════════════════════
# 메인 GUI 창 빌드
# ══════════════════════════════════════════════════════════════

def build_main_window():
    global _root, _region_label, _status_label, _translate_btn

    _root = tk.Tk()
    _root.title("🎌 일본어 번역기")
    _root.configure(bg="#1a1a2e")
    _root.resizable(False, False)
    _root.attributes("-topmost", True)

    _root.update_idletasks()
    sw = _root.winfo_screenwidth()
    sh = _root.winfo_screenheight()
    w, h = 360, 200
    _root.geometry(f"{w}x{h}+{sw - w - 20}+{sh - h - 80}")

    # 헤더
    header = tk.Frame(_root, bg="#16213e", pady=10)
    header.pack(fill="x")
    tk.Label(header, text="🎌  일본어 게임 번역기",
             font=("Malgun Gothic", 13, "bold"),
             fg="#e94560", bg="#16213e").pack()

    # 상태 표시
    info_frame = tk.Frame(_root, bg="#1a1a2e", padx=16, pady=8)
    info_frame.pack(fill="x")
    _region_label = tk.Label(info_frame, text="캡처 영역: 미설정",
                              font=("Malgun Gothic", 9),
                              fg="#e94560", bg="#1a1a2e", anchor="w")
    _region_label.pack(fill="x")
    _status_label = tk.Label(info_frame, text="브라우저 초기화 중...",
                              font=("Malgun Gothic", 8),
                              fg="#666", bg="#1a1a2e", anchor="w")
    _status_label.pack(fill="x")

    tk.Frame(_root, bg="#0f3460", height=1).pack(fill="x", padx=16)

    # 버튼 영역
    btn_frame = tk.Frame(_root, bg="#1a1a2e", padx=16, pady=12)
    btn_frame.pack(fill="x")
    btn_cfg = dict(font=("Malgun Gothic", 10, "bold"), relief="flat",
                   cursor="hand2", pady=7)

    tk.Button(btn_frame, text="📐  영역 설정",
              command=on_region_click,
              fg="white", bg="#0f3460",
              activebackground="#1a4a8a", activeforeground="white",
              **btn_cfg).pack(fill="x", pady=(0, 6))

    _translate_btn = tk.Button(btn_frame, text="🌐  번역 실행",
                               command=on_translate_click,
                               fg="white", bg="#e94560",
                               activebackground="#c73652", activeforeground="white",
                               **btn_cfg)
    _translate_btn.pack(fill="x", pady=(0, 6))

    tk.Button(btn_frame, text="✕  종료",
              command=on_quit_click,
              fg="#aaa", bg="#16213e",
              activebackground="#2a2a4e", activeforeground="white",
              **btn_cfg).pack(fill="x")

    _root.protocol("WM_DELETE_WINDOW", on_quit_click)
    return _root


# ══════════════════════════════════════════════════════════════
# 진입점
# ══════════════════════════════════════════════════════════════

def main():
    global _browser_thread

    load_config()
    build_main_window()
    update_region_label()

    # 저장된 영역이 있으면 오버레이 즉시 표시
    if capture_region:
        _root.after(100, lambda: show_region_overlay(capture_region))

    # 브라우저 전용 워커 스레드 시작
    # daemon=False — 메인 루프 종료 후에도 정상 종료 흐름을 따르게 함
    _browser_thread = threading.Thread(target=_browser_worker, daemon=False, name="BrowserWorker")
    _browser_thread.start()

    _root.mainloop()


if __name__ == "__main__":
    main()
