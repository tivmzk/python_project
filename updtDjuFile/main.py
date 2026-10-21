import tkinter as tk
from tkinter import ttk, messagebox
import re
import threading
import requests
from bs4 import BeautifulSoup
import pyperclip

URL_MAP = {
    '1': 'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2641&mi=4321',
    '2': 'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2642&mi=4322',
    '3': 'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2643&mi=4323',
    '4': 'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2644&mi=4324',
    '5': 'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2645&mi=4325',
    '6': 'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2646&mi=4326',
    '7': 'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2647&mi=4327',
}

# 파일 번호(예: 2-0-1). 파일명 앞에 붙어 있어도 되고, 3-1-2는 _1(기구표)/_2(직제규정)를 붙일 수 있다
FILE_NUM_RE = re.compile(r'(\d+(?:-\d+)+)(_[12])?')

CONTENT_START = '<!-- 페이지뷰 : 서브콘텐츠 시작-->'
CONTENT_END = '<!-- //페이지뷰 : 서브콘텐츠 끝 -->'


def get_query(dtl, file_url):
    return f"UPDATE TSA_ATCH_FILE_DETAIL SET FILE_DTLS = '{dtl}' WHERE FILE_STRE_COURS = '{file_url}';"


def split_db_row(line):
    """'경로<탭>파일명' 또는 '파일명<탭>경로' 한 줄을 (경로, 파일명)으로 나눈다. 경로는 /로 시작하는 쪽이다."""
    parts = [p.strip() for p in line.split('\t') if p.strip()]
    if len(parts) < 2:
        # 탭이 공백으로 바뀌어 붙여넣어진 경우
        m = re.match(r'^(/\S+)\s+(.+)$', line) or re.match(r'^(.+?)\s+(/\S+)$', line)
        if not m:
            return None
        parts = list(m.groups())
    paths = [p for p in parts if p.startswith('/')]
    if len(paths) != 1:
        return None
    return paths[0], ' '.join(p for p in parts if p != paths[0])


def extract_content(page_html):
    """콘텐츠 영역만 잘라낸다. 탭메뉴(.tab_st1_box)와 UPPER TAB 주석들은 마지막 시작 주석보다 앞에 있어 제외된다."""
    start = page_html.rfind(CONTENT_START)
    end = page_html.find(CONTENT_END, start) if start != -1 else -1
    if end != -1:
        return page_html[start:end + len(CONTENT_END)]

    # 시작/끝 주석이 없으면 div.subCntBody 안쪽에서 탭메뉴와 앞뒤 주석을 걷어낸다
    body = re.search(r'<div[^>]*class="[^"]*\bsubCntBody\b[^"]*"[^>]*>', page_html)
    if not body:
        return None
    body_end = find_div_end(page_html, body.end())
    if body_end is None:
        return None
    inner = page_html[body.end():body_end]

    while True:
        tab = re.search(r'<div[^>]*class="[^"]*\btab_st1_box\b[^"]*"[^>]*>', inner)
        if not tab:
            break
        tab_end = find_div_end(inner, tab.end())
        if tab_end is None:
            break
        inner = inner[:tab.start()] + inner[inner.index('>', tab_end) + 1:]

    inner = re.sub(r'^(\s*<!--.*?-->)*\s*', '', inner, flags=re.S)
    inner = re.sub(r'(\s*<!--(?:(?!-->).)*-->)*\s*$', '', inner, flags=re.S)
    return inner or None


def find_div_end(html, pos):
    """pos(여는 div 태그 바로 뒤)에서 시작해 짝이 맞는 </div>의 시작 위치를 찾는다."""
    depth = 1
    for m in re.finditer(r'<!--.*?-->|<div\b|</div\s*>', html[pos:], flags=re.S):
        token = m.group()
        if token.startswith('<!--'):
            continue
        depth += 1 if token.startswith('<div') else -1
        if depth == 0:
            return pos + m.start()
    return None


def fetch_page(url, pairs, log):
    """pairs: [(파일 번호, 새 경로 또는 None)] → (기존 파일 쿼리 목록, 페이지 제목, 수정된 콘텐츠 html 또는 None)"""
    try:
        log(f"[조회] {url}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        all_td = soup.select('.tbl_st td')

        title_tag = soup.select_one('h2.pageTitle')
        title = title_tag.get_text(strip=True) if title_tag else url
        # BeautifulSoup으로 다시 직렬화하면 원본 html이 변형되므로 원문 문자열에서 href만 교체한다
        content = extract_content(resp.text)
        if content is None:
            log("  [경고] 콘텐츠 영역을 찾지 못해 html은 수정하지 않습니다.")
        replaced = 0

        result = []
        for file_num, new_path in pairs:
            temp = ''
            search_num = file_num
            if file_num.startswith('3-1-2_'):
                temp = file_num.split('_')[1]
                search_num = '3-1-2'

            found = False
            for td in all_td:
                if search_num != td.get_text(strip=True):
                    continue
                a_tag = td.find_next_sibling('td').find('a')
                sibling_text = a_tag.get_text(strip=True)
                if temp == '1' and '기구표' not in sibling_text:
                    continue
                if temp == '2' and '직제규정' not in sibling_text:
                    continue
                href = a_tag.attrs['href']
                result.append(get_query('', href))
                log(f"  ✓ {file_num} → {href}")
                found = True

                if new_path and content is not None:
                    old_attr = f'href="{href}"'
                    if content.count(old_attr) == 1:
                        content = content.replace(old_attr, f'href="{new_path}"')
                        replaced += 1
                        log(f"    ↳ html 링크 교체 → {new_path}")
                    else:
                        log(f"    [경고] html에서 링크를 특정하지 못해 교체하지 않았습니다. ({content.count(old_attr)}건)")
                break
            if not found:
                log(f"  ✗ {file_num} 미발견")
        return result, title, content if replaced else None
    except Exception as e:
        log(f"[오류] {e}")
        return [], url, None


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("대전대 규정 파일 쿼리 생성기")
        self.geometry("800x900")
        self.minsize(640, 720)
        self.pages = []  # [(페이지 제목, 수정된 콘텐츠 html)]
        self._build_ui()

    def _build_ui(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # ── 1. 기존 파일 번호 + 새 파일 경로 ──────────────────────
        pair_frame = ttk.LabelFrame(
            main,
            text="① 기존 파일 번호 + 새 파일 경로",
            padding=8
        )
        pair_frame.pack(fill=tk.X, padx=4, pady=4)

        inp_row = ttk.Frame(pair_frame)
        inp_row.pack(fill=tk.X)
        inp_row.columnconfigure(0, weight=2)
        inp_row.columnconfigure(1, weight=3)
        ttk.Label(inp_row, text="번호 또는 파일명 (한 줄에 하나)").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(inp_row, text="새 경로 (한 줄에 하나)").grid(row=0, column=1, sticky=tk.W, padx=(6, 0))
        self.num_text = tk.Text(inp_row, height=4, width=30, wrap=tk.NONE, undo=True)
        self.num_text.grid(row=1, column=0, sticky=tk.EW)
        self.path_text = tk.Text(inp_row, height=4, width=45, wrap=tk.NONE, undo=True)
        self.path_text.grid(row=1, column=1, sticky=tk.EW, padx=(6, 0))
        ttk.Button(inp_row, text="추가", command=self._add_pairs, width=8).grid(row=1, column=2, sticky=tk.N, padx=(6, 0))
        for txt in (self.num_text, self.path_text):
            txt.bind('<Control-Return>', lambda _: self._add_pairs() or 'break')
            txt.bind('<Tab>', lambda e: e.widget.tk_focusNext().focus() or 'break')

        ttk.Label(
            pair_frame,
            text="※ 여러 줄을 한번에 붙여넣을 수 있고, 두 칸의 같은 줄끼리 짝이 됩니다. (추가: 버튼 또는 Ctrl+Enter)\n"
                 "   번호 칸에 파일명(예: 5-0-1.중앙도서관규정.pdf)을 넣으면 앞의 번호만 추출합니다.\n"
                 "   DB 조회 결과(경로 + 파일명, 순서 무관)는 한쪽 칸에만 그대로 붙여넣으면 자동으로 나눠집니다.",
            foreground='#666666',
            justify=tk.LEFT,
        ).pack(fill=tk.X, pady=(4, 0))

        list_row = ttk.Frame(pair_frame)
        list_row.pack(fill=tk.X, pady=(6, 0))
        self.pair_tv = ttk.Treeview(list_row, columns=('num', 'path'), show='headings', height=6, selectmode='browse')
        self.pair_tv.heading('num', text='기존 파일 번호')
        self.pair_tv.heading('path', text='새 파일 경로')
        self.pair_tv.column('num', width=110, stretch=False)
        self.pair_tv.column('path', width=480)
        ts = ttk.Scrollbar(list_row, orient=tk.VERTICAL, command=self.pair_tv.yview)
        self.pair_tv.config(yscrollcommand=ts.set)
        self.pair_tv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ts.pack(side=tk.LEFT, fill=tk.Y)
        self.pair_tv.bind('<Delete>', lambda _: self._del_pair())
        tb = ttk.Frame(list_row)
        tb.pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(tb, text="삭제", command=self._del_pair, width=8).pack(pady=1)
        ttk.Button(tb, text="전체 삭제", command=lambda: self.pair_tv.delete(*self.pair_tv.get_children()), width=8).pack(pady=1)

        # ── 3. 실행 ───────────────────────────────────────────────
        run_row = ttk.Frame(main)
        run_row.pack(fill=tk.X, padx=4, pady=6)
        self.run_btn = ttk.Button(run_row, text="쿼리 생성 실행", command=self._run, width=18)
        self.run_btn.pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="")
        self.status_lbl = ttk.Label(run_row, textvariable=self.status_var)
        self.status_lbl.pack(side=tk.LEFT, padx=10)

        # ── 5. 수정된 콘텐츠 html ─────────────────────────────────
        # 결과 영역이 expand하기 전에 먼저 pack해야 밀려나지 않음
        html_frame = ttk.LabelFrame(main, text="③ 수정된 콘텐츠 html  (페이지 선택 후 복사)", padding=8)
        html_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=4, pady=4)
        self.page_lb = tk.Listbox(html_frame, height=3, selectmode=tk.SINGLE, activestyle='dotbox', exportselection=False)
        pgs = ttk.Scrollbar(html_frame, orient=tk.VERTICAL, command=self.page_lb.yview)
        self.page_lb.config(yscrollcommand=pgs.set)
        self.page_lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pgs.pack(side=tk.LEFT, fill=tk.Y)
        self.page_lb.bind('<Double-Button-1>', lambda _: self._copy_html())
        ttk.Button(html_frame, text="html 복사", command=self._copy_html, width=10).pack(side=tk.LEFT, padx=(6, 0))

        # ── 4. 결과 ───────────────────────────────────────────────
        result_frame = ttk.LabelFrame(main, text="② 생성된 쿼리", padding=8)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # 복사 버튼을 먼저 pack해야 텍스트 영역이 expand할 때 밀려나지 않음
        copy_row = ttk.Frame(result_frame)
        copy_row.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))
        ttk.Button(copy_row, text="클립보드에 복사", command=self._copy).pack(side=tk.RIGHT)

        txt_area = ttk.Frame(result_frame)
        txt_area.pack(fill=tk.BOTH, expand=True)
        v_sc = ttk.Scrollbar(txt_area, orient=tk.VERTICAL)
        h_sc = ttk.Scrollbar(txt_area, orient=tk.HORIZONTAL)
        self.result_text = tk.Text(
            txt_area,
            font=("Consolas", 9),
            wrap=tk.NONE,
            height=10,
            state=tk.DISABLED,
            yscrollcommand=v_sc.set,
            xscrollcommand=h_sc.set,
        )
        v_sc.config(command=self.result_text.yview)
        h_sc.config(command=self.result_text.xview)
        v_sc.pack(side=tk.RIGHT, fill=tk.Y)
        h_sc.pack(side=tk.BOTTOM, fill=tk.X)
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 텍스트 컬러 태그
        self.result_text.tag_config('log',     foreground='#888888')
        self.result_text.tag_config('comment', foreground='#008000')
        self.result_text.tag_config('sql',     foreground='#000080')

    # ── 번호 + 경로 입력 ─────────────────────────────────────────

    def _add_pairs(self):
        num_lines = [l.strip() for l in self.num_text.get('1.0', tk.END).splitlines() if l.strip()]
        path_lines = [l.strip() for l in self.path_text.get('1.0', tk.END).splitlines() if l.strip()]

        # DB 조회 결과(경로 + 파일명)를 한쪽 칸에만 그대로 붙여넣은 경우. 칸과 순서는 상관없다
        if bool(num_lines) != bool(path_lines):
            rows = [split_db_row(l) for l in num_lines or path_lines]
            if all(rows):
                path_lines = [p for p, _ in rows]
                num_lines = [n for _, n in rows]

        if not num_lines:
            messagebox.showwarning("입력 필요", "기존 파일 번호(또는 파일명)를 입력해 주세요.")
            self.num_text.focus()
            return
        if not path_lines:
            messagebox.showwarning("입력 필요", "새 파일 경로를 입력해 주세요.")
            self.path_text.focus()
            return
        if len(num_lines) != len(path_lines):
            messagebox.showwarning(
                "개수 불일치",
                f"번호는 {len(num_lines)}줄, 경로는 {len(path_lines)}줄입니다.\n줄 수가 같아야 짝을 맞출 수 있습니다."
            )
            return

        no_num = [l for l in num_lines if not FILE_NUM_RE.match(l)]
        if no_num:
            messagebox.showwarning(
                "번호 없음",
                "다음 항목에서 파일 번호를 찾지 못해 추가하지 않았습니다.\n\n" + "\n".join(f"· {l}" for l in no_num)
            )
            return

        pairs = []
        for line, path in zip(num_lines, path_lines):
            m = FILE_NUM_RE.match(line)
            num = m.group(1)
            if num == '3-1-2':
                kind = (m.group(2) or '').lstrip('_')
                if not kind:
                    rest = line[m.end():]
                    kind = '1' if '기구표' in rest else '2' if '직제' in rest else self._ask_312(path)
                if not kind:
                    return
                num = f"3-1-2_{kind}"
            pairs.append((num, path))

        for pair in pairs:
            self.pair_tv.insert('', tk.END, values=pair)
        self.num_text.delete('1.0', tk.END)
        self.path_text.delete('1.0', tk.END)
        self.num_text.focus()

    def _ask_312(self, path):
        """기구표/직제규정 중 어느 3-1-2인지 묻는다. 창을 그냥 닫으면 None."""
        dlg = tk.Toplevel(self)
        dlg.title("3-1-2 유형 선택")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()
        ttk.Label(dlg, text=f"어떤 3-1-2를 추가할까요?\n{path}", justify=tk.CENTER).pack(padx=16, pady=12)
        row = ttk.Frame(dlg)
        row.pack(pady=(0, 12))
        picked = []

        def pick(val):
            picked.append(val)
            dlg.destroy()

        ttk.Button(row, text="1 - 기구표",   command=lambda: pick('1'), width=12).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="2 - 직제규정", command=lambda: pick('2'), width=12).pack(side=tk.LEFT, padx=4)
        self.wait_window(dlg)
        return picked[0] if picked else None

    def _del_pair(self):
        sel = self.pair_tv.selection()
        if sel:
            self.pair_tv.delete(sel[0])

    # ── 실행 ─────────────────────────────────────────────────────

    def _run(self):
        # Treeview는 숫자처럼 보이는 값을 int로 돌려줄 수 있어 str로 맞춘다
        pairs = [tuple(str(v) for v in self.pair_tv.item(i, 'values')) for i in self.pair_tv.get_children()]
        if not pairs:
            messagebox.showwarning("입력 필요", "기존 파일 번호와 새 파일 경로를 하나 이상 입력해 주세요.")
            return
        self.run_btn.config(state=tk.DISABLED)
        self._set_status("조회 중...", "blue")
        self._clear_result()
        threading.Thread(target=self._run_bg, args=(pairs,), daemon=True).start()

    def _run_bg(self, pairs):
        logs = []

        def log(msg):
            logs.append(msg)

        num_map = {}
        for pair in pairs:
            key = pair[0].split('-')[0]
            num_map.setdefault(key, []).append(pair)

        old_queries = []
        pages = []
        for key, page_pairs in num_map.items():
            if key not in URL_MAP:
                log(f"[경고] 알 수 없는 분류 키: {key}")
                continue
            queries, title, html = fetch_page(URL_MAP[key], page_pairs, log)
            old_queries.extend(queries)
            if html:
                pages.append((title, html))

        new_queries = [get_query('대학규정', p) for _, p in pairs]
        self.after(0, self._run_done, logs, old_queries, new_queries, pages)

    def _run_done(self, logs, old_queries, new_queries, pages):
        self.run_btn.config(state=tk.NORMAL)

        self.pages = pages
        for title, _ in pages:
            self.page_lb.insert(tk.END, title)
        if pages:
            self.page_lb.selection_set(0)

        def append(text, tag=None):
            self.result_text.config(state=tk.NORMAL)
            if tag:
                self.result_text.insert(tk.END, text, tag)
            else:
                self.result_text.insert(tk.END, text)
            self.result_text.config(state=tk.DISABLED)

        if logs:
            append("-- 실행 로그 --\n", 'comment')
            for line in logs:
                append(line + '\n', 'log')
            append('\n')

        if old_queries:
            append("-- 기존 파일 비활성화 (FILE_DTLS = '') --\n", 'comment')
            for q in old_queries:
                append(q + '\n', 'sql')
            append('\n')

        if new_queries:
            append("-- 새 파일 활성화 (FILE_DTLS = '대학규정') --\n", 'comment')
            for q in new_queries:
                append(q + '\n', 'sql')

        if old_queries or new_queries:
            self._set_status("완료!", "green")
        else:
            self._set_status("결과 없음 – 번호를 확인해 주세요", "red")

    # ── 클립보드 ──────────────────────────────────────────────────

    def _copy(self):
        self.result_text.config(state=tk.NORMAL)
        text = self.result_text.get('1.0', tk.END).strip()
        self.result_text.config(state=tk.DISABLED)
        if not text:
            messagebox.showinfo("알림", "복사할 내용이 없습니다.")
            return
        # SQL 쿼리만 추출 (-- 로그/코멘트 제외)
        sql_lines = [l for l in text.splitlines() if l.startswith('UPDATE')]
        pyperclip.copy('\n'.join(sql_lines))
        self._set_status("SQL 쿼리가 클립보드에 복사되었습니다!", "green")

    def _copy_html(self):
        if not self.pages:
            messagebox.showinfo("알림", "수정된 콘텐츠 html이 없습니다.")
            return
        sel = self.page_lb.curselection()
        if not sel:
            messagebox.showinfo("알림", "복사할 페이지를 선택해 주세요.")
            return
        title, html = self.pages[sel[0]]
        pyperclip.copy(html)
        self._set_status(f"[{title}] 콘텐츠 html이 클립보드에 복사되었습니다!", "green")

    # ── 유틸 ─────────────────────────────────────────────────────

    def _set_status(self, msg, color="black"):
        self.status_var.set(msg)
        self.status_lbl.config(foreground=color)

    def _clear_result(self):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete('1.0', tk.END)
        self.result_text.config(state=tk.DISABLED)
        self.pages = []
        self.page_lb.delete(0, tk.END)


if __name__ == '__main__':
    app = App()
    app.mainloop()
