# srt 자막 추출 및 병합기
import re
import os

def extract_dialogues(srt_file):
    dialogues = []
    timings = []

    with open(srt_file, 'r', encoding='utf-8') as file:
        content = file.read()
        
    # SRT 파일의 대사와 타이밍을 정규 표현식으로 추출
    entries = re.split(r'\n\n+', content.strip())
    
    for entry in entries:
        lines = entry.splitlines()
        if len(lines) > 2:  # 번호와 시간 정보가 있어야 함
            # 타이밍과 대사 부분 추출
            timings.append(lines[1].strip())  # 시간 정보
            dialogue = '\n'.join(lines[2:]).strip()  # 대사 부분
            dialogues.append(dialogue)

    return timings, dialogues

def write_dialogues_to_srt(timings, new_dialogues, output_file):
    with open(output_file, 'w', encoding='utf-8') as file:
        for index, (timing, dialogue) in enumerate(zip(timings, new_dialogues)):
            file.write(f"{index + 1}\n")
            file.write(f"{timing}\n")  # 시간 정보 유지
            file.write(f"{dialogue}\n\n")

def read_dialogues_from_txt(txt_file):
    with open(txt_file, 'r', encoding='utf-8') as file:
        return [line.strip() for line in file if line.strip()]

def save_dialogues_to_txt(dialogues, output_txt_file):
    with open(output_txt_file, 'w', encoding='utf-8') as file:
        for dialogue in dialogues:
            file.write(f"{dialogue}\n")  # 대사만 저장

def main():
    choice = input("내용 추출을 하시겠습니까? (1: 추출, 2: 병합): ")

    if choice == '1':
        srt_file = input("SRT 파일 경로를 입력하세요: ").strip()
        srt_file = os.path.normpath(srt_file)  # 경로 정규화
        output_txt_file = os.path.splitext(srt_file)[0] + "_extract.txt"  # 결과 파일명 설정
        
        timings, dialogues = extract_dialogues(srt_file)
        save_dialogues_to_txt(dialogues, output_txt_file)  # 대사만 저장

        print(f"대사가 '{output_txt_file}'에 저장되었습니다.")

    elif choice == '2':
        srt_file = input("원본 SRT 파일 경로를 입력하세요: ").strip()
        srt_file = os.path.normpath(srt_file)  # 경로 정규화
        txt_file = input("새로운 대사가 있는 텍스트 파일 경로를 입력하세요: ").strip()
        txt_file = os.path.normpath(txt_file)  # 경로 정규화
        output_file = os.path.splitext(srt_file)[0] + "_merge.srt"  # 결과 파일명 설정

        timings, original_dialogues = extract_dialogues(srt_file)
        new_dialogues = read_dialogues_from_txt(txt_file)
        
        write_dialogues_to_srt(timings, new_dialogues, output_file)
        print(f"새로운 SRT 파일 '{output_file}' 작성 완료!")

    else:
        print("잘못된 선택입니다.")

if __name__ == "__main__":
    main()
