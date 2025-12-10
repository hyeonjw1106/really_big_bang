# Cosmos Rendering API (FastAPI)

우주 시각화 백엔드의 HTTP API 명세입니다. 기본 URL은 `/`이며, 모든 응답은 JSON입니다. 인증은 아직 적용되지 않았습니다.

## 헬스체크
- `GET /health` → `{"status": "ok"}` 서버 동작 확인용.

## Epochs
- `GET /epochs?limit=50&offset=0`  
  에폭 리스트. `start_norm`, `end_norm`은 0~1 범위의 정규화된 우주 시간.
- `GET /epochs/{epoch_id}`  
  단일 에폭 상세, `annotations` 포함.
- `GET /epochs/{epoch_id}/annotations`  
  특정 에폭의 타임라인 주석 목록(`time_mark`는 0~1 정규화).

## Elements
- `GET /elements?limit=50&offset=0`  
  입자/원소/천체 정의 목록.
- `GET /elements/{element_id}`  
  단일 엘리먼트 상세.

## Scene(블렌더 파일) 관리
- `POST /renders/scenes` (multipart/form-data)  
  - 필드: `file`(필수, .blend), `name`(선택, UI 표시용)  
  - 응답: `SceneOut { id, name, original_name, file_size, uploaded_at }`  
  - 동작: `DATA_DIR/scenes/` 아래에 저장 후 DB 기록.
- `GET /renders/scenes?limit=50&offset=0`  
  업로드된 씬 목록(최근 업로드 순).

## Render Job
- `POST /renders` (application/json)  
  - 바디:
    ```json
    {
      "scene_id": 1,
      "epoch_id": 2,
      "time_norm": 0.37,
      "resolution_x": 1920,
      "resolution_y": 1080,
      "format": "PNG",
      "camera": "Camera"
    }
    ```
  - `scene_id`가 없으면 서버가 placeholder 씬을 자동 생성/사용.
  - 응답: `RenderJobOut { id, scene_id, epoch_id, time_norm, status, message, output_path, params, created_at, updated_at }`  
  - 동작: 상태 `queued` 로 Job 생성 후 비동기 처리 큐에 넣음. 현재 구현은 블렌더 연동 대신 더미 PNG를 생성해 `status=done` 으로 업데이트(실제 렌더러 연결 지점 표식).
- `GET /renders?limit=50&offset=0`  
  렌더 Job 목록(최신순).
- `GET /renders/{job_id}`  
  렌더 Job 상세 상태.
- `GET /renders/{job_id}/file`  
  `status=done` 인 Job 결과 파일 다운로드(현재는 PNG). 완료 전에는 400을 반환.

## Cosmic Events(큰 단계 전용)
- `GET /events?limit=50&offset=0`  
  통합과학/코스믹 타임라인의 주요 이벤트 목록(전자·쿼크 생성, 양성자·중성자 형성, 수소/헬륨 원자핵·원자 형성 등) 반환. `time_norm`은 0~1 정규화된 이벤트 위치, `time_range`는 교과서식 시간대 표현.
- `GET /events/{event_id}`  
  단일 이벤트 상세.
- `POST /events/{event_id}/render?scene_id=1` (scene_id가 없으면 이벤트에 설정된 default_scene_id 또는 placeholder 사용)  
  이벤트의 `time_norm`/`epoch_id`를 사용해 렌더 Job 생성. 현재는 블렌더 대신 더미 PNG를 만들어 결과를 반환하며, 추후 블렌더 렌더러로 교체 예정.

## 환경 변수
- `DB_DSN`: Async DB 연결 문자열(예: `mysql+asyncmy://user:pwd@localhost:3306/cosmos`).
- `API_ORIGINS`: CORS 허용 origin(쉼표 구분).
- `DATA_DIR`: 업로드/렌더 결과 저장 경로 기본값 `data` (상대경로 가능).

## 렌더 연동 가이드(스텁)
현재는 백엔드에서 더미 파일을 생성하지만, `_enqueue_render` 함수 내부에서 실제 블렌더 렌더러 호출로 교체하면 됩니다. `job.params`에 해상도/포맷/카메라 설정이 포함되어 있어 워커 프로세스에서 그대로 사용할 수 있습니다.
