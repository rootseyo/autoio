# AutoIO

AutoIO는 키보드와 마우스 입력을 기록하고 같은 타이밍으로 재생하는 macOS/Windows용 데스크톱 앱입니다. 하나의 공통 코드와 이식 가능한 JSON 매크로 형식을 사용합니다.

> 매크로 자동화는 사용 중인 앱이나 서비스의 정책을 위반할 수 있습니다. 본인이 제어할 권한이 있는 환경에서만 사용하세요.

## 주요 기능

- 키 누름/해제, 마우스 이동·클릭·스크롤 기록
- `F8` 녹화/중지, `F9` 재생/중지(앱에서 변경 가능)
- 고정 좌표 또는 현재 커서를 따라가는 Free click 모드
- 오토 클릭 반복 횟수와 밀리초(ms) 단위 클릭 간격 설정, `F10` 시작/중지
- 반복 재생, 반복 사이 딜레이 설정 및 `0`/`-1` 무한 반복
- 매크로 저장, 불러오기, 가져오기, 삭제
- macOS와 Windows 사이에서 공유할 수 있는 검증된 JSON 형식
- 중지 또는 오류 시 눌린 키와 마우스 버튼 자동 해제
- 녹화와 재생 중 모든 키보드·마우스 I/O를 Activity에 기록
- 시스템 테마를 따르는 공통 GUI

## 가장 쉬운 설치 방법

GitHub의 **Releases**에서 운영체제에 맞는 파일을 내려받습니다.

- Windows: `AutoIO-Windows.exe`
- macOS: `AutoIO-macOS.zip` 압축 해제 후 `AutoIO.app`

현재 배포 파일은 코드 서명이 되어 있지 않습니다. Windows SmartScreen 또는 macOS Gatekeeper 경고가 나타날 수 있으므로, 이 저장소의 Releases에서 받은 파일인지 확인한 뒤 실행하세요.

### macOS 권한

처음 실행할 때 다음 두 항목에서 AutoIO를 허용하고 앱을 다시 시작해야 합니다.

1. 시스템 설정 → 개인정보 보호 및 보안 → 손쉬운 사용
2. 시스템 설정 → 개인정보 보호 및 보안 → 입력 모니터링

소스에서 실행했다면 AutoIO 대신 사용 중인 Terminal과 Python에 권한을 부여해야 할 수 있습니다.

### Windows 권한

일반 앱에서는 추가 설정이 필요하지 않습니다. 관리자 권한으로 실행 중인 프로그램을 자동화하려면 AutoIO도 같은 권한 수준으로 실행해야 할 수 있습니다.

## 사용법

1. **Record** 또는 `F8`을 눌러 녹화를 시작합니다.
2. 필요한 입력을 수행한 뒤 `F8`을 다시 눌러 중지합니다.
3. **Repeat**에 반복 횟수를 입력하고, **Repeat delay (ms)**에 각 반복 사이의 대기 시간을 입력합니다. 무한 반복은 `0` 또는 `-1`입니다.
4. **Play** 또는 `F9`으로 재생하고, 같은 버튼/키로 중지합니다.
5. **Save macro**로 저장하면 오른쪽 목록에서 다시 불러오거나 바로 실행할 수 있습니다.

### 오토 클릭

1. **Fixed position** 또는 **Free click** 모드를 선택합니다.
2. **Fixed position**은 X/Y 좌표를 직접 입력하거나 **Capture in 3s**를 누른 뒤 원하는 위치로 커서를 옮깁니다.
3. **Free click**은 좌표를 저장하거나 고정하지 않고, 실행 중 현재 커서가 있는 위치를 계속 클릭합니다. 시작 전 3초 동안 커서를 AutoIO 창 밖으로 옮기세요.
4. **Clicks**에 반복 횟수를 입력합니다. 무한 반복은 `0` 또는 `-1`입니다.
5. **Interval (ms)**에 클릭 사이 간격을 `1~60000`ms로 입력합니다. 값이 작을수록 빠릅니다.
6. **Start auto click** 또는 `F10`으로 시작하고, 다시 누르면 즉시 중지합니다.

안전을 위해 Fixed position에서는 AutoIO 창 내부 좌표를 사용할 수 없습니다. Free click 실행 중에는 커서를 AutoIO 창 위로 옮기지 마세요. 녹화·매크로 재생·오토 클릭은 동시에 실행되지 않습니다.

해상도, 디스플레이 배율, 창 위치가 바뀌면 기록된 마우스 좌표가 달라질 수 있습니다. 재생 전 화면 구성을 녹화 당시와 동일하게 맞추세요.

## 소스에서 실행

Python 3.10 이상이 필요합니다.

### macOS

```bash
git clone https://github.com/rootseyo/auto_io.git
cd auto_io
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m auto_io
```

### Windows PowerShell

```powershell
git clone https://github.com/rootseyo/auto_io.git
cd auto_io
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m auto_io
```

기존 명령인 `python auto_kb_mouse.py`와 `python auto_kb_mouse_apple.py`도 호환을 위해 유지됩니다.

## 매크로 저장 위치

매크로는 저장소나 앱 설치 폴더가 아닌 사용자 데이터 폴더에 보관됩니다.

- macOS: `~/Library/Application Support/AutoIO/macros`
- Windows: `%APPDATA%\rootseyo\AutoIO\macros`

기존 버전의 JSON 배열 형식은 **Import JSON**으로 가져올 수 있으며, 저장할 때 현재 스키마로 변환됩니다. JSON 파일은 키 입력과 좌표를 평문으로 담으므로 공유 전에 내용을 확인하세요.

## 직접 빌드

```bash
# macOS
./scripts/build_macos.sh

# Windows Command Prompt
build_windows.bat
```

GitHub Actions는 macOS/Windows에서 테스트하고, 수동 실행 또는 Release 발행 시 각 운영체제용 빌드를 생성합니다. Release에서 실행되면 빌드 파일도 해당 Release에 첨부합니다.

## 개발

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
ruff check .
```

구조와 기여 절차는 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.

## 라이선스

[MIT](LICENSE)
