import tkinter as tk
from tkinter import ttk, messagebox
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


def get_query(dtl, file_url):
    return f"UPDATE TSA_ATCH_FILE_DETAIL SET FILE_DTLS = '{dtl}' WHERE FILE_STRE_COURS = '{file_url}';"


def fetch_queries(url, file_num_list, log):
    try:
        log(f"[조회] {url}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        all_td = soup.select('.tbl_st td')

        result = []
        for file_num in file_num_list:
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
                break
            if not found:
                log(f"  ✗ {file_num} 미발견")
        return result
    except Exception as e:
        log(f"[오류] {e}")
        return []


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("대전대 규정 파일 쿼리 생성기")
        self.geometry("780x740")
        self.minsize(620, 540)
        self._build_ui()

    def _build_ui(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # ── 1. 기존 파일 번호 ─────────────────────────────────────
        num_frame = ttk.LabelFrame(
            main,
            text="① 기존 파일 번호  (예: 1-0-1 / 3-1-2_1 기구표 / 3-1-2_2 직제규정)",
            padding=8
        )
        num_frame.pack(fill=tk.X, padx=4, pady=4)

        inp_row = ttk.Frame(num_frame)
        inp_row.pack(fill=tk.X)
        ttk.Label(inp_row, text="번호:").pack(side=tk.LEFT)
        self.num_var = tk.StringVar()
        self.num_entry = ttk.Entry(inp_row, textvariable=self.num_var, width=14)
        self.num_entry.pack(side=tk.LEFT, padx=4)
        self.num_entry.bind('<Return>', lambda _: self._add_num())
        ttk.Button(inp_row, text="추가", command=self._add_num).pack(side=tk.LEFT)

        list_row = ttk.Frame(num_frame)
        list_row.pack(fill=tk.X, pady=(6, 0))
        self.num_lb = tk.Listbox(list_row, height=4, selectmode=tk.SINGLE, activestyle='dotbox')
        ns = ttk.Scrollbar(list_row, orient=tk.VERTICAL, command=self.num_lb.yview)
        self.num_lb.config(yscrollcommand=ns.set)
        self.num_lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ns.pack(side=tk.LEFT, fill=tk.Y)
        nb = ttk.Frame(list_row)
        nb.pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(nb, text="삭제", command=self._del_num, width=8).pack(pady=1)
        ttk.Button(nb, text="전체 삭제", command=lambda: self.num_lb.delete(0, tk.END), width=8).pack(pady=1)

        # ── 2. 새 파일 경로 ───────────────────────────────────────
        path_frame = ttk.LabelFrame(
            main,
            text="② 새 파일 경로  (예: /upload/cntntsFile/dju/doc_xxx.pdf)",
            padding=8
        )
        path_frame.pack(fill=tk.X, padx=4, pady=4)

        path_inp = ttk.Frame(path_frame)
        path_inp.pack(fill=tk.X)
        ttk.Label(path_inp, text="경로:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(path_inp, textvariable=self.path_var)
        self.path_entry.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)
        self.path_entry.bind('<Return>', lambda _: self._add_path())
        ttk.Button(path_inp, text="추가", command=self._add_path).pack(side=tk.LEFT)

        path_list = ttk.Frame(path_frame)
        path_list.pack(fill=tk.X, pady=(6, 0))
        self.path_lb = tk.Listbox(path_list, height=4, selectmode=tk.SINGLE, activestyle='dotbox')
        ps = ttk.Scrollbar(path_list, orient=tk.VERTICAL, command=self.path_lb.yview)
        phs = ttk.Scrollbar(path_list, orient=tk.HORIZONTAL, command=self.path_lb.xview)
        self.path_lb.config(yscrollcommand=ps.set, xscrollcommand=phs.set)
        phs.pack(side=tk.BOTTOM, fill=tk.X)
        self.path_lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ps.pack(side=tk.LEFT, fill=tk.Y)
        pb = ttk.Frame(path_list)
        pb.pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(pb, text="삭제", command=self._del_path, width=8).pack(pady=1)
        ttk.Button(pb, text="전체 삭제", command=lambda: self.path_lb.delete(0, tk.END), width=8).pack(pady=1)

        # ── 3. 실행 ───────────────────────────────────────────────
        run_row = ttk.Frame(main)
        run_row.pack(fill=tk.X, padx=4, pady=6)
        self.run_btn = ttk.Button(run_row, text="쿼리 생성 실행", command=self._run, width=18)
        self.run_btn.pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="")
        self.status_lbl = ttk.Label(run_row, textvariable=self.status_var)
        self.status_lbl.pack(side=tk.LEFT, padx=10)

        # ── 4. 결과 ───────────────────────────────────────────────
        result_frame = ttk.LabelFrame(main, text="③ 생성된 쿼리", padding=8)
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

    # ── 파일 번호 ────────────────────────────────────────────────

    def _add_num(self):
        num = self.num_var.get().strip()
        if not num:
            return
        if num == '3-1-2':
            self._ask_312()
            return
        self.num_lb.insert(tk.END, num)
        self.num_var.set('')
        self.num_entry.focus()

    def _ask_312(self):
        dlg = tk.Toplevel(self)
        dlg.title("3-1-2 유형 선택")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.geometry("240x100")
        ttk.Label(dlg, text="어떤 3-1-2를 추가할까요?").pack(pady=12)
        row = ttk.Frame(dlg)
        row.pack()

        def pick(val):
            self.num_lb.insert(tk.END, f"3-1-2_{val}")
            self.num_var.set('')
            dlg.destroy()
            self.num_entry.focus()

        ttk.Button(row, text="1 - 기구표",   command=lambda: pick('1'), width=12).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="2 - 직제규정", command=lambda: pick('2'), width=12).pack(side=tk.LEFT, padx=4)

    def _del_num(self):
        sel = self.num_lb.curselection()
        if sel:
            self.num_lb.delete(sel[0])

    # ── 새 파일 경로 ─────────────────────────────────────────────

    def _add_path(self):
        p = self.path_var.get().strip()
        if not p:
            return
        self.path_lb.insert(tk.END, p)
        self.path_var.set('')
        self.path_entry.focus()

    def _del_path(self):
        sel = self.path_lb.curselection()
        if sel:
            self.path_lb.delete(sel[0])

    # ── 실행 ─────────────────────────────────────────────────────

    def _run(self):
        file_nums = list(self.num_lb.get(0, tk.END))
        if not file_nums:
            messagebox.showwarning("입력 필요", "기존 파일 번호를 하나 이상 입력해 주세요.")
            return
        self.run_btn.config(state=tk.DISABLED)
        self._set_status("조회 중...", "blue")
        self._clear_result()
        new_paths = list(self.path_lb.get(0, tk.END))
        threading.Thread(target=self._run_bg, args=(file_nums, new_paths), daemon=True).start()

    def _run_bg(self, file_nums, new_paths):
        logs = []

        def log(msg):
            logs.append(msg)

        num_map = {}
        for fn in file_nums:
            key = fn.split('-')[0]
            num_map.setdefault(key, []).append(fn)

        old_queries = []
        for key, nums in num_map.items():
            if key not in URL_MAP:
                log(f"[경고] 알 수 없는 분류 키: {key}")
                continue
            old_queries.extend(fetch_queries(URL_MAP[key], nums, log))

        new_queries = [get_query('대학규정', p) for p in new_paths]
        self.after(0, self._run_done, logs, old_queries, new_queries)

    def _run_done(self, logs, old_queries, new_queries):
        self.run_btn.config(state=tk.NORMAL)

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

    # ── 유틸 ─────────────────────────────────────────────────────

    def _set_status(self, msg, color="black"):
        self.status_var.set(msg)
        self.status_lbl.config(foreground=color)

    def _clear_result(self):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete('1.0', tk.END)
        self.result_text.config(state=tk.DISABLED)


if __name__ == '__main__':
    app = App()
    app.mainloop()
