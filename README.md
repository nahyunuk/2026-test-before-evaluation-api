# Hire Up API

2026년 전국 기능경기대회 - 채용 플랫폼 Hire Up의 백엔드 API 명세입니다.

**Base URL:** `http://api.hireup.com`

---

## 로컬 실행

### 요구사항
- Python 3.10 이상

### 설치 및 실행

```bash
# 1. 가상환경 활성화
.venv\Scripts\activate  # Windows

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 서버 실행
uvicorn main:app --reload --port 3000 --host 0.0.0.0
```

서버가 실행되면 `http://localhost:3000` 으로 접속할 수 있습니다.

| URL | 설명 |
|---|---|
| `http://localhost:3000` | API 서버 |
| `http://localhost:3000/docs` | Swagger UI (자동 생성) |
| `http://localhost:3000/redoc` | ReDoc 문서 |

### 테스트 계정

| 항목 | 값 |
|---|---|
| 이메일 | `test@example.com` |
| 비밀번호 | `Test1234!` |
| 토큰 | `test_token` |
| 사용자 ID | `1` |

---

## 인증

| 방식 | 형식 |
|---|---|
| Bearer Token | `Authorization: Bearer {token}` |
| Query 인증 | `?userId={userId}` |

---

## Module A

### 001. 인증

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/auth/login` | 로그인 |
| `POST` | `/auth/phone/send` | 휴대폰 인증번호 발송 |
| `POST` | `/auth/phone/verify` | 인증번호 확인 |
| `POST` | `/auth/signup` | 회원가입 |

#### POST /auth/login
- **Body:** `email`, `password`
- **200:** JWT 토큰 + 사용자 정보 반환
- **401:** `INVALID_CREDENTIALS`

#### POST /auth/phone/send
- **Body:** `phone` (숫자만, 11자리)
- **200:** `expiresIn: 180` (초)

#### POST /auth/phone/verify
- **Body:** `phone`, `code`
- **비고:** 코드 값에 상관없이 입력만 하면 통과

#### POST /auth/signup
- **Body:** `email`, `password`, `name`, `phone` (인증 완료된 번호)
- **비밀번호 규칙:** 8자 이상, 대/소문자 + 숫자 + 특수문자 각 1자 이상
- **201:** 생성된 사용자 정보 반환
- **409:** 이메일 중복 (`DUPLICATE`)

---

### 002. 공고 조회

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/jobs` | 공고 목록 조회 |

#### GET /jobs

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| category | string | N | 직무 카테고리 (`DEV` / `DESIGN` / `MARKETING` / `HR`) |
| sort | string | N | 정렬 기준 (기본: `latest`) |
| keyword | string | N | 검색어 |
| page | int | N | 페이지 번호 (기본: 1) |
| size | int | N | 페이지 크기 (기본: 20) |

**sort 코드**

| 코드 | 설명 |
|---|---|
| `latest` | 등록일 내림차순 |
| `popular` | 조회수 내림차순 |
| `salary` | 급여 내림차순 |

`deadlineLabel` 규칙: 마감 시 `마감`, 당일 `오늘 마감`, 7일 이내 `{n}일 전`

---

### 003. 검색

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/search/popular` | 인기 검색어 목록 조회 |

---

## Module B

### 001. 추천 공고

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/jobs/recommended` | 오늘의 추천 공고 조회 |

#### GET /jobs/recommended

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| limit | int | N | 조회 개수 (홈 가로 스크롤용) |

**recruitStatus 코드**

| 코드 | 설명 | 색상 |
|---|---|---|
| `OPEN` | 채용중 | `#3366FF` |
| `CLOSING` | 마감임박 | `#FF9500` |
| `CLOSED` | 마감 | `#999999` |

---

### 002. 공고 상세

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/jobs/{id}` | 공고 상세 조회 |

- **200:** 회사명, 로고, 직무, 채용상태, 위치, 연차, 급여, 고용형태, 마감일, 포지션 소개, 담당업무, 자격요건, 복리후생
- **404:** `NOT_FOUND`

---

### 003. AI 모의 면접

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/interview/questions` | 면접 질문 목록 조회 |

#### GET /interview/questions

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| jobRole | string | Y | 직무 코드 (`FRONTEND` / `BACKEND` / `DATA` / `PM` / `DESIGN`) |
| career | string | N | 연차 코드 |
| type | string | N | 면접 유형 코드 |

**career 코드**

| 코드 | 설명 |
|---|---|
| `NEW` | 신입 (0~1년) |
| `JUNIOR` | 주니어 (2~3년) |
| `MIDDLE` | 미들 (4~7년) |
| `SENIOR` | 시니어 (8년+) |

**type 코드**

| 코드 | 설명 |
|---|---|
| `GENERAL` | 일반 면접 |
| `PRACTICAL` | 실무 면접 |
| `PERSONALITY` | 인성 면접 |

- **200:** 질문 목록 (질문 번호, 텍스트, 오디오 URL, 재생 시간)
- **인증 필요:** `Authorization: Bearer {token}`

---

## 공통 응답 형식

```json
// 성공
{ "success": true, "message": "...", "data": { ... } }

// 실패
{ "success": false, "message": "...", "errors": [{ "code": "...", "field": "...", "message": "..." }] }
```