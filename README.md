# Python Mouse Macro

F8 키를 눌러 기록을 시작/중지하고, F9 키를 눌러 기록된 움직임을 재생하는 마우스 매크로입니다.

## 요구 사항
- Python 3.x
- `pynput` 라이브러리

## 설치 방법
```bash
pip install pynput
```

## 사용 방법
1. 스크립트 실행:
   ```bash
   python mouse_macro.py
   ```
2. **F8**: 기록 시작 (한 번 더 누르면 중지)
3. **F9**: 기록된 내용 재생

## 기능
- 마우스 이동 기록
- 마우스 클릭 기록
- 시간 간격 유지 (정확한 재생)
