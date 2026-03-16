# Version

This is not ready for use
초안일 뿐 사용이 아직은 불가합니다.
추후 사용자가 직접 값을 넣는게 아니라 브라우저에서 화면을 보고 클릭하여 액션을 취하게 하며, 단계별로 실행을 테스트 해볼 수 있는 프로세스를 추가할 예정입니다.




# click_next_click

`click_next_click` is a small Python tool for building repeatable browser routines without writing a new script every time.

`click_next_click`은 브라우저 반복 작업을 매번 새 코드로 작성하지 않고, 순서화된 액션으로 구성해서 재사용할 수 있게 만드는 작은 Python 도구입니다.

The project assumes:

- `node.js` is already installed
- `playwright` and `chromium` are already installed
- the user edits a routine as ordered JSON steps

프로젝트 기본 전제는 아래와 같습니다.

- `node.js`가 이미 설치되어 있음
- `playwright`와 `chromium`이 이미 설치되어 있음
- 사용자는 루틴을 순서가 있는 JSON step들로 편집함

The core idea is simple:

- `main.py` is the only executable code file
- the UI lets the user add steps one by one
- each step has an `action` dropdown and a few input values
- routines can be saved to `/data` as JSON and loaded again later
- the runner reads the JSON order and executes Playwright actions in sequence

핵심 구조는 단순합니다.

- 실행 코드는 `main.py` 한 파일에 모아둠
- UI에서 step을 한 코스씩 추가함
- 각 step은 `action` 드롭다운과 몇 개의 입력값으로 구성됨
- 루틴은 `/data` 아래 JSON으로 저장하고 다시 불러올 수 있음
- 실행기는 JSON 순서를 그대로 읽어서 Playwright 액션을 순차 실행함

## Current Action Set

The first version keeps the action model intentionally small:

- `open`
- `goto`
- `check`
- `wait`
- `click`
- `fill`
- `close`

첫 버전은 액션 종류를 일부러 작게 유지합니다.

- `open`
- `goto`
- `check`
- `wait`
- `click`
- `fill`
- `close`

This covers the repeated work you described:

- open browser and initial page
- move to another page
- find or verify an element
- click an element
- fill an input
- close the browser cleanly

이 정도만 있어도 지금 설명한 반복 작업을 대부분 다룰 수 있습니다.

- 브라우저 열기와 첫 페이지 진입
- 다른 페이지로 이동
- 요소 탐색 또는 존재 여부 확인
- 요소 클릭
- 입력창 값 입력
- 브라우저 종료 및 정리

## Selector Types

Each step can use one of these selector modes:

- `none`
- `css`
- `id`
- `class`
- `text`
- `placeholder`
- `label`
- `role`

각 step은 아래 selector 방식을 사용할 수 있습니다.

- `none`
- `css`
- `id`
- `class`
- `text`
- `placeholder`
- `label`
- `role`

Examples:

- `id` + `username`
- `class` + `login-button`
- `placeholder` + `Email`
- `text` + `Login`
- `role` + `button`

예시는 아래와 같습니다.

- `id` + `username`
- `class` + `login-button`
- `placeholder` + `Email`
- `text` + `Login`
- `role` + `button`

For `role`, put the visible name in the `value` field if needed.

`role`을 쓸 때는 버튼 이름 같은 접근성 이름을 `value` 칸에 넣으면 됩니다.

## JSON Format

The runnable format is:

실행 가능한 JSON 형식은 아래와 같습니다.

```json
{
  "settings": {
    "headless": false,
    "timeout_ms": 10000,
    "start_url": ""
  },
  "steps": [
    {
      "action": "open",
      "selector_mode": "none",
      "selector": "",
      "value": "https://example.com/login",
      "note": "Launch browser and open first page",
      "required": true
    }
  ]
}
```

Field meanings:

- `action`: what to do
- `selector_mode`: how to find the element
- `selector`: selector value
- `value`: URL, input text, or role name depending on the action
- `note`: free memo
- `required`: if true, stop when that step fails

필드 의미는 아래와 같습니다.

- `action`: 수행할 동작
- `selector_mode`: 요소를 찾는 방식
- `selector`: selector 값
- `value`: URL, 입력값, role 이름 등 액션에 따라 달라지는 값
- `note`: 자유 메모
- `required`: `true`이면 실패 시 실행 중단

## Files

- [main.py](/E:/3_DEV/click_next_click/main.py)
- [data/action1.json](/E:/3_DEV/click_next_click/data/action1.json)
- [data/action2.json](/E:/3_DEV/click_next_click/data/action2.json)
- [data/action3.json](/E:/3_DEV/click_next_click/data/action3.json)

`action1.json` and `action2.json` are earlier rough ideas.

`action1.json`, `action2.json`은 초기 구상 예시로 남겨둔 파일입니다.

Use `action3.json` as the current working example for the code in `main.py`.

현재 코드와 맞는 기준 샘플은 `action3.json`입니다.

## Run

```bash
python main.py
```

실행은 위 명령으로 하면 됩니다.

## UI Flow

1. Set browser options at the top.
2. Add a step.
3. Choose an `action`.
4. Choose a `selector_mode`.
5. Enter `selector`, `value`, and optional `note`.
6. Save to `/data`.
7. Load again later or run immediately.

사용 흐름은 아래와 같습니다.

1. 상단에서 브라우저 옵션을 설정합니다.
2. step을 추가합니다.
3. `action`을 선택합니다.
4. `selector_mode`를 선택합니다.
5. `selector`, `value`, `note`를 입력합니다.
6. `/data`에 JSON으로 저장합니다.
7. 나중에 다시 불러오거나 바로 실행합니다.

## Action Behavior

- `open`: starts Playwright Chromium and optionally opens the URL in `value`, otherwise uses `settings.start_url`
- `goto`: moves the current page to the URL in `value`
- `check`: verifies whether the target element exists
- `wait`: waits until the target element is visible
- `click`: clicks the first matched element
- `fill`: fills the first matched element with `value`
- `close`: closes page, context, browser, and Playwright safely

각 액션의 동작은 아래와 같습니다.

- `open`: Playwright Chromium을 시작하고, `value`에 URL이 있으면 그 주소를 열고 없으면 `settings.start_url`을 사용합니다.
- `goto`: 현재 페이지를 `value`의 URL로 이동시킵니다.
- `check`: 대상 요소가 존재하는지 확인합니다.
- `wait`: 대상 요소가 보일 때까지 기다립니다.
- `click`: 첫 번째로 매칭된 요소를 클릭합니다.
- `fill`: 첫 번째로 매칭된 요소에 `value`를 입력합니다.
- `close`: page, context, browser, Playwright를 안전하게 종료합니다.

## Notes

- The implementation stays intentionally small so new actions can be added without redesigning the whole app.
- The JSON order is the routine order.
- If a `required` step fails, execution stops.

추가 메모입니다.

- 구현은 의도적으로 작게 유지해서, 나중에 액션을 추가해도 전체 구조를 다시 짤 필요가 없게 했습니다.
- JSON 순서가 곧 실행 순서입니다.
- `required` step이 실패하면 실행을 중단합니다.
