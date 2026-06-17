from fastapi import FastAPI, Header, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Any
import re
import secrets
import time
from datetime import date
import os

app = FastAPI(title="Hire Up API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙 (company 로고 이미지)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/company", StaticFiles(directory=os.path.join(BASE_DIR, "company")), name="company")
app.mount("/interview", StaticFiles(directory=os.path.join(BASE_DIR, "interview")), name="interview")

# ── In-memory stores ──────────────────────────────────────────
users_db: dict = {}
email_index: dict = {}
tokens_db: dict = {}
phone_codes: dict = {}
_next_id = 2

# 테스트용 기본 유저
users_db[1] = {"id": 1, "email": "test@example.com", "name": "홍길동", "phone": "01000000000", "password": "Test1234!"}
email_index["test@example.com"] = 1
tokens_db["test_token"] = 1

# ── Mock 공고 데이터 ──────────────────────────────────────────
MOCK_JOBS = [
    {
        "id": 1,
        "companyName": "카카오",
        "companyLogo": "kakao.png",
        "jobTitle": "프론트엔드 개발자",
        "location": "경기 성남시 분당구",
        "employmentType": "정규직",
        "career": "경력 3년↑",
        "salary": "4,000~6,000만원",
        "deadline": "2026-07-31",
        "viewCount": 1200,
        "createdAt": "2026-06-10T09:00:00+09:00",
        "category": "DEV",
        "positionIntro": "사용자 경험을 책임지는 프론트엔드 개발자를 찾습니다.",
        "tasks": ["웹 서비스 UI 개발", "사내 디자인 시스템 구축"],
        "qualifications": ["React 3년 이상 경험", "REST API 연동 경험"],
        "benefits": ["유연근무", "식대 지원", "교육비 지원"],
    },
    {
        "id": 2,
        "companyName": "네이버",
        "companyLogo": "naver.png",
        "jobTitle": "백엔드 개발자",
        "location": "경기 성남시 분당구",
        "employmentType": "정규직",
        "career": "경력 2년↑",
        "salary": "4,500~7,000만원",
        "deadline": "2026-07-15",
        "viewCount": 980,
        "createdAt": "2026-06-08T10:00:00+09:00",
        "category": "DEV",
        "positionIntro": "글로벌 서비스를 만드는 백엔드 개발자를 채용합니다.",
        "tasks": ["RESTful API 개발", "대용량 트래픽 처리 시스템 설계"],
        "qualifications": ["Java/Spring 경험", "MySQL/Redis 경험"],
        "benefits": ["스톡옵션", "유연근무", "사내 카페테리아"],
    },
    {
        "id": 3,
        "companyName": "토스",
        "companyLogo": "toss.png",
        "jobTitle": "그로스 마케터",
        "location": "서울 강남구",
        "employmentType": "정규직",
        "career": "경력 2년↑",
        "salary": "5,000~8,000만원",
        "deadline": "2026-06-20",
        "viewCount": 860,
        "createdAt": "2026-06-12T11:00:00+09:00",
        "category": "MARKETING",
        "positionIntro": "데이터 기반으로 금융 서비스 성장을 이끌어갈 그로스 마케터를 모집합니다.",
        "tasks": ["퍼널 분석 및 전환율 최적화", "A/B 테스트 설계 및 성과 분석"],
        "qualifications": ["그로스 해킹 경험 2년 이상", "SQL/데이터 분석 능숙"],
        "benefits": ["자율 출퇴근", "무제한 휴가", "최신 장비 지원"],
    },
    {
        "id": 4,
        "companyName": "무신사",
        "companyLogo": "musinsa.png",
        "jobTitle": "UX/UI 디자이너",
        "location": "서울 성동구",
        "employmentType": "정규직",
        "career": "경력 1년↑",
        "salary": "3,500~5,000만원",
        "deadline": "2026-07-10",
        "viewCount": 620,
        "createdAt": "2026-06-11T09:00:00+09:00",
        "category": "DESIGN",
        "positionIntro": "패션 커머스 UX/UI를 담당할 디자이너를 모집합니다.",
        "tasks": ["앱/웹 UI 디자인", "사용자 리서치 및 IA 설계"],
        "qualifications": ["Figma 능숙", "커머스 서비스 경험 우대"],
        "benefits": ["임직원 할인", "유연근무", "도서 지원"],
    },
    {
        "id": 5,
        "companyName": "쿠팡",
        "companyLogo": "coupang.png",
        "jobTitle": "퍼포먼스 마케터",
        "location": "서울 송파구",
        "employmentType": "정규직",
        "career": "경력 3년↑",
        "salary": "6,000~10,000만원",
        "deadline": "2026-05-30",
        "viewCount": 2100,
        "createdAt": "2026-05-01T09:00:00+09:00",
        "category": "MARKETING",
        "positionIntro": "로켓배송 브랜드를 알릴 퍼포먼스 마케터를 채용합니다.",
        "tasks": ["온라인 광고 집행 및 성과 분석", "CPA/ROAS 최적화"],
        "qualifications": ["퍼포먼스 마케팅 경험 3년 이상", "GA/Meta Ads 운영 경험"],
        "benefits": ["성과급", "스톡옵션", "글로벌 오피스 경험"],
    },
    {
        "id": 6,
        "companyName": "당근마켓",
        "companyLogo": "karrot.png",
        "jobTitle": "iOS 개발자",
        "location": "서울 마포구",
        "employmentType": "정규직",
        "career": "경력 2년↑",
        "salary": "4,500~7,000만원",
        "deadline": "2026-06-18",
        "viewCount": 750,
        "createdAt": "2026-06-09T10:00:00+09:00",
        "category": "DEV",
        "positionIntro": "동네 생활 서비스를 함께 만들어 갈 iOS 개발자를 찾습니다.",
        "tasks": ["iOS 앱 신규 기능 개발", "앱 성능 최적화"],
        "qualifications": ["Swift 2년 이상 경험", "UIKit/SwiftUI 경험"],
        "benefits": ["자율 출퇴근", "원격 근무", "최신 맥북 지급"],
    },
    {
        "id": 7,
        "companyName": "우아한형제들",
        "companyLogo": "woowa.png",
        "jobTitle": "백엔드 개발자 (Java)",
        "location": "서울 송파구",
        "employmentType": "정규직",
        "career": "경력 3년↑",
        "salary": "5,000~8,000만원",
        "deadline": "2026-07-20",
        "viewCount": 890,
        "createdAt": "2026-06-07T09:00:00+09:00",
        "category": "DEV",
        "positionIntro": "배달의민족 서버를 담당할 백엔드 개발자를 모집합니다.",
        "tasks": ["주문/결제 시스템 개발", "MSA 기반 서비스 설계"],
        "qualifications": ["Java/Spring Boot 3년 이상", "대용량 트래픽 처리 경험"],
        "benefits": ["반반 무료", "자율 출퇴근", "교육비 지원"],
    },
    {
        "id": 8,
        "companyName": "야놀자",
        "companyLogo": "yanolja.png",
        "jobTitle": "브랜드 마케터",
        "location": "서울 강남구",
        "employmentType": "정규직",
        "career": "경력 2년↑",
        "salary": "4,000~6,500만원",
        "deadline": "2026-06-16",
        "viewCount": 430,
        "createdAt": "2026-06-05T11:00:00+09:00",
        "category": "MARKETING",
        "positionIntro": "여행/숙박 브랜드를 기획하고 확산시킬 마케터를 찾습니다.",
        "tasks": ["브랜드 캠페인 기획 및 운영", "SNS 채널 마케팅"],
        "qualifications": ["브랜드 마케팅 경험 2년 이상", "콘텐츠 기획 능력"],
        "benefits": ["숙박 할인", "유연근무", "의료비 지원"],
    },
    {
        "id": 9,
        "companyName": "직방",
        "companyLogo": "zigbang.png",
        "jobTitle": "프론트엔드 개발자 (React)",
        "location": "서울 강남구",
        "employmentType": "정규직",
        "career": "경력 1년↑",
        "salary": "3,500~5,500만원",
        "deadline": "2026-08-01",
        "viewCount": 510,
        "createdAt": "2026-06-13T10:00:00+09:00",
        "category": "DEV",
        "positionIntro": "부동산 플랫폼 프론트엔드를 함께 만들어갈 개발자를 모집합니다.",
        "tasks": ["React 기반 웹 서비스 개발", "지도 연동 UI 구현"],
        "qualifications": ["React/TypeScript 경험", "지도 API 연동 경험 우대"],
        "benefits": ["유연근무", "식대 지원", "자기계발비"],
    },
    {
        "id": 10,
        "companyName": "라인",
        "companyLogo": "line.png",
        "jobTitle": "글로벌 서비스 개발자",
        "location": "서울 강남구",
        "employmentType": "정규직",
        "career": "경력 3년↑",
        "salary": "5,500~9,000만원",
        "deadline": "2026-06-22",
        "viewCount": 1050,
        "createdAt": "2026-06-06T09:00:00+09:00",
        "category": "DEV",
        "positionIntro": "글로벌 메신저 서비스를 만드는 개발자를 찾습니다.",
        "tasks": ["글로벌 메신저 기능 개발", "다국어/다지역 서비스 최적화"],
        "qualifications": ["Java 또는 Go 경험", "영어 커뮤니케이션 가능"],
        "benefits": ["글로벌 오피스 파견", "스톡옵션", "어학 지원"],
    },
    {
        "id": 11,
        "companyName": "AWS코리아",
        "companyLogo": "aws.png",
        "jobTitle": "클라우드 솔루션 아키텍트",
        "location": "서울 강남구",
        "employmentType": "정규직",
        "career": "경력 5년↑",
        "salary": "8,000~15,000만원",
        "deadline": "2026-07-05",
        "viewCount": 1680,
        "createdAt": "2026-06-03T09:00:00+09:00",
        "category": "DEV",
        "positionIntro": "고객사의 클라우드 아키텍처를 설계하고 컨설팅합니다.",
        "tasks": ["엔터프라이즈 고객 AWS 아키텍처 설계", "기술 영업 지원"],
        "qualifications": ["AWS 자격증 보유", "클라우드 인프라 경험 5년 이상"],
        "benefits": ["글로벌 복지", "RSU 지급", "교육 지원"],
    },
    {
        "id": 12,
        "companyName": "원티드",
        "companyLogo": "wanted.png",
        "jobTitle": "콘텐츠 마케터",
        "location": "서울 서초구",
        "employmentType": "정규직",
        "career": "경력 2년↑",
        "salary": "4,000~6,500만원",
        "deadline": "2026-06-17",
        "viewCount": 730,
        "createdAt": "2026-06-10T10:00:00+09:00",
        "category": "MARKETING",
        "positionIntro": "채용 플랫폼의 콘텐츠 마케팅을 이끌 마케터를 모집합니다.",
        "tasks": ["블로그/SNS 콘텐츠 기획 및 제작", "채용 트렌드 리포트 발행"],
        "qualifications": ["콘텐츠 마케팅 경험 2년 이상", "카피라이팅 능력"],
        "benefits": ["스톡옵션", "자율 출퇴근", "교육비 지원"],
    },
    {
        "id": 13,
        "companyName": "프로토파이",
        "companyLogo": "protopie.png",
        "jobTitle": "UX 디자이너",
        "location": "서울 강남구",
        "employmentType": "정규직",
        "career": "경력 1년↑",
        "salary": "3,500~5,000만원",
        "deadline": "2026-07-25",
        "viewCount": 390,
        "createdAt": "2026-06-14T09:00:00+09:00",
        "category": "DESIGN",
        "positionIntro": "글로벌 프로토타이핑 툴의 UX를 책임질 디자이너를 찾습니다.",
        "tasks": ["프로토타이핑 툴 UX 설계", "글로벌 사용자 리서치"],
        "qualifications": ["Figma/ProtoPie 능숙", "영어 커뮤니케이션 가능"],
        "benefits": ["글로벌 환경", "유연근무", "최신 장비 지급"],
    },
    {
        "id": 14,
        "companyName": "스트림랩스",
        "companyLogo": "streamlab.png",
        "jobTitle": "AI 엔지니어",
        "location": "서울 마포구",
        "employmentType": "정규직",
        "career": "경력 2년↑",
        "salary": "5,000~8,000만원",
        "deadline": "2026-05-01",
        "viewCount": 920,
        "createdAt": "2026-04-10T09:00:00+09:00",
        "category": "DEV",
        "positionIntro": "스트리밍 서비스에 AI 기술을 접목할 엔지니어를 모집합니다.",
        "tasks": ["추천 알고리즘 개발", "ML 모델 배포 및 운영"],
        "qualifications": ["PyTorch/TensorFlow 경험", "ML 모델 서빙 경험"],
        "benefits": ["스톡옵션", "원격 근무", "컨퍼런스 지원"],
    },
    {
        "id": 15,
        "companyName": "플로우테크",
        "companyLogo": "flowtech.png",
        "jobTitle": "풀스택 개발자",
        "location": "서울 영등포구",
        "employmentType": "정규직",
        "career": "경력 2년↑",
        "salary": "3,500~5,500만원",
        "deadline": "2026-07-01",
        "viewCount": 310,
        "createdAt": "2026-06-11T11:00:00+09:00",
        "category": "DEV",
        "positionIntro": "스타트업에서 풀스택으로 서비스를 함께 만들어갈 개발자를 찾습니다.",
        "tasks": ["프론트/백엔드 기능 개발", "인프라 관리"],
        "qualifications": ["React + Node.js 또는 Python 경험", "AWS 기본 지식"],
        "benefits": ["스톡옵션", "자율 출퇴근", "성장 지원금"],
    },
    {
        "id": 16,
        "companyName": "카카오",
        "companyLogo": "kakao.png",
        "jobTitle": "HR 비즈니스 파트너",
        "location": "경기 성남시 분당구",
        "employmentType": "정규직",
        "career": "경력 3년↑",
        "salary": "4,500~7,000만원",
        "deadline": "2026-07-20",
        "viewCount": 540,
        "createdAt": "2026-06-11T09:00:00+09:00",
        "category": "HR",
        "positionIntro": "카카오의 조직문화와 인재를 함께 만들어갈 HR BP를 모집합니다.",
        "tasks": ["사업부 HR 파트너링", "채용 기획 및 운영", "조직문화 프로그램 설계"],
        "qualifications": ["HR 실무 경험 3년 이상", "채용/조직개발 경험 보유"],
        "benefits": ["유연근무", "식대 지원", "교육비 지원"],
    },
    {
        "id": 17,
        "companyName": "네이버",
        "companyLogo": "naver.png",
        "jobTitle": "채용 담당자",
        "location": "경기 성남시 분당구",
        "employmentType": "정규직",
        "career": "경력 2년↑",
        "salary": "4,000~6,000만원",
        "deadline": "2026-08-05",
        "viewCount": 380,
        "createdAt": "2026-06-12T10:00:00+09:00",
        "category": "HR",
        "positionIntro": "글로벌 IT 기업의 기술직군 채용을 담당할 리크루터를 찾습니다.",
        "tasks": ["개발/기획직 채용 전반 운영", "채용 공고 기획 및 면접 조율", "채용 데이터 분석 및 개선"],
        "qualifications": ["IT 업종 채용 경험 2년 이상", "ATS 툴 사용 경험"],
        "benefits": ["스톡옵션", "유연근무", "사내 카페테리아"],
    },
    {
        "id": 18,
        "companyName": "원티드",
        "companyLogo": "wanted.png",
        "jobTitle": "HR 컨설턴트",
        "location": "서울 서초구",
        "employmentType": "정규직",
        "career": "경력 1년↑",
        "salary": "3,500~5,500만원",
        "deadline": "2026-07-15",
        "viewCount": 290,
        "createdAt": "2026-06-13T11:00:00+09:00",
        "category": "HR",
        "positionIntro": "기업 고객의 채용 문제를 함께 해결하는 HR 컨설턴트를 모집합니다.",
        "tasks": ["기업 채용 니즈 파악 및 솔루션 제안", "후보자 서칭 및 매칭", "채용 성과 리포트 작성"],
        "qualifications": ["HR 또는 영업 경험 1년 이상", "커뮤니케이션 능력 우수"],
        "benefits": ["성과급", "자율 출퇴근", "교육비 지원"],
    },
]

# ── 면접 질문 데이터 ──────────────────────────────────────────
INTERVIEW_QUESTIONS: dict = {
    "FRONTEND": [
        {"questionNumber": 1, "questionText": "자기소개를 부탁드립니다.", "audioUrl": "https://cdn.hireup.com/interview/fe_q1.mp3", "duration": 8},
        {"questionNumber": 2, "questionText": "React의 Virtual DOM에 대해 설명해주세요.", "audioUrl": "https://cdn.hireup.com/interview/fe_q2.mp3", "duration": 10},
        {"questionNumber": 3, "questionText": "상태 관리 라이브러리를 사용해 본 경험이 있으신가요?", "audioUrl": "https://cdn.hireup.com/interview/fe_q3.mp3", "duration": 10},
        {"questionNumber": 4, "questionText": "크로스 브라우저 호환성 이슈를 해결한 경험을 말씀해주세요.", "audioUrl": "https://cdn.hireup.com/interview/fe_q4.mp3", "duration": 12},
        {"questionNumber": 5, "questionText": "웹 성능 최적화 방법에 대해 아는 것을 말씀해주세요.", "audioUrl": "https://cdn.hireup.com/interview/fe_q5.mp3", "duration": 12},
    ],
    "BACKEND": [
        {"questionNumber": 1, "questionText": "자기소개를 부탁드립니다.", "audioUrl": "https://cdn.hireup.com/interview/be_q1.mp3", "duration": 8},
        {"questionNumber": 2, "questionText": "RESTful API 설계 원칙에 대해 설명해주세요.", "audioUrl": "https://cdn.hireup.com/interview/be_q2.mp3", "duration": 10},
        {"questionNumber": 3, "questionText": "데이터베이스 인덱스에 대해 설명해주세요.", "audioUrl": "https://cdn.hireup.com/interview/be_q3.mp3", "duration": 10},
        {"questionNumber": 4, "questionText": "동시성 처리 방법에 대해 아는 것을 말씀해주세요.", "audioUrl": "https://cdn.hireup.com/interview/be_q4.mp3", "duration": 12},
        {"questionNumber": 5, "questionText": "마이크로서비스 아키텍처의 장단점을 설명해주세요.", "audioUrl": "https://cdn.hireup.com/interview/be_q5.mp3", "duration": 12},
    ],
    "DATA": [
        {"questionNumber": 1, "questionText": "자기소개를 부탁드립니다.", "audioUrl": "https://cdn.hireup.com/interview/data_q1.mp3", "duration": 8},
        {"questionNumber": 2, "questionText": "데이터 분석 프로세스에 대해 설명해주세요.", "audioUrl": "https://cdn.hireup.com/interview/data_q2.mp3", "duration": 10},
        {"questionNumber": 3, "questionText": "사용해본 데이터 시각화 도구를 말씀해주세요.", "audioUrl": "https://cdn.hireup.com/interview/data_q3.mp3", "duration": 10},
        {"questionNumber": 4, "questionText": "SQL 쿼리 최적화 경험이 있으신가요?", "audioUrl": "https://cdn.hireup.com/interview/data_q4.mp3", "duration": 12},
        {"questionNumber": 5, "questionText": "머신러닝 모델을 활용한 프로젝트 경험을 말씀해주세요.", "audioUrl": "https://cdn.hireup.com/interview/data_q5.mp3", "duration": 12},
    ],
    "PM": [
        {"questionNumber": 1, "questionText": "자기소개를 부탁드립니다.", "audioUrl": "https://cdn.hireup.com/interview/pm_q1.mp3", "duration": 8},
        {"questionNumber": 2, "questionText": "제품 로드맵을 어떻게 수립하시나요?", "audioUrl": "https://cdn.hireup.com/interview/pm_q2.mp3", "duration": 10},
        {"questionNumber": 3, "questionText": "개발팀과 협업할 때 어려웠던 점을 말씀해주세요.", "audioUrl": "https://cdn.hireup.com/interview/pm_q3.mp3", "duration": 10},
        {"questionNumber": 4, "questionText": "지표를 기반으로 의사결정을 한 경험을 설명해주세요.", "audioUrl": "https://cdn.hireup.com/interview/pm_q4.mp3", "duration": 12},
        {"questionNumber": 5, "questionText": "본인이 성장시킨 서비스의 성과 지표를 공유해주세요.", "audioUrl": "https://cdn.hireup.com/interview/pm_q5.mp3", "duration": 12},
    ],
    "DESIGN": [
        {"questionNumber": 1, "questionText": "자기소개를 부탁드립니다.", "audioUrl": "https://cdn.hireup.com/interview/ds_q1.mp3", "duration": 8},
        {"questionNumber": 2, "questionText": "UX 리서치 방법론에 대해 설명해주세요.", "audioUrl": "https://cdn.hireup.com/interview/ds_q2.mp3", "duration": 10},
        {"questionNumber": 3, "questionText": "디자인 시스템을 구축한 경험이 있으신가요?", "audioUrl": "https://cdn.hireup.com/interview/ds_q3.mp3", "duration": 10},
        {"questionNumber": 4, "questionText": "개발자와 소통할 때 사용하는 방법을 말씀해주세요.", "audioUrl": "https://cdn.hireup.com/interview/ds_q4.mp3", "duration": 12},
        {"questionNumber": 5, "questionText": "사용자 피드백을 디자인에 반영한 사례를 공유해주세요.", "audioUrl": "https://cdn.hireup.com/interview/ds_q5.mp3", "duration": 12},
    ],
}


# ── 헬퍼 ─────────────────────────────────────────────────────

def _deadline_info(deadline_str: str) -> tuple:
    today = date.today()
    try:
        dl = date.fromisoformat(deadline_str)
    except Exception:
        return "OPEN", "", ""
    diff = (dl - today).days
    if diff < 0:
        return "CLOSED", "마감", f"D+{abs(diff)}"
    if diff == 0:
        return "CLOSING", "오늘 마감", "D-Day"
    if diff <= 7:
        return "CLOSING", f"{diff}일 전", f"D-{diff}"
    return "OPEN", f"{diff}일 전", f"D-{diff}"


def _logo_url(request: Request, filename: str) -> str:
    return str(request.base_url) + f"company/{filename}"


def ok(data: Any, message: str = None, status: int = 200) -> JSONResponse:
    body: dict = {"success": True}
    if message:
        body["message"] = message
    body["data"] = data
    return JSONResponse(body, status_code=status)


def fail(message: str, errors: list, status: int) -> JSONResponse:
    return JSONResponse({"success": False, "message": message, "errors": errors}, status_code=status)


def get_user(authorization: Optional[str] = Header(None), userId: Optional[int] = Query(None)):
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            uid = tokens_db.get(parts[1])
            if uid:
                return users_db.get(uid)
    if userId is not None:
        return users_db.get(userId)
    return None


# ── Pydantic 모델 ─────────────────────────────────────────────

class LoginBody(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None


class PhoneSendBody(BaseModel):
    phone: Optional[str] = None


class PhoneVerifyBody(BaseModel):
    phone: Optional[str] = None
    code: Optional[str] = None


class SignupBody(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None


# ── 인증 ──────────────────────────────────────────────────────

@app.post("/auth/login")
def login(body: LoginBody):
    errors = []
    email = (body.email or "").strip()

    if not email:
        errors.append({"code": "REQUIRED", "field": "email", "message": "이메일을 입력해주세요."})
    else:
        at = email.find("@")
        if at == -1 or "." not in email or (at > 0 and email[at - 1] == "."):
            errors.append({"code": "INVALID_FORMAT", "field": "email", "message": "올바른 이메일 형식을 입력해주세요."})

    pw = body.password or ""
    if not pw:
        errors.append({"code": "REQUIRED", "field": "password", "message": "비밀번호를 입력해주세요."})
    elif len(pw) < 6:
        errors.append({"code": "INVALID_LENGTH", "field": "password", "message": "비밀번호는 6자 이상이어야 합니다."})

    if errors:
        return fail("로그인 실패", errors, 400)

    uid = email_index.get(email)
    if uid is None or users_db[uid]["password"] != pw:
        return fail("로그인 실패", [{"code": "INVALID_CREDENTIALS", "message": "이메일 또는 비밀번호가 올바르지 않습니다."}], 401)

    token = secrets.token_hex(32)
    tokens_db[token] = uid
    u = users_db[uid]
    return ok({"token": token, "user": {"id": u["id"], "email": u["email"], "name": u["name"]}}, "로그인 성공")


@app.post("/auth/phone/send")
def phone_send(body: PhoneSendBody):
    errors = []
    phone = body.phone or ""

    if not phone:
        errors.append({"code": "REQUIRED", "field": "phone", "message": "휴대폰 번호를 입력해주세요."})
    elif not re.fullmatch(r"\d{11}", phone):
        errors.append({"code": "INVALID_FORMAT", "field": "phone", "message": "올바른 휴대폰 번호를 입력해주세요."})

    if errors:
        return fail("인증번호 발송 실패", errors, 400)

    phone_codes[phone] = {"code": "123456", "expires_at": time.time() + 180}
    return ok({"expiresIn": 180}, "인증번호가 발송되었습니다.")


@app.post("/auth/phone/verify")
def phone_verify(body: PhoneVerifyBody):
    code = body.code or ""

    if not code:
        return fail("인증 실패", [{"code": "REQUIRED", "field": "code", "message": "인증번호를 입력해주세요."}], 400)

    return ok({"verified": True}, "인증이 완료되었습니다.")


@app.post("/auth/signup")
def signup(body: SignupBody):
    global _next_id
    errors = []
    email = (body.email or "").strip()

    if not email:
        errors.append({"code": "REQUIRED", "field": "email", "message": "이메일을 입력해주세요."})
    elif "@" not in email:
        errors.append({"code": "INVALID_FORMAT", "field": "email", "message": "올바른 이메일 형식을 입력해주세요."})

    pw = body.password or ""
    if not pw:
        errors.append({"code": "REQUIRED", "field": "password", "message": "비밀번호를 입력해주세요."})
    elif len(pw) < 8:
        errors.append({"code": "INVALID_LENGTH", "field": "password", "message": "비밀번호는 8자 이상이어야 합니다."})
    elif not (re.search(r"[A-Z]", pw) and re.search(r"[a-z]", pw)
              and re.search(r"\d", pw) and re.search(r"[^A-Za-z0-9]", pw)):
        errors.append({"code": "INVALID_FORMAT", "field": "password", "message": "대/소문자, 숫자, 특수문자를 각 1자 이상 포함해야 합니다."})

    name = body.name or ""
    if not name:
        errors.append({"code": "REQUIRED", "field": "name", "message": "이름을 입력해주세요."})
    elif not re.fullmatch(r"[가-힣A-Za-z]+", name):
        errors.append({"code": "INVALID_FORMAT", "field": "name", "message": "이름은 한글 또는 영문만 입력 가능합니다."})

    phone = body.phone or ""
    if not phone:
        errors.append({"code": "REQUIRED", "field": "phone", "message": "휴대폰 번호를 입력해주세요."})
    elif not re.fullmatch(r"\d+", phone):
        errors.append({"code": "INVALID_FORMAT", "field": "phone", "message": "휴대폰 번호는 숫자만 입력 가능합니다."})

    if errors:
        return JSONResponse({"success": False, "message": "회원가입 실패", "errors": errors}, status_code=400)

    if email in email_index:
        return JSONResponse(
            {"success": False, "message": "회원가입 실패",
             "errors": [{"code": "DUPLICATE", "field": "email", "message": "이미 사용 중인 이메일입니다."}]},
            status_code=409,
        )

    uid = _next_id
    _next_id += 1
    users_db[uid] = {"id": uid, "email": email, "name": name, "phone": phone, "password": pw}
    email_index[email] = uid

    return JSONResponse(
        {"success": True, "message": "회원가입이 완료되었습니다.",
         "data": {"user": {"id": uid, "email": email, "name": name}}},
        status_code=201,
    )


# ── 공고 ──────────────────────────────────────────────────────

@app.get("/jobs/recommended")
def recommended_jobs(
    request: Request,
    limit: Optional[int] = Query(None, ge=1),
    user=Depends(get_user),
):
    items = sorted(MOCK_JOBS, key=lambda j: j["viewCount"], reverse=True)
    if limit is not None:
        items = items[:limit]

    result = []
    for j in items:
        status, label, dday = _deadline_info(j["deadline"])
        result.append({
            "id": j["id"],
            "companyName": j["companyName"],
            "companyLogo": _logo_url(request, j["companyLogo"]),
            "jobTitle": j["jobTitle"],
            "location": j["location"],
            "employmentType": j["employmentType"],
            "career": j["career"],
            "salary": j["salary"],
            "deadlineLabel": label,
            "dDay": dday,
            "recruitStatus": status,
        })
    return ok({"items": result})


@app.get("/jobs")
def list_jobs(
    request: Request,
    category: Optional[str] = Query(None),
    sort: str = Query("latest"),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    items = list(MOCK_JOBS)

    if category:
        items = [j for j in items if j["category"] == category]
    if keyword:
        kw = keyword.lower()
        items = [j for j in items if kw in j["jobTitle"].lower() or kw in j["companyName"].lower()]

    if sort == "popular":
        items.sort(key=lambda j: j["viewCount"], reverse=True)
    elif sort == "salary":
        items.sort(key=lambda j: j["salary"], reverse=True)
    else:
        items.sort(key=lambda j: j["createdAt"], reverse=True)

    total = len(items)
    paged = items[(page - 1) * size: page * size]

    result = []
    for j in paged:
        _, label, _ = _deadline_info(j["deadline"])
        result.append({
            "id": j["id"],
            "companyName": j["companyName"],
            "companyLogo": _logo_url(request, j["companyLogo"]),
            "jobTitle": j["jobTitle"],
            "location": j["location"],
            "employmentType": j["employmentType"],
            "career": j["career"],
            "salary": j["salary"],
            "deadlineLabel": label,
            "viewCount": j["viewCount"],
            "createdAt": j["createdAt"],
        })

    return ok({"items": result, "page": page, "size": size, "totalCount": total})


@app.get("/jobs/{job_id}")
def job_detail(request: Request, job_id: int):
    job = next((j for j in MOCK_JOBS if j["id"] == job_id), None)
    if not job:
        return fail(
            "공고를 찾을 수 없습니다.",
            [{"code": "NOT_FOUND", "field": "id", "message": "존재하지 않는 공고입니다."}],
            404,
        )

    status, _, _ = _deadline_info(job["deadline"])
    return ok({
        "id": job["id"],
        "companyName": job["companyName"],
        "companyLogo": _logo_url(request, job["companyLogo"]),
        "jobTitle": job["jobTitle"],
        "recruitStatus": status,
        "location": job["location"],
        "career": job["career"],
        "salary": job["salary"],
        "employmentType": job["employmentType"],
        "deadline": job["deadline"],
        "positionIntro": job["positionIntro"],
        "tasks": job["tasks"],
        "qualifications": job["qualifications"],
        "benefits": job["benefits"],
    })


# ── 검색 ──────────────────────────────────────────────────────

@app.get("/search/popular")
def popular_keywords():
    return ok({"keywords": ["프론트엔드", "백엔드", "데이터 분석", "PM", "디자이너"]})


# ── AI 모의 면접 ──────────────────────────────────────────────

@app.get("/interview/questions")
def interview_questions(
    request: Request,
    jobRole: str = Query(...),
    career: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    user=Depends(get_user),
):
    questions = INTERVIEW_QUESTIONS.get(jobRole.upper(), INTERVIEW_QUESTIONS["FRONTEND"])
    result = [
        {**q, "audioUrl": str(request.base_url) + f"interview/{q['audioUrl'].split('/')[-1]}"}
        for q in questions
    ]
    return ok({"jobRole": jobRole, "total": len(result), "questions": result})
