import tkinter as tk
from tkinter import filedialog, messagebox
import mecro_system
import threading


class Program:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Calculate Mobility & Threshold Voltage")
        self.window.resizable(False, False)

        self.system = mecro_system.System(self)

        self.folder_path = ''
        self.result_folder_path = ''
        self.is_working = False

        self.create_widgets()
        self.window.mainloop()

    def create_widgets(self):
        # 작업 폴더 선택
        tk.Button(self.window, text='작업 폴더 지정', command=self.select_folder).grid(row=0, column=0)
        self.folder_label = tk.Label(self.window, text='작업 폴더를 지정해 주세요')
        self.folder_label.grid(row=0, column=1)

        # 결과 폴더 선택
        tk.Button(self.window, text='결과 폴더 지정', command=self.select_result_folder).grid(row=1, column=0)
        self.result_label = tk.Label(self.window, text='결과 폴더를 지정해 주세요')
        self.result_label.grid(row=1, column=1)

        # 실행 버튼
        tk.Button(self.window, text='실행', command=self.execute, width=10).grid(row=1, column=2)

        # 진행 상태 표시
        self.progress_var = tk.StringVar(value='대기 중')
        tk.Label(self.window, textvariable=self.progress_var).grid(row=2, column=2)

        # 입력 필드 및 레이블
        self.create_input_fields()

        # 도움말 버튼
        tk.Button(self.window, text='설명', command=self.show_help, width=10).grid(row=0, column=2, columnspan=2)

    def create_input_fields(self):
        labels = ['Width', 'Length', 'Capacitance', 'FV', 'Point Count']
        self.entries = {}

        for i, label in enumerate(labels):
            tk.Label(self.window, text=label).grid(row=i + 2, column=0)
            entry = tk.Entry(self.window)
            entry.grid(row=i + 2, column=1)
            self.entries[label] = entry

    def select_folder(self):
        self.folder_path = filedialog.askdirectory(title='작업 폴더 선택')
        self.folder_label.config(text=self.folder_path or '작업 폴더를 지정해 주세요')

    def select_result_folder(self):
        self.result_folder_path = filedialog.askdirectory(title='결과 폴더 선택')
        self.result_label.config(text=self.result_folder_path or '결과 폴더를 지정해 주세요')

    def execute(self):
        if self.validate_inputs() and not self.is_working:
            self.is_working = True
            threading.Thread(target=self.run_calculation).start()

    def validate_inputs(self):
        if not self.folder_path or not self.result_folder_path:
            messagebox.showwarning('주의', '작업 및 결과 폴더를 지정해 주세요.')
            return False
        return True

    def run_calculation(self):
        try:
            self.update_progress('작업 중...')
            params = {label: float(entry.get()) for label, entry in self.entries.items()}
            self.system.set_params(**params)  # Unpacking dictionary to set parameters
            result = self.system.start(self.folder_path, self.result_folder_path)
            self.update_progress('작업 완료!' if result else '작업 실패')
        except Exception as e:
            messagebox.showerror('에러', str(e))
            self.update_progress('작업 실패')
        finally:
            self.is_working = False

    def update_progress(self, message):
        self.progress_var.set(message)

    def show_help(self):
        messagebox.showinfo('정보', '필수조건\n 1. 작업 파일이 csv여야함.\n 2. N열에 ID, O열에 VG, P열에 IG가 있는 양식이어야 함.(기본 양식)')


if __name__ == '__main__':
    Program()
