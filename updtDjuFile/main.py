# 대전대 홈페이지에서 규정 첨부파일 교체 시 검색엔진 관련한 데이터를 수정하는 쿼리를 출력하는 프로그램
# 규정 번호를 입력해서 현재 홈페이지의 첨부파일이 검색되지 않게 하는 쿼리를 출력하고
# 새로 등록한 첨부파일을 입력해서 새로 등록한 첨부파일이 검색되게 하는 쿼리를 출력한다
# 3-1-2는 두개 있어서 따로 수정하기

import requests
from bs4 import BeautifulSoup
import pyperclip

def get_query(dtl, file_url):
    return 'UPDATE TSA_ATCH_FILE_DETAIL SET FILE_DTLS = \'{0}\' WHERE FILE_STRE_COURS = \'{1}\';'.format(dtl, file_url)

def get_file_query_from_url(url, file_num_list):
    try:
        print('조회 : ' + url)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # 요청이 성공했는지 확인
        soup = BeautifulSoup(response.text, 'html.parser')

        result = []
        find_td = soup.select('.tbl_st td')
        for file_num in file_num_list:
            temp = ''
            if file_num.startswith('3-1-2_'):
                temp = file_num.split('_')[1]
                file_num = '3-1-2'

            for td in find_td:
                if file_num == td.get_text(strip=True):
                    sibling_text = td.find_next_sibling('td').find('a').get_text(strip=True)
                    if temp == '1':
                        if '기구표' not in sibling_text:
                            continue
                    elif temp == '2':
                        if '직제규정' not in sibling_text:
                            continue
                    print(file_num+' 발견')
                    href = td.find_next_sibling('td').find('a').attrs['href']
                    result.append(get_query('', href))
                    break
        return result
    except Exception as e:
        print(f"오류 발생: {e}")
        
    return None

def main():
    file_nums = []
    print("추출할 규정 파일의 번호를 입력, 빈칸 입력 시 다음으로 넘어감 예) 1-0-1 : ")
    while True:
        file_num = input("파일 번호 : ")
        if file_num.strip() == "":
            break
        if file_num == '3-1-2':
            temp = input('추가 번호 입력 (1 기구표, 2 직제규정) : ')
            file_num = file_num.strip() + '_' + temp.strip()
        file_nums.append(file_num.strip())
    print("새로 교체하는 파일의 경로를 입력, 빈칸 입력 시 다음으로 넘어감 예) /upload/cntntsFile/dju/doc_e67ca63f-b31e-4f35-b4bc-dba0a86a69b41712562087537.pdf : ")
    new_file_query = []
    while True:
        filePath = input("새 파일 경로 : ")
        if filePath.strip() == "":
            break
        new_file_query.append(get_query('대학규정', filePath.strip()))

    file_num_map = {}
    for file_num in file_nums:
        key = file_num.split('-')[0]
        if key in file_num_map:
            file_num_map[key].append(file_num)
        else:
            file_num_map[key] = [file_num]

    url_map = {
        '1':'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2641&mi=4321'
        ,'2':'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2642&mi=4322'
        ,'3':'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2643&mi=4323'
        ,'4':'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2644&mi=4324'
        ,'5':'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2645&mi=4325'
        ,'6':'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2646&mi=4326'
        ,'7':'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2647&mi=4327'
    }

    result = []
    
    for key in file_num_map.keys():
        result_querys = get_file_query_from_url(url_map[key], file_num_map[key])
        if result_querys:
            result.extend(result_querys)

    if result:
        # 결과를 클립보드에 복사
        result_str = "\n".join(result)
        result_str += '\n\n'
        result_str += "\n".join(new_file_query)
        pyperclip.copy(result_str)
        print("결과를 클립보드에 복사되었습니다. 이제 Ctrl+V로 붙여넣기 할 수 있습니다.")
    else:
        print("하나도 못찾았습니다. 뭔가 잘못된 듯")

if __name__ == "__main__":
    main()
    input('Enter key to exit...')