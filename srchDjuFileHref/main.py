# 대전대 홈페이지에서 규정 첨부파일을 찾는 코드

import requests
from bs4 import BeautifulSoup
import pyperclip

def get_file_hrefs_from_url(url, fileNumList):
    try:
        print('조회 : ' + url)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # 요청이 성공했는지 확인
        soup = BeautifulSoup(response.text, 'html.parser')

        result = []
        for fileNum in fileNumList:
            find_td = soup.select('.tbl_st td')
            if find_td:
                for td in find_td:
                    if fileNum in td.get_text(strip=True):
                        href = td.find_next_sibling('td').find('a').attrs['href']
                        result.append(getQuery(href))
                        break
        return result
    except Exception as e:
        print(f"오류 발생: {e}")
        
    return None

def getQuery(fileUrl):
    return 'UPDATE TSA_ATCH_FILE_DETAIL SET FILE_DTLS = \'\' WHERE FILE_STRE_COURS = \'{0}\';'.format(fileUrl)

def main():
    fileNums = []
    print("추출할 규정 파일의 번호를 입력, 빈칸 입력 시 다음으로 넘어감 예) 1-0-1 : ")
    while True:
        fileNum = input("파일 번호 : ")
        if fileNum.strip() == "":
            break
        fileNums.append(fileNum.strip())

    fileNumMap = {}
    for fileNum in fileNums:
        key = fileNum.split('-')[0]
        if key in fileNumMap:
            fileNumMap[key].append(fileNum)
        else:
            fileNumMap[key] = [fileNum]

    urlMap = {
        '1':'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2641&mi=4321'
        ,'2':'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2642&mi=4322'
        ,'3':'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2643&mi=4323'
        ,'4':'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2644&mi=4324'
        ,'5':'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2645&mi=4325'
        ,'6':'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2645&mi=4325'
        ,'7':'https://www.dju.ac.kr/dju/cm/cntnts/cntntsView.do?cntntsId=2645&mi=4325'
    }

    result = []
    
    for key in fileNumMap.keys():
        result_hrefs = get_file_hrefs_from_url(urlMap[key], fileNumMap[key])
        if result_hrefs:
            result.extend(result_hrefs)

    if result:
        # 결과를 클립보드에 복사
        pyperclip.copy("\n".join(result))
        print("결과를 클립보드에 복사되었습니다. 이제 Ctrl+V로 붙여넣기 할 수 있습니다.")
    else:
        print("하나도 못찾았습니다. 뭔가 잘못된 듯")

if __name__ == "__main__":
    main()
