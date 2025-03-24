# 로컬 프로젝트에 있는 파일을 운영서버에 반영하기 쉽게 추출하는 프로그램
# func.html의 svn 파일 경로 수정와 같이 사용
import os
import shutil

def create_folder(project_folder, result_folder, input_data):
    project_folder = project_folder[:-len(os.path.sep + 'webapp')]
    # 결과 폴더 없으면 생성
    if not os.path.exists(result_folder):
        os.makedirs(result_folder)
        print("결과 폴더 생성 완료")

    for input in input_data:
        # 제거된 파일 무시
        if input[0] == "-":
            continue
        # 입력한 데이터에서 파일 경로
        input_path = os.path.dirname(input)
        # 입력한 데이터에서 파일명(확장자 포함)
        key = os.path.basename(input)
        # 복사할 파일 경로
        src_path = os.path.join(project_folder + input_path, key)
        # 파일이 없을 경우 처리
        if not os.path.exists(src_path):
            print(f"파일이 없습니다. : {src_path}")
            continue
        # 붙여넣기 할 파일 경로
        dst_path = os.path.join(result_folder + input_path, key)
        # 붙여넣기할 폴더가 없으면 생성
        if not os.path.exists(os.path.dirname(dst_path)):
            os.makedirs(os.path.dirname(dst_path))
        # 파일 복사
        shutil.copy(src_path, dst_path)
        print(f"복사 완료 : {dst_path}")

project_folder = input("프로젝트 폴더 경로(webapp 폴더까지)를 입력하세요: ")
project_folder = os.path.normpath(project_folder)
if not os.path.normpath(project_folder).endswith('webapp'):
    exit("경로를 프로젝트의 webapp 폴더로 입력하세요.")
result_folder = input("결과를 저장할 폴더 경로를 입력하세요: ")  # 예: /path/to/result/folder
result_folder = os.path.normpath(result_folder)
input_data = []
while True:
    line = input("데이터를 입력하세요 (종료하려면 빈 줄을 입력하세요): ") # func.html의 svn 파일 경로 수정 사용
    if line == "":
        break
    input_data.append(line)

create_folder(project_folder, result_folder, input_data)
print("프로그램이 완료되었습니다.")
input("종료하려면 Enter 키를 누르세요...")