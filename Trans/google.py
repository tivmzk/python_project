import asyncio
import re
import os
from googletrans import Translator

# 번역하지 않을 조건 리스트
# 시작하는 문자
skip_conditions1 = ['@@', '\\']
# 중간에 있는 문자
skip_conditions2 = ['ッッ', 'パンパンパン', 'パシャパシャパシ', 'ツンツンツン', 'んんん']
# 예외 처리 단서 사전
translations_cache = {}
# "를 「」로 수정
quote = ''
output_folder = ''

# 특정 조건을 확인하는 함수
def should_skip(line):
    return any(line.startswith(condition) for condition in skip_conditions1) or any(condition in line for condition in skip_conditions2)

def replace_quotes(text):
    result = text.replace('"', '「', 1).replace('"', '」', 1)
    if result.strip().endswith('「'):
        result = result[:-1] + '」'
        if text.endswith('\n'):
            result += '\n'
    return result

# 비동기 번역 함수
async def translate_blocks(data, filename):
    translator = Translator()
    
    # 데이터를 줄 단위로 나누기
    lines = data.strip().split('\n')

    # 결과를 저장할 리스트
    result = []
    current_block = []
    block_number = None

    # 각 줄을 처리
    for line in lines:
        if line.startswith('---'):
            if current_block:
                result.append((block_number, '\n'.join(current_block)))
                current_block = []
            block_number = line
        else:
            current_block.append(line)

    if current_block:
        result.append((block_number, '\n'.join(current_block)))

    texts_to_translate = []

    for block_number, original_text in result:
        lines = original_text.split('\n')
        for line in lines:
            if not should_skip(line) and line not in translations_cache:
                texts_to_translate.append(line)

    # 리스트를 사용하여 번역 요청 (수정된 부분)
    if texts_to_translate:
        print(f'{filename} : 번역 요청 중...')
        translations = await translator.translate(texts_to_translate, dest='ko')
        for original, translated in zip(texts_to_translate, translations):
            translations_cache[original] = replace_quotes(translated.text) if quote == 'y' else translated.text

    # 최종 결과 조합
    final_output = []

    for block_number, original_text in result:
        if block_number is not None:
            final_output.append(block_number)
        lines = original_text.split('\n')
        for line in lines:
            if should_skip(line):
                final_output.append(line)
            else:
                # 캐시에서 번역된 라인 추가
                translated_line = translations_cache.get(line)  # get() 메서드를 사용하여 None 체크
                
                if translated_line is not None:  # 번역된 라인이 None이 아닐 경우에만 추가
                    matches1 = re.findall(r'\\[A-Za-z]+\[\d+\]', line)
                    matches2 = re.findall(r'\\ [A-Za-z]+ \[\d+\] ', translated_line)

                    for match1, match2 in zip(matches1, matches2):
                        translated_line = translated_line.replace(match2, match1)

                    final_output.append(translated_line)
                else:
                    print(f"Warning: No translation found for line: {line}")  # 경고 메시지 출력
                    final_output.append(line)  # 원래 라인을 추가 (번역되지 않은 경우)

    # 번역 결과를 파일에 저장
    output_file_path = os.path.join(output_folder, f'{filename}')
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write('\n'.join(final_output))
        print(f'{filename} 완료')

# 번역 모드 선택
quote = input("\"수정 여부 선택 (y/n): ").lower()

# 폴더 경로 입력 받기
input_folder = input("번역할 폴더의 경로를 입력하세요: ")
# 경로 표준화
input_folder = os.path.normpath(input_folder)

# 결과 저장 폴더 생성
output_folder = os.path.join(input_folder, 'trans')
os.makedirs(output_folder, exist_ok=True)

# 폴더 내 모든 파일에 대해 반복
for filename in os.listdir(input_folder):
    if filename.endswith('.txt'):  # .txt 파일만 처리
        input_file_path = os.path.join(input_folder, filename)
        
        # 파일 읽기
        with open(input_file_path, 'r', encoding='utf-8') as file:
            lines = file.read()
            # 비동기 실행
            asyncio.run(translate_blocks(lines, filename))
