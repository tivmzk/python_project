from pynput import keyboard
from pynput import mouse
import time
import threading
import os

class mouse_macro:
    is_working = False
    pos_list = []
    mouse_controller = mouse.Controller()
    speed = 5
    msg = ''
    cmt = ''

    def __init__(self):
        self.draw()
        self.run()

    def run(self):
        with keyboard.Listener(on_release=self.on_released) as listener:
            listener.join()

    def draw(self):
        os.system('cls')
        print('사용법')
        print('a : 입력 저장')
        print('r : 입력 초기화')
        print('v : 입력 리스트 보기')
        print('w : 일 시작')
        print('s : 일 정지')
        print('e : 나가기')
        print('+ : 속도 상승')
        print('- : 속도 저하')
        print()
        print(f'messsage : {self.msg}')
        print(f'comment : {self.cmt}')

    def set_des(self, msg='', cmt=''):
        if msg != 'pass':
            self.msg = msg
        if cmt != 'pass':
            self.cmt = cmt

    def work(self):
        while self.is_working:
            for pos in self.pos_list:
                time.sleep(self.speed * 0.1)
                if not self.is_working:
                    break
                self.mouse_controller.position = pos
                self.mouse_controller.click(mouse.Button.left, 1)

    def on_released(self, key):
        result = self.key_event(f'{key}'.strip("'"))
        self.draw()
        return result

    def speed_down(self):
        if self.speed < 10:
            self.speed += 1
            self.set_des('클릭 속도 감소', f'현재 속도 : {round(self.speed * 0.1, 1)}click/sec')

    def speed_up(self):
        if self.speed > 1:
            self.speed -= 1
            self.set_des('클릭 속도 상승', f'현재 속도 : {round(self.speed * 0.1, 1)}click/sec')

    def key_event(self, key):
        if key == 'e':
            self.set_des('나가기')
            self.is_working = False
            return False
        elif key == '+':
            self.speed_up()
        elif key == '-':
            self.speed_down()

        if self.is_working:
            if key == 's':
                self.set_des('일 중지')
                self.is_working = False
        else:
            if key == 'a':
                self.pos_list.append(self.mouse_controller.position)
                self.set_des('입력 저장', f'현재 : {self.pos_list}')
            elif key == 'w':
                self.set_des('일 시작', f'현재 : {self.pos_list}')
                self.is_working = True
                th = threading.Thread(target=self.work)
                th.daemon = True
                th.start()
            elif key == 'r':
                self.set_des('입력 리스트 초기화')
                self.pos_list.clear()
            elif key == 'v':
                self.set_des('입력 리스트 보기', f'현재 : {self.pos_list}')

        return True

if __name__ == '__main__':
    mouse_macro()
    input('프로그램을 종료하려면 Enter 키를 누르세요...')