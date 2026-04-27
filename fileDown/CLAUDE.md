# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 개요

`data.xlsx`에 담긴 URL 목록을 읽어 파일을 일괄 다운로드하는 Python 스크립트입니다.

## 실행

```bash
python download.py
```

다운로드 결과는 `downloads/` 폴더에 저장됩니다.

## data.xlsx 구조

| 열 | 내용 |
|----|------|
| 1열 | 제목 (폴더명으로 사용) |
| 2열 | 날짜/시간 |
| 3열 | 다운로드 URL |

같은 제목이 여러 행에 걸쳐 있으면 같은 폴더에 모두 저장됩니다.

## downloads/ 폴더 구조

```
downloads/
├── 001_제목A/
│   ├── 파일1.pdf
│   └── 파일2.pdf
├── 002_제목B/
│   └── 파일3.hwp
└── ...
```

폴더명은 `001_` 부터 시작하는 3자리 번호 + 1열 제목이며, Excel 행 순서(첫 등장 기준)를 따릅니다.

## download.py 주요 동작

- **파일명 추출**: 서버 응답의 `Content-Disposition` 헤더에서 파일명을 파싱합니다. 우선순위: RFC 5987(`filename*=UTF-8''...`) → URL 인코딩(`%ED%...`) → latin-1 바이트를 UTF-8로 재해석 (한국 서버 관행)
- **파일명/폴더명 정제**: `sanitize_name()`으로 Windows 금지 문자(`\ / : * ? " < > |`)를 `_`로 치환
- **충돌 방지**: 같은 폴더에 동일 파일명이 있으면 `파일명_숫자.확장자`로 저장
