import tkinter
from tkinter import filedialog
import tkinter.messagebox
import mecro_system
import threading
import time

class Program:
  def __init__(self):
    self.window = tkinter.Tk()

    self.window.title("Calculate Mobility & Threshold Voltage")
    self.window.resizable(False, False)

    self.system = mecro_system.system(self)

    self.folder_path = ''
    self.result_folder_path = ''

    self.btn_folder_path = tkinter.Button(self.window, text='작업 폴더 지정', command=self.search_dir_folder)
    self.btn_folder_path.grid(row=0, column=0)

    self.txt_folder_path = tkinter.StringVar()
    self.txt_folder_path.set('작업 폴더를 지정해 주세요')

    self.lb_folder_path = tkinter.Label(self.window, textvariable=self.txt_folder_path)
    self.lb_folder_path.grid(row=0, column=1)

    self.btn_result_path = tkinter.Button(self.window, text='결과 폴더 지정', command=self.search_dir_result)
    self.btn_result_path.grid(row=1, column=0)

    self.txt_result_path = tkinter.StringVar()
    self.txt_result_path.set('결과 폴더를 지정해 주세요')

    self.lb_result_path = tkinter.Label(self.window, textvariable=self.txt_result_path)
    self.lb_result_path.grid(row=1, column=1)

    self.btn_help = tkinter.Button(self.window, text='설명', command=self.help, width=10)
    self.btn_help.grid(row=0, column=2, columnspan=2)

    self.btn_execute = tkinter.Button(self.window, text='실행', command=self.execute, width=10)
    self.btn_execute.grid(row=1, column=2, columnspan=2)

    self.txt_progress = tkinter.StringVar()
    self.txt_progress.set('대기 중')

    self.lb_progress = tkinter.Label(self.window, textvariable=self.txt_progress)
    self.lb_progress.grid(row=2, column=2, rowspan=4, columnspan=2)

    self.lb_W = tkinter.Label(self.window, text='Width')
    self.lb_W.grid(row=2, column=0)

    self.lb_L = tkinter.Label(self.window, text="Length")
    self.lb_L.grid(row=3, column=0)

    self.lb_C = tkinter.Label(self.window, text='Capacitance')
    self.lb_C.grid(row=4, column=0)

    self.lb_FV = tkinter.Label(self.window, text='FV')
    self.lb_FV.grid(row=5, column=0)

    self.et_W = tkinter.Entry(self.window)
    self.et_W.insert(0, str(self.system.get_W()))
    self.et_W.grid(row=2, column=1)

    self.et_L = tkinter.Entry(self.window)
    self.et_L.insert(0, str(self.system.get_L()))
    self.et_L.grid(row=3, column=1)

    self.et_C = tkinter.Entry(self.window)
    self.et_C.insert(0, str(self.system.get_C()))
    self.et_C.grid(row=4, column=1)

    self.et_FV = tkinter.Entry(self.window)
    self.et_FV.insert(0, str(self.system.get_FV()))
    self.et_FV.grid(row=5, column=1)

    self.lb_point = tkinter.Label(self.window, text='Point Count')
    self.lb_point.grid(row=6, column=0)

    self.et_point = tkinter.Entry(self.window)
    self.et_point.insert(0, str(self.system.get_point_count()))
    self.et_point.grid(row=6, column=1)

    self.cb_setting_fv_var = tkinter.BooleanVar()
    self.cb_setting_fv_var.set(False)
    self.cb_setting_fv = tkinter.Checkbutton(self.window, var=self.cb_setting_fv_var)
    self.cb_setting_fv.grid(row=6, column=3)

    self.lb_setting_fv = tkinter.Label(self.window, text='N타입')
    self.lb_setting_fv.grid(row=6, column=2)

    self.is_working = False

    self.thread = threading.Thread(target=self.work)

  def search_dir_folder(self):
    self.folder_path = filedialog.askdirectory(parent=self.window, initialdir='/', title='Please select a directory')
    self.txt_folder_path.set(self.folder_path)

  def search_dir_result(self):
    self.result_path = filedialog.askdirectory(parent=self.window, initialdir='/', title='Please select a directory')
    self.txt_result_path.set(self.result_path)

  def execute(self):
    if(self.folder_path == '' or self.result_path == '' or self.is_working):
      tkinter.messagebox.showwarning('주의', '입력을 제대로 해주세요.')
      return

    self.thread = threading.Thread(target=self.work)
    self.thread.start()
    
  def work(self):
    self.btn_execute['state'] = tkinter.DISABLED

    self.system.set_L(int(self.et_L.get()))
    self.system.set_W(int(self.et_W.get()))
    self.system.set_C(float(self.et_C.get()))
    self.system.set_FV(int(self.et_FV.get()))
    self.system.set_point_count(int(self.et_point.get()))
    self.system.set_is_n_type(self.cb_setting_fv_var.get())

    self.is_working = True
    self.txt_progress.set('작업 중...')
    result = self.system.start(self.folder_path, self.result_path)

    if result:
      self.txt_progress.set('작업 완료!')

      time.sleep(1)

      self.txt_progress.set('대기 중')
      self.is_working = False
      self.btn_execute['state'] = tkinter.NORMAL
    else:
      self.error()

  def help(self):
    tkinter.messagebox.showinfo('정보', '필수조건\n 1. 작업 파일이 csv여야함.\n 2. N열에 ID, O열에 VG, P열에 IG가 있는 양식이어야 함.(기본 양식)\n\n *단위 차원\n Width: Channel Width [um]\n Length: Channel Length [um]\n Capacitance: Dielectric Capacitance[F/cm^2]\n FV: On current\n ex) p-type> 20~-40V의 경우 -40, n-type> -20~40V의 경우 40\n Point Count: 기울기 및 절편을 구하는데 사용할 점의 갯수\n ex) 5개 > -40V,-39V,-38V,-37V,-36V(1V step으로 측정했을 시)\n\n 출력 파일에서 mobility 및 다른 팩터가 0 또는 blank로 표시될 때에는\n FV나 ntype 체크, 데이터 파일을 열어둔 상태라 수정이 되지 않는 상태에서 실행을 한 것이므로,\n 다시 확인할 것.')

  def run(self):
    self.window.mainloop()
  
  def error(self, msg):
    self.txt_progress.set('작업 실패')
    tkinter.messagebox.showerror('에러', msg)
    time.sleep(1)
    self.txt_progress.set('대기 중')
    self.is_working = False
    self.btn_execute['state'] = tkinter.NORMAL


if __name__ == '__main__':
  Program().run()