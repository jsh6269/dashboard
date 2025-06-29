# Dashboard 통합 프로젝트

이 프로젝트는 다음 기술 스택을 한 번에 학습할 수 있도록 구성되었습니다.

- Python FastAPI
- MySQL(dashboard_db, 비밀번호 password)
- Elasticsearch
- Dockerfile(커스텀 이미지) + 외부 이미지(mysql, elasticsearch)
- Docker Compose
- Ubuntu 기반 컨테이너
- 외부에서 접근할 수 있는 3개 포트
  - 8000: Dashboard REST API
  - 9200: Elasticsearch REST API
  - 3000: 정적 프런트엔드 (Nginx)

## 사전 준비

- Docker ≥ 20.10
- Docker Compose ≥ v2

## 실행 방법

```bash
# 프로젝트 루트(example)에서
docker compose up --build -d        # 최초 실행(전체 빌드)

# 코드 수정 후 API 서비스만 빠르게 재배포하고 싶을 때
docker compose up -d --no-deps --build api  # db/es/front 컨테이너는 그대로 유지
```

서비스 확인:

- http://localhost:8000/docs – Dashboard REST API 문서
- http://localhost:9200 – Elasticsearch 노드 정보
- http://localhost:3000 – 정적 프런트(아이템 추가/검색 UI)

## Front / Back 구성

### Front-end (Nginx 정적 서버)

- 경로: `frontend/`
- 이미지: `nginx:alpine`
- 포트 매핑: `3000:80`
  - `3000` (호스트) → `80` (컨테이너)  
    즉 브라우저에서 `http://localhost:3000` 요청 시 컨테이너 내부 Nginx(80번 포트)에 전달되어 정적 페이지를 반환
- 주요 파일
  - `index.html` : 기본 페이지 (폼 + 결과 렌더링)
  - `styles.css` : UI 스타일
  - `main.js` : API 호출 및 동적 렌더링 로직
  - `favicon.ico`: 파비콘
- 제공 기능
  1. 대시보드 아이템 등록(제목, 설명, 이미지 업로드)
  2. 아이템 검색 및 결과 카드 렌더링

### Back-end (FastAPI)

- 경로: `app/`
- 주요 엔드포인트
  - `POST /items` : multipart/form-data 로 아이템 생성 (이미지 업로드 포함)
  - `GET /search` : Elasticsearch 기반 아이템 검색
  - Swagger UI : `http://localhost:8000/docs`
- 내부 구성
  - MySQL 8.0 (`dashboard_db`, 비밀번호 `password`)
  - Elasticsearch 8.x (`dashboard_items` 인덱스)

## 사용 예시 (CLI)

1. **이미지 없이 아이템 추가**

```bash
curl -X POST "http://localhost:8000/items" \
     -F "title=Hello" \
     -F "description=No image"
```

2. **이미지 포함 아이템 추가**

```bash
curl -X POST "http://localhost:8000/items" \
     -F "title=With image" \
     -F "description=Sample" \
     -F "image=@/absolute/path/to/file.png"
```

3. **검색**

```bash
curl "http://localhost:8000/search?q=Hello"
```

브라우저에서 http://localhost:3000 을 열어 UI 로도 동일 기능을 테스트할 수 있습니다.

## 데이터 보존

- `mysql_data` 볼륨: MySQL 데이터
- `es_data` 볼륨: Elasticsearch 데이터

## 구조

```
example/
├── app/
│   ├── main.py            # FastAPI 라우터
│   ├── models.py          # SQLAlchemy ORM
│   ├── schemas.py         # Pydantic 스키마
│   └── dependencies.py    # FastAPI Depends 함수
├── frontend/
│   ├── index.html
│   ├── styles.css
│   ├── main.js
│   └── favicon.ico
├── Dockerfile             # Ubuntu 기반 커스텀 Python 이미지
├── docker-compose.yml
├── requirements.txt
└── README.md
```

- - 아이템 추가 시 선택적으로 이미지 업로드 가능(프런트 파일 입력 또는 curl -F)
    ...

```bash
curl -X POST "http://localhost:8000/items" \
     -F "title=Hello" \
     -F "description=With image" \
     -F "image=@path/to/file.png"
```

검색 결과 또는 응답에서 `image_path` 값이 있으면 브라우저에서 `http://localhost:8000/<image_path>` 로 접근하여 이미지를 확인할 수 있습니다.
