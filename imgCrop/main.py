from PIL import Image
import os
import math

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
            # 이미지 열기
            self.img = Image.open(input_image_path)
            self.original_width, self.original_height = self.img.size
            
            # 출력 디렉토리 생성
            os.makedirs(output_dir, exist_ok=True)
            
            # 파일 이름 및 확장자 분리
            self.base_name, self.extension = self._get_file_basename_and_ext(input_image_path)

            print(f"원본 이미지 크기: {self.original_width}x{self.original_height}")
            print(f"자르려는 조각 기본 크기: {self.crop_width}x{self.crop_height}")

        except FileNotFoundError:
            raise FileNotFoundError(f"오류: '{input_image_path}' 파일을 찾을 수 없습니다. 경로를 확인해 주세요.")
        except Exception as e:
            raise Exception(f"이미지 로드 중 오류 발생: {e}")

    # 이미지 경로에서 기본 이름과 확장자를 분리하는 내부 헬퍼 함수
    def _get_file_basename_and_ext(self, file_path):
        base_name_with_ext = os.path.basename(file_path)
        base_name, ext = os.path.splitext(base_name_with_ext)
        return base_name, ext.lower().replace('.', '') # 확장자는 . 없이 소문자로 반환

    # 잘라낸 이미지를 저장하는 내부 헬퍼 함수
    def _save_cropped_image(self, cropped_img, part_number):
        output_path = os.path.join(self.output_dir, 
                                   f"{self.base_name}_part_{part_number}.{self.extension}")
        cropped_img.save(output_path)
        print(f"이미지 저장 완료: {output_path}")

    # 1. 가로 자르기 모드
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
            lower = self.original_height # 가로 자르기는 높이는 원본 이미지 높이 그대로

            cropped_img = self.img.crop((left, upper, right, lower))
            current_part += 1
            self._save_cropped_image(cropped_img, current_part)

        print("모든 이미지 분할 및 저장 완료! (가로 자르기)")

    # 2. 세로 자르기 모드
    def split_vertical(self):
        print("\n[세로 자르기 모드 시작]")
        if self.original_height % self.crop_height != 0:
            print("경고: 이미지의 세로 길이가 자르려는 세로 길이의 배수가 아닙니다. 마지막 이미지가 잘려나갈 수 있습니다.")
        
        num_splits = self.original_height // self.crop_height
        current_part = 0

        for i in range(num_splits):
            left = 0
            upper = i * self.crop_height
            right = self.original_width # 세로 자르기는 너비는 원본 이미지 너비 그대로
            lower = (i + 1) * self.crop_height

            cropped_img = self.img.crop((left, upper, right, lower))
            current_part += 1
            self._save_cropped_image(cropped_img, current_part)

        print("모든 이미지 분할 및 저장 완료! (세로 자르기)")

    # 3. 바둑판 자르기 모드
    def split_grid(self):
        print("\n[바둑판 자르기 모드 시작]")
        # 바둑판 모양으로 몇 줄, 몇 칸으로 나뉘는지 계산
        num_cols = math.ceil(self.original_width / self.crop_width)
        num_rows = math.ceil(self.original_height / self.crop_height)

        if self.original_width % self.crop_width != 0:
            print("경고: 이미지의 가로 길이가 자르려는 가로 길이의 배수가 아닙니다. 마지막 열의 이미지가 잘려나갈 수 있습니다.")
        if self.original_height % self.crop_height != 0:
            print("경고: 이미지의 세로 길이가 자르려는 세로 길이의 배수가 아닙니다. 마지막 행의 이미지가 잘려나갈 수 있습니다.")

        current_part = 0
        for r in range(num_rows): # 행
            for c in range(num_cols): # 열
                left = c * self.crop_width
                upper = r * self.crop_height
                # 이미지가 지정된 크기보다 작을 경우를 대비하여 min 함수 사용
                right = min(self.original_width, (c + 1) * self.crop_width)
                lower = min(self.original_height, (r + 1) * self.crop_height)

                if right <= left or lower <= upper: # 유효하지 않은 자르기 영역 건너뛰기
                    continue

                cropped_img = self.img.crop((left, upper, right, lower))
                current_part += 1
                self._save_cropped_image(cropped_img, current_part)

        print("모든 이미지 분할 및 저장 완료! (바둑판 자르기)")

# --- 메인 실행 부분 ---
if __name__ == "__main__":
    print("--- 이미지 분할 프로그램 ---")
    print("모드를 선택하세요:")
    print("1: 가로 자르기 (가로 방향으로 이미지를 분할)")
    print("2: 세로 자르기 (세로 방향으로 이미지를 분할)")
    print("3: 바둑판 자르기 (격자 모양으로 이미지를 분할)")

    while True:
        mode = input('모드 입력 (1, 2, 3): ')
        if mode in ['1', '2', '3']:
            break
        else:
            print("잘못된 입력입니다. 1, 2, 3 중 하나를 입력해 주세요.")

    input_file = input('원본 이미지 파일 경로를 입력하세요 (예: C:/image.png): ')
    output_folder = input('잘라낸 이미지를 저장할 폴더 경로를 입력하세요 (예: C:/output_images): ')
    
    # 가로/세로 자르기 모드에서도 바둑판 자르기를 고려하여, 잘라낼 '조각'의 목표 크기를 모두 입력받도록 합니다.
    # 각 분할 메서드 내에서는 이 중 필요한 값만 사용합니다.
    target_width = int(input('각 조각의 목표 가로 크기를 입력하세요 (px): '))
    target_height = int(input('각 조각의 목표 세로 크기를 입력하세요 (px): '))

    try:
        # ImageSplitter 객체 생성
        splitter = ImageSplitter(input_file, output_folder, target_width, target_height)

        if mode == '1':
            splitter.split_horizontal()
        elif mode == '2':
            splitter.split_vertical()
        elif mode == '3':
            splitter.split_grid()

    except FileNotFoundError as e:
        print(f"오류 발생: {e}")
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        print("\n프로그램을 종료합니다.")
        input("종료하려면 Enter 키를 누르세요...")