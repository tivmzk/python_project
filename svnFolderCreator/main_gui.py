import os
import shutil
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


def convert_svn_paths(raw_text):
    """JS btnFunc14 로직과 동일: 원본 SVN 경로를 배포용 경로로 변환"""
    results = []
    for v in raw_text.splitlines():
        if not v.strip():
            continue
        v_norm = v.replace('\\', '/')
        ext = v_norm[v_norm.rfind('.'):]

        if ext == '.java':
            idx = v_norm.find('/egovframework')
            last_dot = v_norm.rfind('.')
            result = '/webapp/WEB-INF/classes' + v_norm[idx:last_dot] + '.class'
        elif ext == '.xml':
            idx = v_norm.find('/egovframework')
            result = '/webapp/WEB-INF/classes' + v_norm[idx:]
        else:
            idx = v_norm.find('/webapp/')
            result = v_norm[idx:]

        if v_norm.startswith('D '):
            result = '-' + result

        results.append(result)
    return '\n'.join(results)


def create_folder(project_folder, result_folder, input_data, log):
    project_folder = project_folder[:-len(os.path.sep + 'webapp')]

    if not os.path.exists(result_folder):
        os.makedirs(result_folder)
        log("결과 폴더 생성 완료")

    for input in input_data:
        if input[0] == "-":
            continue
        input_path = os.path.dirname(input)
        key = os.path.basename(input)
        src_path = os.path.join(project_folder + input_path, key)
        if not os.path.exists(src_path):
            log(f"파일이 없습니다. : {src_path}")
            continue
        dst_path = os.path.join(result_folder + input_path, key)
        if not os.path.exists(os.path.dirname(dst_path)):
            os.makedirs(os.path.dirname(dst_path))
        shutil.copy(src_path, dst_path)
        log(f"복사 완료 : {dst_path}")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SVN Folder Creator")
        self.resizable(True, True)
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        # 프로젝트 폴더
        frm1 = ttk.LabelFrame(self, text="프로젝트 폴더 경로 (webapp 폴더까지)")
        frm1.pack(fill="x", **pad)
        self.project_var = tk.StringVar()
        ttk.Entry(frm1, textvariable=self.project_var, width=60).pack(side="left", fill="x", expand=True, padx=(5, 2), pady=5)
        ttk.Button(frm1, text="찾아보기", command=self._browse_project).pack(side="left", padx=(0, 5), pady=5)

        # 결과 폴더
        frm2 = ttk.LabelFrame(self, text="결과 저장 폴더 경로")
        frm2.pack(fill="x", **pad)
        self.result_var = tk.StringVar()
        ttk.Entry(frm2, textvariable=self.result_var, width=60).pack(side="left", fill="x", expand=True, padx=(5, 2), pady=5)
        ttk.Button(frm2, text="찾아보기", command=self._browse_result).pack(side="left", padx=(0, 5), pady=5)

        # 원본 경로 변환 입력
        frm_conv = ttk.LabelFrame(self, text="원본 SVN 경로 입력 (변환 후 아래 목록으로 이동)")
        frm_conv.pack(fill="both", expand=True, **pad)
        self.raw_text = tk.Text(frm_conv, height=6, font=("Consolas", 10))
        raw_scroll = ttk.Scrollbar(frm_conv, command=self.raw_text.yview)
        self.raw_text.configure(yscrollcommand=raw_scroll.set)
        self.raw_text.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)
        raw_scroll.pack(side="left", fill="y", padx=(0, 5), pady=5)
        ttk.Button(self, text="경로 변환하여 목록에 추가 ▼", command=self._convert).pack(pady=(0, 2))

        # SVN 경로 입력
        frm3 = ttk.LabelFrame(self, text="SVN 파일 경로 목록 (한 줄에 하나씩, '-'로 시작하면 건너뜀)")
        frm3.pack(fill="both", expand=True, **pad)
        self.input_text = tk.Text(frm3, height=10, font=("Consolas", 10))
        scroll = ttk.Scrollbar(frm3, command=self.input_text.yview)
        self.input_text.configure(yscrollcommand=scroll.set)
        self.input_text.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)
        scroll.pack(side="left", fill="y", padx=(0, 5), pady=5)

        # 실행 버튼
        self.run_btn = ttk.Button(self, text="실행", command=self._run)
        self.run_btn.pack(pady=(0, 5))

        # 로그 출력
        frm4 = ttk.LabelFrame(self, text="로그")
        frm4.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(frm4, height=8, state="disabled", font=("Consolas", 10), background="#f5f5f5")
        log_scroll = ttk.Scrollbar(frm4, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)
        log_scroll.pack(side="left", fill="y", padx=(0, 5), pady=5)

    def _browse_project(self):
        path = filedialog.askdirectory(title="프로젝트 webapp 폴더 선택")
        if path:
            self.project_var.set(os.path.normpath(path))

    def _browse_result(self):
        path = filedialog.askdirectory(title="결과 저장 폴더 선택")
        if path:
            self.result_var.set(os.path.normpath(path))

    def _convert(self):
        raw = self.raw_text.get("1.0", "end").strip()
        if not raw:
            messagebox.showwarning("알림", "변환할 원본 경로를 입력하세요.")
            return
        converted = convert_svn_paths(raw)
        # 기존 목록 끝에 이어 붙이기 (중복 개행 방지)
        current = self.input_text.get("1.0", "end").strip()
        new_content = (current + "\n" + converted).strip() + "\n"
        self.input_text.delete("1.0", "end")
        self.input_text.insert("1.0", new_content)
        self.raw_text.delete("1.0", "end")

    def _log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _run(self):
        project_folder = self.project_var.get().strip()
        result_folder = self.result_var.get().strip()
        raw = self.input_text.get("1.0", "end").strip()

        if not project_folder:
            messagebox.showerror("오류", "프로젝트 폴더 경로를 입력하세요.")
            return
        if not os.path.normpath(project_folder).endswith('webapp'):
            messagebox.showerror("오류", "경로를 프로젝트의 webapp 폴더로 입력하세요.")
            return
        if not result_folder:
            messagebox.showerror("오류", "결과 저장 폴더 경로를 입력하세요.")
            return
        if not raw:
            messagebox.showerror("오류", "SVN 파일 경로를 하나 이상 입력하세요.")
            return

        input_data = [line for line in raw.splitlines() if line.strip()]

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        self.run_btn.configure(state="disabled")

        def worker():
            try:
                create_folder(project_folder, result_folder, input_data, self._log)
                self._log("프로그램이 완료되었습니다.")
            except Exception as e:
                self._log(f"오류 발생: {e}")
            finally:
                self.run_btn.configure(state="normal")

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
