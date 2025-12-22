from PIL import Image
import os

def split_long_image_python(input_image_path, output_dir, crop_width, crop_height):
    try:
        # 이미지 열기
        img = Image.open(input_image_path)
        original_width, original_height = img.size

        # 출력 디렉토리가 없으면 생성
        os.makedirs(output_dir, exist_ok=True)

        print(f"원본 이미지 크기: {original_width}x{original_height}")
        print(f"자르려는 크기: {crop_width}x{crop_height}")

        # 몇 개로 잘릴지 계산 (세로 방향)
        # 이미지의 높이가 crop_height로 나누어 떨어지지 않을 경우를 대비하여 math.ceil을 사용할 수도 있지만,
        # 여기서는 정확히 crop_height 배수로 떨어지는 경우만 처리한다고 가정합니다.
        if original_height % crop_height != 0:
            print("경고: 이미지의 높이가 자르려는 높이의 배수가 아닙니다. 마지막 이미지가 잘려나갈 수 있습니다.")
        
        num_splits = original_height // crop_height

        for i in range(num_splits):
            # 자를 영역 정의 (left, upper, right, lower)
            # x 좌표는 0부터 시작해서 crop_width까지, y 좌표는 i * crop_height 부터 (i+1) * crop_height 까지
            left = 0
            upper = i * crop_height
            right = crop_width
            lower = (i + 1) * crop_height

            cropped_img = img.crop((left, upper, right, lower))
            
            # 저장할 파일 이름과 경로 설정
            # 원본 파일명에서 확장자를 제외하고 "_part_N.png" 형식으로 저장
            base_name = os.path.splitext(os.path.basename(input_image_path))[0]
            output_path = os.path.join(output_dir, f"{base_name}_part_{i+1}.png")
            
            cropped_img.save(output_path)
            print(f"이미지 저장 완료: {output_path}")

        print("모든 이미지 분할 및 저장 완료!")

    except FileNotFoundError:
        print(f"오류: '{input_image_path}' 파일을 찾을 수 없습니다. 경로를 확인해 주세요.")
    except Exception as e:
        print(f"이미지 처리 중 오류 발생: {e}")

# --- 사용 예시 ---
input_file = input('이미지 경로 입력 : ')           # 자르고 싶은 이미지 파일 경로
output_folder = input('이미지 저장 경로 입력 : ')   # 잘라낸 이미지를 저장할 폴더
target_width = int(input('이미지 가로 크기 입력 : '))    # 잘라낼 이미지의 가로 크기
target_height = int(input('이미지 세로 크기 입력 : '))      # 잘라낼 이미지의 세로 크기

split_long_image_python(input_file, output_folder, target_width, target_height)

# 위에 주석 처리된 부분을 참고해서 input_file, output_folder, target_width, target_height를 설정하고 실행해 보세요.