from PIL import Image
import os
import math
import abc # 추상 기본 클래스를 위한 모듈

# --- Receiver: 실제 작업을 수행하는 ImageSplitter 클래스 ---
class ImageSplitter:
    def __init__(self, input_image_path, output_dir, crop_width, crop_height):
        self.input_image_path = input_image_path
        self.output_dir = output_dir
        self.crop_width = crop_width
        self.crop_height = crop_height
        
        self.img = None
        self.original_width = 0
        self.original_height = 0
        self.base_name = ""
        self.extension = ""
        
        try:
            self.img = Image.open(input_image_path)
            self.original_width, self.original_height = self.img.size
            
            os.makedirs(output_dir, exist_ok=True)
            
            self.base_name, self.extension = self._get_file_basename_and_ext(input_image_path)

            print(f"원본 이미지 크기: {self.original_width}x{self.original_height}")
            print(f"자르려는 조각 기본 크기: {self.crop_width}x{self.crop_height}")

        except FileNotFoundError:
            raise FileNotFoundError(f"오류: '{input_image_path}' 파일을 찾을 수 없습니다. 경로를 확인해 주세요.")
        except Exception as e:
            raise Exception(f"이미지 로드 중 오류 발생: {e}")

    def _get_file_basename_and_ext(self, file_path):
        base_name_with_ext = os.path.basename(file_path)
        base_name, ext = os.path.splitext(base_name_with_ext)
        return base_name, ext.lower().replace('.', '')

    def _save_cropped_image(self, cropped_img, part_number):
        output_path = os.path.join(self.output_dir, 
                                   f"{self.base_name}_part_{part_number}.{self.extension}")
        cropped_img.save(output_path)
        print(f"이미지 저장 완료: {output_path}")

    # 커맨드에 의해 호출될 실제 작업 메서드들
    def split_horizontal(self):
        print("\n[가로 자르기 모드 시작]")
        if self.original_width % self.crop_width != 0:
            print("경고: 이미지의 가로 길이가 자르려는 가로 길이의 배수가 아닙니다. 마지막 이미지가 잘려나갈 수 있습니다.")
        
        num_splits = self.original_width // self.crop_width
        current_part = 0

        for i in range(num_splits):
            left = i * self.crop_width
            upper = 0
            right = (i + 1) * self.crop_width
            lower = self.original_height

            cropped_img = self.img.crop((left, upper, right, lower))
            current_part += 1
            self._save_cropped_image(cropped_img, current_part)

        print("모든 이미지 분할 및 저장 완료! (가로 자르기)")

    def split_vertical(self):
        print("\n[세로 자르기 모드 시작]")
        if self.original_height % self.crop_height != 0:
            print("경고: 이미지의 세로 길이가 자르려는 세로 길이의 배수가 아닙니다. 마지막 이미지가 잘려나갈 수 있습니다.")
        
        num_splits = self.original_height // self.crop_height
        current_part = 0

        for i in range(num_splits):
            left = 0
            upper = i * self.crop_height
            right = self.original_width
            lower = (i + 1) * self.crop_height

            cropped_img = self.img.crop((left, upper, right, lower))
            current_part += 1
            self._save_cropped_image(cropped_img, current_part)

        print("모든 이미지 분할 및 저장 완료! (세로 자르기)")

    def split_grid(self):
        print("\n[바둑판 자르기 모드 시작]")
        num_cols = math.ceil(self.original_width / self.crop_width)
        num_rows = math.ceil(self.original_height / self.crop_height)

        if self.original_width % self.crop_width != 0:
            print("경고: 이미지의 가로 길이가 자르려는 가로 길이의 배수가 아닙니다. 마지막 열의 이미지가 잘려나갈 수 있습니다.")
        if self.original_height % self.crop_height != 0:
            print("경고: 이미지의 세로 길이가 자르려는 세로 길이의 배수가 아닙니다. 마지막 행의 이미지가 잘려나갈 수 있습니다.")

        current_part = 0
        for r in range(num_rows):
            for c in range(num_cols):
                left = c * self.crop_width
                upper = r * self.crop_height
                right = min(self.original_width, (c + 1) * self.crop_width)
                lower = min(self.original_height, (r + 1) * self.crop_height)

                if right <= left or lower <= upper:
                    continue

                cropped_img = self.img.crop((left, upper, right, lower))
                current_part += 1
                self._save_cropped_image(cropped_img, current_part)

        print("모든 이미지 분할 및 저장 완료! (바둑판 자르기)")


# --- Command: 추상 커맨드 클래스 ---
@abc.abstractmethod
class Command(abc.ABC):
    def __init__(self, receiver):
        # 커맨드는 작업을 수행할 수신자 객체를 알고 있어야 합니다.
        self._receiver = receiver

    @abc.abstractmethod
    def execute(self):
        # 모든 구체 커맨드는 execute 메서드를 구현해야 합니다.
        pass

# --- Concrete Commands: 구체적인 작업 요청을 캡슐화하는 클래스들 ---
class HorizontalSplitCommand(Command):
    def execute(self):
        self._receiver.split_horizontal()

class VerticalSplitCommand(Command):
    def execute(self):
        self._receiver.split_vertical()

class GridSplitCommand(Command):
    def execute(self):
        self._receiver.split_grid()

# --- Invoker: 커맨드 객체를 받아 실행하는 부분 (main 블록이 Invoker 역할을 겸합니다) ---

# --- Client: 커맨드 객체를 생성하고, Receiver를 커맨드에 바인딩하며, Invoker에게 커맨드를 제공하는 부분 (main 블록이 Client 역할을 겸합니다) ---
if __name__ == "__main__":
    print("--- 이미지 분할 프로그램 ---")
    print("모드를 선택하세요:")
    print("1: 가로 자르기 (가로 방향으로 이미지를 분할)")
    print("2: 세로 자르기 (세로 방향으로 이미지를 분할)")
    print("3: 바둑판 자르기 (격자 모양으로 이미지를 분할)")

    while True:
        mode_input = input('모드 입력 (1, 2, 3): ')
        if mode_input in ['1', '2', '3']:
            break
        else:
            print("잘못된 입력입니다. 1, 2, 3 중 하나를 입력해 주세요.")

    input_file = input('원본 이미지 파일 경로를 입력하세요 (예: C:/image.png): ')
    output_folder = input('잘라낸 이미지를 저장할 폴더 경로를 입력하세요 (예: C:/output_images): ')
    
    target_width = int(input('각 조각의 목표 가로 크기를 입력하세요 (px): '))
    target_height = int(input('각 조각의 목표 세로 크기를 입력하세요 (px): '))

    try:
        # Receiver (ImageSplitter) 객체 생성
        splitter_receiver = ImageSplitter(input_file, output_folder, target_width, target_height)

        # Command 객체들을 모드 입력에 매핑하는 딕셔너리 생성
        # 여기서 Concrete Command 객체를 생성하고 Receiver를 바인딩합니다. (Client 역할)
        command_dispatch = {
            '1': HorizontalSplitCommand(splitter_receiver),
            '2': VerticalSplitCommand(splitter_receiver),
            '3': GridSplitCommand(splitter_receiver)
        }
        
        # Invoker 역할: 딕셔너리에서 선택된 커맨드 객체를 가져와 execute() 메서드를 호출합니다.
        selected_command = command_dispatch.get(mode_input)
        if selected_command:
            selected_command.execute() # 커맨드 실행
        else:
            print("오류: 정의되지 않은 모드입니다. 프로그램을 종료합니다.")


    except FileNotFoundError as e:
        print(f"오류 발생: {e}")
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        print("\n프로그램을 종료합니다.")
        input('Enter key to exit...')