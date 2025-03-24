# 전남에서 사용한 새 게시글이 있는지 확인하는 코드
# 웹접근성 때문에 사용함

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import pyperclip

def get_dates_from_url(url, input_date):
    try:
        print('조회 : ' + url)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # 요청이 성공했는지 확인
        soup = BeautifulSoup(response.text, 'html.parser')

        # 테이블 또는 특정 요소 찾기
        elems = None
        
        # 첫 번째 방법: 테이블에서 '등록일' 열 찾기
        table = soup.select_one('#myTable')
        if table:
            th = table.select('thead > tr > th')
            idx = next((i for i, header in enumerate(th) if '등록일' in header.text), None)
            if idx is not None:
                elems = table.select(f'tr > td:nth-child({idx + 1})')

        # 두 번째 방법: photo_list에서 날짜 찾기
        if elems is None:
            elems = soup.select('.photo_list > ul > li > a > p > span:nth-child(2)')

        # 세 번째 방법: photo_list2에서 날짜 찾기
        if elems is None:
            elems = soup.select('.photo_list2 > ul > li > a > dl > dd.date')

        for elem in elems:
            date_pattern = r'\d{4}\.\d{2}\.\d{2}'
            match = re.search(date_pattern, elem.text)
            if match:
                curr_date = datetime.strptime(match.group(), '%Y.%m.%d')
                if curr_date >= input_date:
                    return url  # 유효한 URL 반환
    except Exception as e:
        print(f"오류 발생: {e}")
        
    return None

def main():
    input_date_str = input("날짜를 입력하세요 (형식: YYYY-MM-DD): ")
    input_date = datetime.strptime(input_date_str, '%Y-%m-%d')

    urls = []
    print("URL을 입력하세요. 빈칸을 입력하면 종료됩니다.")
    while True:
        url = input("URL: ")
        if url.strip() == "":
            break
        urls.append(url.strip())

    matching_urls = []
    
    for url in urls:
        result_url = get_dates_from_url(url, input_date)
        if result_url:
            matching_urls.append(result_url)

    if matching_urls:
        print("입력한 날짜보다 큰 날짜가 있는 URL:")
        for url in matching_urls:
            print(url)
        
        # 결과를 클립보드에 복사
        pyperclip.copy("\n".join(matching_urls))
        print("\nURL 리스트가 클립보드에 복사되었습니다. 이제 Ctrl+V로 붙여넣기 할 수 있습니다.")
    else:
        print("해당 날짜보다 큰 날짜가 있는 URL이 없습니다.")

if __name__ == "__main__":
    main()
