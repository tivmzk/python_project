function translateAndLog(st, max) {
    const lines = st.split('\n'); // 문자열을 줄 단위로 분리
    const results = []; // 결과를 저장할 배열
   if(!max) max = 100;

    // 100줄 단위로 문자열을 잘라서 처리
    const processChunk = (start) => {
        const chunk = lines.slice(start, start + max).join('\n'); // 100줄 단위로 잘라서 결합
        const encodedChunk = encodeURIComponent(chunk); // 인코딩
        
        const win = open(`https://papago.naver.com?sk=auto&tk=ko&st=${encodedChunk}`, 'papago');

        // 새 창이 로드된 후 innerText를 가져오기 위해 setTimeout 사용
        setTimeout(() => {
            try {
                // innerText를 가져와서 결과 배열에 추가
                results.push(win.document.querySelector('#txtTarget').innerText);
            } catch (error) {
                console.error('Error accessing the window:', error);
            }

            // 다음 청크를 처리
            if (start + max < lines.length) {
                processChunk(start + max); // 다음 100줄을 처리
            } else if (start < lines.length) {
                // 남은 줄이 100 이하일 경우 처리
                processChunk(lines.length); // 마지막 남은 줄 처리
            } else {
                console.log(results.join('\n')); // 모든 결과 출력
            }
        }, 1500); // 1초 후에 실행
    };

    // 첫 번째 청크 처리 시작
    processChunk(0);
}