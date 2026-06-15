"""
게임 번역기 (GUI 버전)
- 영역 설정 버튼 → 드래그로 캡처 영역 선택 → 화면에 테두리로 표시
- 번역 실행 버튼 → OCR → 파파고 번역 → 팝업 표시
- 언어 쌍 선택 (일본어·영어·중국어 → 한국어 등)
"""

import asyncio
import re
import threading
import queue
import tkinter as tk
import pyperclip
import winocr
from PIL import ImageGrab, Image, ImageEnhance
import json
import os
import time
from playwright.sync_api import sync_playwright

# ── 설정 파일 경로 ──────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "translator_config.json")

# ── 언어 쌍 옵션 ────────────────────────────────────────────
# (표시 이름, 파파고 sk 코드, 파파고 tk 코드, OCR 언어, CJK 공백 제거 여부)
LANG_PAIRS = [
    ("🇯🇵 일본어  →  한국어",   "ja",    "ko", "ja",    True),
    ("🇺🇸 영어    →  한국어",   "en",    "ko", "en",    False),
    ("🇨🇳 중국어(간체) → 한국어", "zh-CN", "ko", "zh-Hans", True),
    ("🇹🇼 중국어(번체) → 한국어", "zh-TW", "ko", "zh-Hant", True),
    ("🇯🇵 일본어  →  영어",    "ja",    "en", "ja",    True),
    ("🇺🇸 영어    →  일본어",   "en",    "ja", "en",    False),
]
# 현재 선택된 언어 쌍 인덱스
_lang_pair_idx: int = 0

# ── 이미지 전처리 프리셋 ─────────────────────────────────────
# (표시 이름, 설명, 확대 배율, 그레이스케일, 대비, 선명도)
PREPROCESS_PRESETS = [
    ("⚡ 기본",          "대부분의 게임에 적합",              2.0, True,  1.8, 2.5),
    ("🌑 어두운 배경",   "검은/어두운 배경에 밝은 글자",     2.0, True,  2.5, 2.0),
    ("☀️ 밝은 배경",    "흰/밝은 배경에 어두운 글자",       2.0, True,  1.4, 2.0),
    ("🔍 작은 글씨",     "글자가 매우 작거나 저해상도 화면",  3.0, True,  2.0, 3.0),
    ("🎨 컬러 유지",     "그레이스케일 변환 없이 원색 유지",  2.0, False, 1.8, 2.5),
    ("🚫 전처리 없음",   "원본 이미지 그대로 OCR",           1.0, False, 1.0, 1.0),
]
# 현재 선택된 전처리 프리셋 인덱스
_preprocess_idx: int = 0

# ── 미리 컴파일된 CJK 공백 제거 패턴 ────────────────────────
_RE_CJK_SPACE_NL   = re.compile(r'(?<=[　-鿿＀-￯])\s+(?=[　-鿿＀-￯])')
_RE_CJK_SPACE_NONL = re.compile(r'(?<=[　-鿿＀-￯])[^\S\n]+(?=[　-鿿＀-￯])')

# ── 전역 상태 ───────────────────────────────────────────────
capture_region      = None  # (x1, y1, x2, y2)
is_translating      = False
_cfg_remove_newline = True  # OCR 결과 줄바꿈 제거 여부
_cfg_remove_space   = True  # OCR 결과 CJK 띄어쓰기 제거 여부

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
_lang_var:          object = None   # tk.StringVar  — 언어 쌍 드롭다운
_preprocess_var:    object = None   # tk.StringVar  — 전처리 프리셋 드롭다운
_remove_newline_var: object = None  # tk.BooleanVar — 줄바꿈 제거 체크박스
_remove_space_var:   object = None  # tk.BooleanVar — 띄어쓰기 제거 체크박스


# ══════════════════════════════════════════════════════════════
# 설정 저장/불러오기
# ══════════════════════════════════════════════════════════════

def load_config():
    global capture_region, _lang_pair_idx, _preprocess_idx
    global _cfg_remove_newline, _cfg_remove_space
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                region = data.get("capture_region")
                if region and len(region) == 4:
                    capture_region = tuple(region)
                idx = data.get("lang_pair_idx", 0)
                if isinstance(idx, int) and 0 <= idx < len(LANG_PAIRS):
                    _lang_pair_idx = idx
                pidx = data.get("preprocess_idx", 0)
                if isinstance(pidx, int) and 0 <= pidx < len(PREPROCESS_PRESETS):
                    _preprocess_idx = pidx
                _cfg_remove_newline = bool(data.get("remove_newline", True))
                _cfg_remove_space   = bool(data.get("remove_space",   True))
        except Exception:
            pass

def save_config():
    data = {
        "capture_region":  list(capture_region) if capture_region else None,
        "lang_pair_idx":   _lang_pair_idx,
        "preprocess_idx":  _preprocess_idx,
        "remove_newline":  _cfg_remove_newline,
        "remove_space":    _cfg_remove_space,
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════
# 브라우저 전용 워커 스레드
# ══════════════════════════════════════════════════════════════

def _launch_browser(playwright):
    """Chrome → Edge 순으로 시도해 브라우저 인스턴스를 반환한다."""
    for channel in ("chrome", "msedge"):
        try:
            browser = playwright.chromium.launch(
                channel=channel,
                headless=False,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            print(f"  ✅ {channel} 브라우저 사용")
            return browser
        except Exception:
            continue
    raise RuntimeError(
        "Chrome 또는 Edge가 설치되어 있지 않습니다.\n"
        "https://www.google.com/chrome 에서 Chrome을 설치해 주세요."
    )


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
        browser = _launch_browser(playwright)
        page = browser.new_page()
        _, sk0, tk0, _, _ = LANG_PAIRS[0]
        page.goto(f"https://papago.naver.com/?sk={sk0}&tk={tk0}",
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

        text, sk, tk_lang, result_box, done_event = item
        papago_url = f"https://papago.naver.com/?sk={sk}&tk={tk_lang}"
        try:
            # 페이지 살아있는지 확인, 죽었으면 재시작
            if page is None or page.is_closed():
                print("  🔄 브라우저 재시작 중...")
                try:
                    if page:    page.close()
                    if browser: browser.close()
                except Exception:
                    pass
                browser = _launch_browser(playwright)
                page = browser.new_page()
                page.goto(papago_url, wait_until="domcontentloaded", timeout=20000)

            # 언어 쌍이 달라졌거나 파파고가 아닌 경우 해당 언어 URL로 이동
            if not page.url.startswith(papago_url):
                page.goto(papago_url, wait_until="domcontentloaded", timeout=20000)

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


def translate_via_queue(text: str, sk: str, tk_lang: str) -> str:
    """
    번역 요청을 브라우저 워커 큐에 넣고 결과를 기다린다.
    호출은 메인 스레드가 아닌 번역 워커 스레드에서 이루어진다.
    """
    result_box = [None]
    done_event = threading.Event()
    _browser_queue.put((text, sk, tk_lang, result_box, done_event))
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

def _set_overlay_visibility(visible: bool):
    if _overlay:
        try:
            _overlay.deiconify() if visible else _overlay.withdraw()
        except Exception:
            pass


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

def preprocess_image(image: Image.Image) -> Image.Image:
    """
    현재 선택된 프리셋(_preprocess_idx)에 따라 이미지를 전처리한다.

    파이프라인:
      1. 확대   — 작은 글자·저해상도 캡처 인식률 향상 (배율은 프리셋마다 다름)
      2. 그레이스케일 — 배경 색상 노이즈 제거 (프리셋에 따라 생략 가능)
      3. 대비 강화  — 글자/배경 경계 명확화
      4. 선명도 강화 — 확대로 흐려진 엣지 복원
    """
    _, _, scale, grayscale, contrast, sharpness = PREPROCESS_PRESETS[_preprocess_idx]

    # 전처리 없음 프리셋이면 원본 그대로 반환
    if scale == 1.0 and not grayscale and contrast == 1.0 and sharpness == 1.0:
        return image

    w, h = image.size
    image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    if grayscale:
        image = image.convert("L")

    image = ImageEnhance.Contrast(image).enhance(contrast)
    image = ImageEnhance.Sharpness(image).enhance(sharpness)

    # WinOCR은 RGB 입력을 기대하므로 다시 변환
    image = image.convert("RGB")

    return image

async def do_ocr_lang(image: Image.Image, lang: str) -> str:
    """WinOCR 언어 코드를 받아 OCR 수행 (언어 쌍 선택 연동용)"""
    result = await winocr.recognize_pil(image, lang)
    # result.text 는 줄바꿈 없이 전체를 하나의 문자열로 반환한다.
    # result.lines 를 사용해 인식된 줄 단위로 \n 을 삽입해 재구성한다.
    if hasattr(result, "lines") and result.lines:
        return "\n".join(line.text for line in result.lines)
    return result.text

def clean_text(text: str, remove_cjk_spaces: bool = True) -> str:
    """
    OCR 결과 텍스트 정리.
    - 줄바꿈 제거: _cfg_remove_newline 전역값에 따라 적용
    - 띄어쓰기 제거: _cfg_remove_space AND remove_cjk_spaces 모두 True일 때 적용
      (remove_cjk_spaces는 언어 쌍에 따른 자동 판단값)
    """
    if _cfg_remove_newline:
        text = text.replace("\n", "").replace("\r", "")
    if _cfg_remove_space and remove_cjk_spaces:
        pat = _RE_CJK_SPACE_NL if _cfg_remove_newline else _RE_CJK_SPACE_NONL
        text = pat.sub('', text)
    return text.strip()


# ══════════════════════════════════════════════════════════════
# 팝업 결과 창
# ══════════════════════════════════════════════════════════════

def _set_text_widget(widget: tk.Text, content: str):
    widget.config(state="normal")
    widget.delete("1.0", "end")
    widget.insert("1.0", content)
    widget.config(state="disabled")


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
        px = sw - w - 20
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
        _set_text_widget(self._trans_text, translated)
        _set_text_widget(self._orig_text, original)

        def copy_translated():
            pyperclip.copy(translated)
            self._copy_btn.config(text="✓ 복사됨!")
            self.win.after(1500, lambda: self._copy_btn.config(text="📋 번역 복사"))

        self._copy_btn.config(command=copy_translated)

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

        # 현재 선택된 언어 쌍 스냅샷 (번역 도중 UI 변경 방지)
        pair = LANG_PAIRS[_lang_pair_idx]
        _, sk, tk_lang, ocr_lang, remove_spaces = pair

        _root.after(0, lambda: show_toast("📸 캡처 & 텍스트 인식 중..."))

        # 오버레이가 스크린샷에 찍히지 않도록 잠깐 숨김
        _root.after(0, lambda: _set_overlay_visibility(False))
        time.sleep(0.15)

        image    = ImageGrab.grab(bbox=capture_region)
        _root.after(0, lambda: _set_overlay_visibility(True))

        image    = preprocess_image(image)
        raw_text = asyncio.run(do_ocr_lang(image, ocr_lang))

        if not raw_text.strip():
            _root.after(0, lambda: show_toast("⚠ 텍스트를 인식하지 못했습니다"))
            return

        cleaned = clean_text(raw_text, remove_cjk_spaces=remove_spaces)
        _root.after(0, lambda: show_toast("🌐 파파고 번역 중..."))

        # 번역은 브라우저 전용 워커 큐를 통해 요청
        translated = translate_via_queue(cleaned, sk, tk_lang)

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


def _find_label_index(items: list, label: str) -> int:
    for i, item in enumerate(items):
        if item[0] == label:
            return i
    return 0

def on_lang_change(*_):
    global _lang_pair_idx
    if _lang_var is None:
        return
    _lang_pair_idx = _find_label_index(LANG_PAIRS, _lang_var.get())
    save_config()

def on_preprocess_change(*_):
    global _preprocess_idx
    if _preprocess_var is None:
        return
    _preprocess_idx = _find_label_index(PREPROCESS_PRESETS, _preprocess_var.get())
    save_config()

def on_text_option_change(*_):
    """체크박스 변경 시 전역 설정값 동기화 후 저장"""
    global _cfg_remove_newline, _cfg_remove_space
    if _remove_newline_var:
        _cfg_remove_newline = bool(_remove_newline_var.get())
    if _remove_space_var:
        _cfg_remove_space = bool(_remove_space_var.get())
    save_config()


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
    if not _region_label:
        return
    if capture_region:
        x1, y1, x2, y2 = capture_region
        text  = f"캡처 영역: ({x1}, {y1}) → ({x2}, {y2})  [{x2-x1}×{y2-y1}]"
        color = "#00FF88"
    else:
        text  = "캡처 영역: 미설정"
        color = "#e94560"
    _region_label.config(text=text, fg=color)

def update_status_label(msg: str):
    if _status_label:
        _status_label.config(text=msg)

def set_translate_btn_state(state: str):
    if _translate_btn:
        _translate_btn.config(state=state)


# ══════════════════════════════════════════════════════════════
# 메인 GUI 창 빌드
# ══════════════════════════════════════════════════════════════

def _style_option_menu(menu: tk.OptionMenu, width: int = 26):
    menu.config(
        font=("Malgun Gothic", 9),
        fg="white", bg="#0f3460",
        activeforeground="white", activebackground="#1a4a8a",
        relief="flat", cursor="hand2",
        highlightthickness=0, bd=0,
        anchor="w", width=width,
    )
    menu["menu"].config(
        font=("Malgun Gothic", 9),
        fg="white", bg="#0f3460",
        activeforeground="white", activebackground="#1a4a8a",
    )


def build_main_window():
    global _root, _region_label, _status_label, _translate_btn
    global _lang_var, _preprocess_var, _remove_newline_var, _remove_space_var

    _root = tk.Tk()
    _root.title("🎌 게임 번역기")
    _root.configure(bg="#1a1a2e")
    _root.resizable(False, False)
    _root.attributes("-topmost", True)

    sw = _root.winfo_screenwidth()
    sh = _root.winfo_screenheight()
    w = 360  # 너비만 고정 — 높이는 위젯 배치 후 자동 결정

    # 헤더
    header = tk.Frame(_root, bg="#16213e", pady=10)
    header.pack(fill="x")
    tk.Label(header, text="🎌  게임 번역기",
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

    # ── 언어 쌍 선택 드롭다운 ──────────────────────────────────
    lang_frame = tk.Frame(_root, bg="#1a1a2e", padx=16, pady=4)
    lang_frame.pack(fill="x")
    tk.Label(lang_frame, text="번역 언어",
             font=("Malgun Gothic", 8), fg="#666", bg="#1a1a2e"
             ).pack(anchor="w")

    _lang_var = tk.StringVar(value=LANG_PAIRS[_lang_pair_idx][0])
    _lang_var.trace_add("write", on_lang_change)

    opt_menu = tk.OptionMenu(lang_frame, _lang_var, *[p[0] for p in LANG_PAIRS])
    _style_option_menu(opt_menu)
    opt_menu.pack(fill="x")

    # ── 전처리 프리셋 드롭다운 ────────────────────────────────
    pre_frame = tk.Frame(_root, bg="#1a1a2e", padx=16, pady=4)
    pre_frame.pack(fill="x")

    # 레이블 + 툴팁 설명을 한 줄에 배치
    pre_header = tk.Frame(pre_frame, bg="#1a1a2e")
    pre_header.pack(fill="x")
    tk.Label(pre_header, text="OCR 전처리",
             font=("Malgun Gothic", 8), fg="#666", bg="#1a1a2e"
             ).pack(side="left")
    _pre_desc_label = tk.Label(pre_header,
             text=f"  ← {PREPROCESS_PRESETS[_preprocess_idx][1]}",
             font=("Malgun Gothic", 7), fg="#444", bg="#1a1a2e")
    _pre_desc_label.pack(side="left")

    _preprocess_var = tk.StringVar(value=PREPROCESS_PRESETS[_preprocess_idx][0])

    def _on_preprocess_change_with_desc(*_):
        on_preprocess_change()
        label = _preprocess_var.get()
        for preset in PREPROCESS_PRESETS:
            if preset[0] == label:
                _pre_desc_label.config(text=f"  ← {preset[1]}")
                break

    _preprocess_var.trace_add("write", _on_preprocess_change_with_desc)

    pre_menu = tk.OptionMenu(pre_frame, _preprocess_var, *[p[0] for p in PREPROCESS_PRESETS])
    _style_option_menu(pre_menu)
    pre_menu.pack(fill="x")

    # ── OCR 텍스트 정리 옵션 체크박스 ────────────────────────
    chk_frame = tk.Frame(_root, bg="#1a1a2e", padx=16, pady=4)
    chk_frame.pack(fill="x")
    tk.Label(chk_frame, text="텍스트 정리",
             font=("Malgun Gothic", 8), fg="#666", bg="#1a1a2e"
             ).pack(anchor="w")

    chk_row = tk.Frame(chk_frame, bg="#1a1a2e")
    chk_row.pack(fill="x")

    chk_cfg = dict(
        font=("Malgun Gothic", 9), bg="#1a1a2e",
        activebackground="#1a1a2e", cursor="hand2",
        relief="flat", bd=0,
    )

    _remove_newline_var = tk.BooleanVar(value=_cfg_remove_newline)
    _remove_newline_var.trace_add("write", on_text_option_change)
    tk.Checkbutton(chk_row, text="줄바꿈 제거",
                   variable=_remove_newline_var,
                   fg="#ccc", selectcolor="#0f3460",
                   **chk_cfg).pack(side="left", padx=(0, 16))

    _remove_space_var = tk.BooleanVar(value=_cfg_remove_space)
    _remove_space_var.trace_add("write", on_text_option_change)
    tk.Checkbutton(chk_row, text="띄어쓰기 제거",
                   variable=_remove_space_var,
                   fg="#ccc", selectcolor="#0f3460",
                   **chk_cfg).pack(side="left")

    tk.Frame(_root, bg="#0f3460", height=1).pack(fill="x", padx=16, pady=(6, 0))

    # 버튼 영역
    btn_frame = tk.Frame(_root, bg="#1a1a2e", padx=16, pady=12)
    btn_frame.pack(fill="x")
    btn_cfg = dict(font=("Malgun Gothic", 10, "bold"), relief="flat",
                   cursor="hand2", pady=7)

    tk.Button(btn_frame, text="📐  영역 설정",
              command=select_region,
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

    # 모든 위젯 배치 후 자연 높이를 측정해 위치 설정
    _root.update_idletasks()
    h = _root.winfo_reqheight()
    _root.geometry(f"{w}x{h}+{sw - w - 20}+{sh - h - 80}")

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
