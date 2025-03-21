# 파일은 한번에 번역한다. ollama 사용
# 환경변수에서 파이썬 3.13로 수정

import os
from ollama import chat
from ollama import ChatResponse

model = "gemma3:4b"


def translate_text(lines, filename):
    # 프롬프트1 : Translate the text into Korean, and only write the translated content without any additional information. When translating, modify only the person's name and dialogue, and preserve the original text format.
    result_lines = []
    response = None  # 초기화

    try:
        messages = [
            {
                "role": "user",
                "content": "앞으로 내가 입력하는 말을 한국어로 번역해줘, 대답할때는 번역한 내용만 말하고 원문의 포맷 그대로 대답해야되",
            },
        ]
        
        response: ChatResponse = chat(
            model=model,
            messages=messages
        )
        print(response.message.content)
        messages.append({
            "role": "assistant",
            "content": response.message.content,
        })

        idx = 1
        for line in lines:
            print(f"{filename} : {idx}/{len(lines)}")
            if line.startswith('--') or line.startswith('@') or line.startswith('\\'):
                result_lines.append(line)
            else:
                newMsg = list(messages)
                newMsg.append({
                    "role": "user",
                    "content": line.strip(),
                })
                response = chat(
                    model=model,
                    messages=newMsg
                )
                result_lines.append(response.message.content if response.message.content.endswith('\n') else response.message.content + '\n')
            idx += 1
        
        # 응답에서 번역된 텍스트만 추출
        translated_text = "".join(result_lines)
        return translated_text.strip()  # 공백 제거
    except Exception as e:
        print(f"Error translating text: {e}")
        if response:  # 응답이 있는 경우만 출력
            print(f"{response}")
        return "".join(result_lines)


def translate_files_in_folder(folder_path):
    trans_folder = os.path.join(folder_path, "trans")
    os.makedirs(trans_folder, exist_ok=True)  # trans 폴더 생성

    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, "r", encoding="utf-8") as file:
                print(f"{filename} 파일 읽기 중...")
                content = file.readlines()
                translated_content = translate_text(content, filename)

            # 번역된 내용을 trans 폴더에 원래 파일명 그대로 저장
            translated_file_path = os.path.join(trans_folder, filename)
            with open(translated_file_path, "w", encoding="utf-8") as translated_file:
                translated_file.write(translated_content)
            print(f"{filename} 번역 완료: {translated_file_path}")


# 폴더 경로 입력 받기
folder_to_translate = input("번역할 폴더의 경로를 입력하세요: ")
# 경로 표준화
folder_to_translate = os.path.normpath(folder_to_translate)
translate_files_in_folder(folder_to_translate)