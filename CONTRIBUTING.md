# Contributing

버그 리포트와 Pull Request를 환영합니다.

## 개발 환경

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
ruff check .
```

`main`에서 브랜치를 만들고, 한 PR에는 하나의 논리적인 변경을 담아 주세요. 사용자 동작이 바뀌면 README도 함께 수정하고 macOS 또는 Windows 중 테스트한 환경을 PR에 적어 주세요.

## 프로젝트 구조

- `auto_io/app.py`: GUI, 녹화와 사용자 상호작용
- `auto_io/playback.py`: 중단 가능한 재생 엔진과 입력 정리
- `auto_io/events.py`: 버전형 JSON 스키마, 검증, 기존 형식 호환
- `auto_io/storage.py`: OS별 사용자 데이터 저장소
- `auto_io/platform_support.py`: macOS에 한정된 권한/호환 코드
- `tests/`: GUI 없이 실행되는 스키마와 저장소 테스트

## 보안과 개인정보

매크로에는 사용자가 입력한 키와 화면 좌표가 포함됩니다. 실제 비밀번호, 인증 토큰, 개인정보가 들어간 매크로는 이슈나 PR에 첨부하지 마세요.
