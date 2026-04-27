# 파일을 여러개 한꺼번에 다운로드 하는 코드

import openpyxl
import requests
import os
import re
import sys
from urllib.parse import unquote

sys.stdout.reconfigure(encoding='utf-8')

EXCEL_PATH = "data.xlsx"
OUTPUT_DIR = "downloads"

def sanitize_name(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip()

def get_filename_from_response(response, fallback):
    cd = response.headers.get("Content-Disposition", "")

    # 1순위: filename*=UTF-8''%EC%9D%B4%EB%A6%84.pdf (RFC 5987)
    m = re.search(r"filename\*=UTF-8''([^\s;]+)", cd, re.IGNORECASE)
    if m:
        try:
            decoded_name = unquote(m.group(1), encoding='utf-8')
            return sanitize_name(decoded_name)
        except Exception:
            pass

    # 2순위: filename="..." 또는 filename=...
    m = re.search(r'filename=["\']?([^"\';\r\n]+)["\']?', cd, re.IGNORECASE)
    if m:
        name = m.group(1).strip().strip('"\'')
        

        # URL 인코딩된 경우 먼저 디코딩 시도
        if '%' in name:
            try:
                decoded_name = unquote(name, encoding='utf-8')
                return sanitize_name(decoded_name)
            except Exception:
                pass

        # CP949(한국 서버 관행) 변환 시도
        try:
            decoded_name = name.encode('latin-1').decode('cp949')
            return sanitize_name(decoded_name)
        except Exception:
            pass

        # UTF-8 변환 시도
        try:
            decoded_name = name.encode('latin-1').decode('utf-8')
            return sanitize_name(decoded_name)
        except Exception:
            pass

        # 변환 실패 시 원본 그대로
        return sanitize_name(name)

    # 실패하면 fallback 사용
    return fallback

def main():
    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb.active

    # 제목 순서 유지하며 URL 그룹화
    order = []
    groups = {}
    for row in ws.iter_rows(min_row=1, values_only=True):
        title, _, url = row[0], row[1], row[2]
        if not title or not url:
            continue
        if title not in groups:
            order.append(title)
            groups[title] = []
        groups[title].append(url)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for idx, title in enumerate(order, start=1):
        folder_name = f"{idx:03d}_{sanitize_name(title)}"
        folder_path = os.path.join(OUTPUT_DIR, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        urls = groups[title]
        print(f"\n[{idx:03d}] {title} ({len(urls)}개 파일)")

        for file_idx, url in enumerate(urls, start=1):
            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                filename = get_filename_from_response(resp, f"file_{file_idx}")
                save_path = os.path.join(folder_path, filename)
                # 동일 파일명 충돌 방지
                if os.path.exists(save_path):
                    base, ext = os.path.splitext(filename)
                    save_path = os.path.join(folder_path, f"{base}_{file_idx}{ext}")
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                print(f"  ✓ {filename}")
            except Exception as e:
                print(f"  ✗ 실패 ({url}): {e}")

    print("\n완료!")

if __name__ == "__main__":
    main()
