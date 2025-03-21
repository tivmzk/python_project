# 파일은 한번에 번역한다.
# 환경변수에서 파이썬 3.13로 수정

# key1 : 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
# key2 : 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

# model1 : google/gemini-2.0-flash-thinking-exp:free
# model2 : google/gemini-2.0-pro-exp-02-05:free

import os
from openai import OpenAI

# OpenAI API 키 설정
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="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",
)

def translate_text(text):
    # 프롬프트1 : Translate the text into Korean, and only write the translated content without any additional information. When translating, modify only the person's name and dialogue, and preserve the original text format.
    completion = client.chat.completions.create(
    extra_body={},
    model="google/gemini-2.0-flash-thinking-exp:free",
    messages=[
        {
        "role": "user",
        "content": [
            {
            "type": "text",
            "text": f"Translate the text into Korean, and only write the translated content without any additional information. When translating, modify only the person's name and dialogue, and preserve the original text format.\n: {text}"
            }
        ]
        }
    ]
    )
    try:
        # 응답에서 번역된 텍스트만 추출
        translated_text = completion.choices[0].message.content
        return translated_text.strip()  # 공백 제거
    except Exception as e:
        print(f"Error translating text: {e}")
        print(f"{completion}")
        return text

def translate_files_in_folder(folder_path):
    trans_folder = os.path.join(folder_path, 'trans')
    os.makedirs(trans_folder, exist_ok=True)  # trans 폴더 생성

    for filename in os.listdir(folder_path):
        if filename.endswith('.txt'):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                translated_content = translate_text(content)
                
            # 번역된 내용을 trans 폴더에 원래 파일명 그대로 저장
            translated_file_path = os.path.join(trans_folder, filename)
            with open(translated_file_path, 'w', encoding='utf-8') as translated_file:
                translated_file.write(translated_content)
            print(f"{filename} 번역 완료: {translated_file_path}")

# 폴더 경로 입력 받기
folder_to_translate = input("번역할 폴더의 경로를 입력하세요: ")
# 경로 표준화
folder_to_translate = os.path.normpath(folder_to_translate)
translate_files_in_folder(folder_to_translate)
