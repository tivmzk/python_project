from tkinter import Tk, Button, Label, simpledialog
from threading import Thread
import tkinter
import pyautogui
import keyboard
import time

class AutoManager:
    def __init__(self, win):
        self.is_auto = False
        self.is_wating = False
        self.use_wating = True
        self.click_per_sec = 3.0
        self.MAX = 100
        self.MIN = 1
        self.start_key = '`'
        self.win = win

        self.btn_start = Button(win, width=10, height=1)
        self.btn_start.config(text="자동 클릭 시작")
        self.btn_start.config(command=self.auto_click_start)

        self.btn_click_per_sec_up = Button(win)
        self.btn_click_per_sec_up.config(text="▲")
        self.btn_click_per_sec_up.config(command=self.click_per_sec_up)
        self.btn_click_per_sec_up.config(repeatdelay=500, repeatinterval=80)

        self.btn_click_per_sec_down = Button(win)
        self.btn_click_per_sec_down.config(text="▼")
        self.btn_click_per_sec_down.config(command=self.click_per_sec_down)
        self.btn_click_per_sec_down.config(repeatdelay=500, repeatinterval=80)

        self.lb_click_per_sec = Label(win)
        self.lb_click_per_sec.config(text=str(self.click_per_sec)+" click/sec")

        self.lb_key_info = Label(win)
        self.lb_key_info.config(text=self.start_key+" = 시작, 중지")

        self.btn_key_config = Button(win, text="키 설정", command=self.set_start_key, width=7, height=4)

        self.btn_use_waiting = Button(win)
        self.btn_use_waiting.config(text="딜레이 사용중", command=self.waiting_setting)

        self.btn_key_config.grid(column=3, row=0, padx=10, rowspan=2)
        self.lb_key_info.grid(column=2, row=0, padx=10)
        self.btn_use_waiting.grid(column=2,row=1, pady=10)
        self.btn_start.grid(column=0, row=0, padx=10, pady=10)
        self.btn_click_per_sec_up.grid(column=1, row=0)
        self.btn_click_per_sec_down.grid(column=1, row=1)
        self.lb_click_per_sec.grid(column=0, row=1)

        t = Thread(target=self.run)
        t.daemon = True
        t.start()

    def set_start_key(self):
        self.is_wating = True
        input_key = simpledialog.askstring('키 입력', '단축키로 설정할 키를 입력하세요.')
        if input_key != None:
            self.start_key = input_key
        self.lb_key_info.config(text=self.start_key+" = 시작, 중지")
        self.is_wating = False

    def waiting_setting(self):
        if self.is_wating or self.is_auto:
            return
            
        self.use_wating = not self.use_wating

        if self.use_wating:
            self.btn_use_waiting.config(text="딜레이 사용중")
        else:
            self.btn_use_waiting.config(text="딜레이 안씀")

    def click_per_sec_up(self):
        if self.is_auto:
            return

        if self.click_per_sec == self.MAX:
            return

        self.change_click_per_sec(1)

    def click_per_sec_down(self):
        if self.is_auto:
            return

        if self.click_per_sec == self.MIN:
            return

        self.change_click_per_sec(-1)

    def auto_click_start(self):
        if self.is_wating or self.is_auto:
            return

        self.is_auto = True
        t = Thread(target=self.auto_click)
        t.daemon = True
        t.start()

    def auto_click_stop(self):
        if not self.is_auto or self.is_wating:
            return

        self.is_auto = False
        self.btn_start.config(text="자동 클릭 시작", command=self.auto_click_start)

    def auto_click(self):
        if self.use_wating:
            self.is_wating = True

            for count in reversed(range(0, 4)):
                self.btn_start.config(text=str(count))
                time.sleep(1)

            self.is_wating = False

        self.btn_start.config(text="중지", command=self.auto_click_stop)
        pyautogui.PAUSE = 1.0 / self.click_per_sec

        while self.is_auto:
            pyautogui.click()

    def change_click_per_sec(self, value):
        self.click_per_sec += value
        self.lb_click_per_sec.config(text=str(self.click_per_sec)+" click/sec")

    def run(self):
        key_down = False
        while True:
            time.sleep(0.033)
            # if win32api.GetKeyState(0x1B) < 0:
            #     self.auto_click_stop()

            if keyboard.is_pressed(self.start_key):
                if key_down:
                    continue
                key_down = True

                if self.is_auto:
                    self.auto_click_stop()
                else:
                    self.auto_click_start()
            elif keyboard.is_pressed("+"):
                self.click_per_sec_up()
            elif keyboard.is_pressed("-"):
                self.click_per_sec_down()
            
            if not keyboard.is_pressed(self.start_key):
                if not key_down:
                    continue
                key_down = False

# 설정
win = Tk()

win.title("Auto Mouse")
win.option_add("*Font", "맑은고딕 10")
win.resizable(False, False)

AutoManager(win)

win.mainloop()