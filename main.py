from fastapi import FastAPI, Header, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Any, List
import re
import secrets
import time
import subprocess
import socket
from datetime import date, datetime, timezone, timedelta
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
app.mount("/interview-audio", StaticFiles(directory=os.path.join(BASE_DIR, "interview")), name="interview")

# ── In-memory stores ──────────────────────────────────────────
users_db: dict = {}
email_index: dict = {}
tokens_db: dict = {}
phone_codes: dict = {}
_next_id = 2

# 테스트용 기본 유저
users_db[1] = {"id": 1, "email": "test@example.com", "name": "홍길동", "phone": "01000000000", "password": "Test1234!", "intro": "성장하는 개발자입니다"}
email_index["test@example.com"] = 1
tokens_db["test_token"] = 1

# 이력서 데이터
resumes_db: dict = {}  # {user_id: {resume_id: data}}
_next_resume_id = 1

# 북마크/면접 카운트 (다른 모듈에서 관리되는 값 반영)
bookmarks_count: dict = {1: 5}
interviews_count: dict = {1: 3}

# ── Mock 공고 데이터 ──────────────────────────────────────────
MOCK_JOBS = [
    {
        "id": 1,
        "companyName": "카카오",
        "companyLogo": "kakao.png",
        "jobTitle": "프론트엔드 개발자",
        "location": "경기 성남시",
        "employmentType": "정규직",
        "career": "경력 3년↑",
        "salary": "4,000~6,000만원",
        "deadline": "2026-07-31",
        "viewCount": 1200,
        "createdAt": "2026-06-10T09:00:00+09:00",
        "category": "DEV",
        "positionIntro": "카카오는 국민 메신저를 중심으로 다양한 라이프스타일 서비스를 운영하며, 수천만 사용자의 일상을 더 편리하게 만들어가고 있습니다.\n\n프론트엔드 개발자 포지션에서 함께 성장할 인재를 모집합니다. 우리는 사용자 경험에 깊이 공감하고, 아름답고 빠른 인터페이스를 만드는 것에 열정을 가진 분을 찾고 있습니다.",
        "tasks": ["웹 서비스 UI 개발", "사내 디자인 시스템 구축"],
        "qualifications": ["React 3년 이상 경험", "REST API 연동 경험"],
        "benefits": ["유연근무", "식대 지원", "교육비 지원"],
    },
    {
        "id": 2,
        "companyName": "네이버",
        "companyLogo": "naver.png",
        "jobTitle": "백엔드 개발자",
        "location": "경기 성남시",
        "employmentType": "정규직",
        "career": "경력 2년↑",
        "salary": "4,500~7,000만원",
        "deadline": "2026-07-15",
        "viewCount": 980,
        "createdAt": "2026-06-08T10:00:00+09:00",
        "category": "DEV",
        "positionIntro": "네이버는 검색, 커머스, 콘텐츠를 아우르는 글로벌 IT 기업으로, 기술 혁신을 통해 더 나은 사용자 경험을 만들어가고 있습니다.\n\n백엔드 개발자 포지션에서 함께 성장할 인재를 모집합니다. 우리는 대용량 트래픽 환경에서 안정적인 시스템을 설계하고, 기술적 난제를 해결하는 것을 즐기는 분을 찾고 있습니다.",
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
        "positionIntro": "토스는 금융 서비스의 경계를 허물고, 누구나 쉽고 빠르게 금융을 경험할 수 있는 플랫폼을 만들어가고 있습니다.\n\n그로스 마케터 포지션에서 함께 성장할 인재를 모집합니다. 우리는 데이터를 기반으로 가설을 세우고, 실험을 통해 서비스 성장을 이끌어가는 것을 즐기는 분을 찾고 있습니다.",
        "tasks": ["퍼널 분석 및 전환율 최적화", "A/B 테스트 설계 및 성과 분석"],
        "qualifications": ["그로스 해킹 경험 2년 이상", "SQL/데이터 분석 능숙"],
        "benefits": ["자율 출퇴근", "무제한 휴가", "최신 장비 지원"],
    },
    {
        "id": 4,
        "companyName": "무신사",
        "companyLogo": "musinsa.png",
        "jobTitle": "UX 디자이너",
        "location": "서울 성동구",
        "employmentType": "정규직",
        "career": "경력 1년↑",
        "salary": "3,500~5,000만원",
        "deadline": "2026-07-10",
        "viewCount": 620,
        "createdAt": "2026-06-11T09:00:00+09:00",
        "category": "DESIGN",
        "positionIntro": "무신사는 국내 최대 패션 커머스 플랫폼으로, 브랜드와 소비자를 연결하며 패션 문화를 이끌어가고 있습니다.\n\nUX 디자이너 포지션에서 함께 성장할 인재를 모집합니다. 우리는 사용자의 쇼핑 경험에 깊이 공감하고, 직관적이고 매력적인 인터페이스를 설계하는 것을 즐기는 분을 찾고 있습니다.",
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
        "positionIntro": "쿠팡은 로켓배송으로 대표되는 혁신적인 커머스 서비스를 운영하며, 고객의 쇼핑 경험을 새롭게 정의해가고 있습니다.\n\n퍼포먼스 마케터 포지션에서 함께 성장할 인재를 모집합니다. 우리는 데이터와 광고 운영 경험을 바탕으로 효율적인 성과를 만들고, 더 많은 고객과 연결되는 것을 즐기는 분을 찾고 있습니다.",
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
        "positionIntro": "당근마켓은 동네 이웃과 연결되는 커뮤니티 플랫폼으로, 지역 기반 생활 서비스를 통해 따뜻한 동네를 만들어가고 있습니다.\n\niOS 개발자 포지션에서 함께 성장할 인재를 모집합니다. 우리는 수백만 사용자가 매일 사용하는 앱을 더 빠르고 안정적으로 만들고, 새로운 기능에 도전하는 것을 즐기는 분을 찾고 있습니다.",
        "tasks": ["iOS 앱 신규 기능 개발", "앱 성능 최적화"],
        "qualifications": ["Swift 2년 이상 경험", "UIKit/SwiftUI 경험"],
        "benefits": ["자율 출퇴근", "원격 근무", "최신 맥북 지급"],
    },
    {
        "id": 7,
        "companyName": "우아한형제들",
        "companyLogo": "woowa.png",
        "jobTitle": "백엔드 개발자",
        "location": "서울 송파구",
        "employmentType": "정규직",
        "career": "경력 3년↑",
        "salary": "5,000~8,000만원",
        "deadline": "2026-07-20",
        "viewCount": 890,
        "createdAt": "2026-06-07T09:00:00+09:00",
        "category": "DEV",
        "positionIntro": "우아한형제들은 배달의민족 서비스를 통해 외식 문화를 혁신하고, 라이더부터 사장님, 고객까지 연결하는 플랫폼을 만들어가고 있습니다.\n\n백엔드 개발자 포지션에서 함께 성장할 인재를 모집합니다. 우리는 수천만 주문을 안정적으로 처리하는 시스템을 설계하고, MSA 기반의 기술적 도전을 즐기는 분을 찾고 있습니다.",
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
        "positionIntro": "야놀자는 숙박, 레저, 여행을 아우르는 글로벌 여가 플랫폼으로, 더 많은 사람이 여가를 즐길 수 있는 세상을 만들어가고 있습니다.\n\n브랜드 마케터 포지션에서 함께 성장할 인재를 모집합니다. 우리는 브랜드의 이야기를 설득력 있게 전달하고, 고객과 깊이 공감하는 캠페인을 만드는 것을 즐기는 분을 찾고 있습니다.",
        "tasks": ["브랜드 캠페인 기획 및 운영", "SNS 채널 마케팅"],
        "qualifications": ["브랜드 마케팅 경험 2년 이상", "콘텐츠 기획 능력"],
        "benefits": ["숙박 할인", "유연근무", "의료비 지원"],
    },
    {
        "id": 9,
        "companyName": "직방",
        "companyLogo": "zigbang.png",
        "jobTitle": "프론트엔드 개발자",
        "location": "서울 강남구",
        "employmentType": "정규직",
        "career": "경력 1년↑",
        "salary": "3,500~5,500만원",
        "deadline": "2026-08-01",
        "viewCount": 510,
        "createdAt": "2026-06-13T10:00:00+09:00",
        "category": "DEV",
        "positionIntro": "직방은 부동산 정보의 투명성을 높이고, 누구나 쉽게 집을 구할 수 있는 부동산 플랫폼을 만들어가고 있습니다.\n\n프론트엔드 개발자 포지션에서 함께 성장할 인재를 모집합니다. 우리는 복잡한 부동산 데이터를 직관적인 UI로 표현하고, 사용자가 원하는 집을 더 빠르게 찾을 수 있도록 돕는 것을 즐기는 분을 찾고 있습니다.",
        "tasks": ["React 기반 웹 서비스 개발", "지도 연동 UI 구현"],
        "qualifications": ["React/TypeScript 경험", "지도 API 연동 경험 우대"],
        "benefits": ["유연근무", "식대 지원", "자기계발비"],
    },
    {
        "id": 10,
        "companyName": "라인",
        "companyLogo": "line.png",
        "jobTitle": "서비스 개발자",
        "location": "서울 강남구",
        "employmentType": "정규직",
        "career": "경력 3년↑",
        "salary": "5,500~9,000만원",
        "deadline": "2026-06-22",
        "viewCount": 1050,
        "createdAt": "2026-06-06T09:00:00+09:00",
        "category": "DEV",
        "positionIntro": "라인은 전 세계 수억 명이 사용하는 글로벌 메신저 플랫폼으로, 소통의 경계를 넘어 다양한 서비스로 사람들을 연결하고 있습니다.\n\n서비스 개발자 포지션에서 함께 성장할 인재를 모집합니다. 우리는 글로벌 사용자를 위한 안정적인 서비스를 개발하고, 다국어·다지역 환경에서의 기술적 도전을 즐기는 분을 찾고 있습니다.",
        "tasks": ["글로벌 메신저 기능 개발", "다국어/다지역 서비스 최적화"],
        "qualifications": ["Java 또는 Go 경험", "영어 커뮤니케이션 가능"],
        "benefits": ["글로벌 오피스 파견", "스톡옵션", "어학 지원"],
    },
    {
        "id": 11,
        "companyName": "AWS코리아",
        "companyLogo": "aws.png",
        "jobTitle": "솔루션 아키텍트",
        "location": "서울 강남구",
        "employmentType": "정규직",
        "career": "경력 5년↑",
        "salary": "8,000~15,000만원",
        "deadline": "2026-07-05",
        "viewCount": 1680,
        "createdAt": "2026-06-03T09:00:00+09:00",
        "category": "DEV",
        "positionIntro": "AWS 코리아는 클라우드 인프라를 통해 국내 기업들의 디지털 혁신을 지원하며, 기술로 비즈니스의 가능성을 넓혀가고 있습니다.\n\n솔루션 아키텍트 포지션에서 함께 성장할 인재를 모집합니다. 우리는 고객사의 비즈니스를 깊이 이해하고, 최적의 클라우드 아키텍처를 설계하여 실질적인 가치를 만드는 것을 즐기는 분을 찾고 있습니다.",
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
        "positionIntro": "원티드는 채용의 패러다임을 바꾸는 HR 테크 플랫폼으로, 기술과 데이터를 활용해 인재와 기업의 최적 매칭을 만들어가고 있습니다.\n\n콘텐츠 마케터 포지션에서 함께 성장할 인재를 모집합니다. 우리는 채용 트렌드와 커리어 인사이트를 진정성 있는 콘텐츠로 전달하고, 사람들의 커리어 성장에 기여하는 것을 즐기는 분을 찾고 있습니다.",
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
        "positionIntro": "프로토파이는 전 세계 디자이너들이 사용하는 고급 프로토타이핑 툴을 만들며, 디자인과 기술의 경계를 허물고 있습니다.\n\nUX 디자이너 포지션에서 함께 성장할 인재를 모집합니다. 우리는 글로벌 사용자를 깊이 이해하고, 직관적이고 강력한 사용자 경험을 설계하는 것을 즐기는 분을 찾고 있습니다.",
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
        "positionIntro": "스트림랩스는 스트리밍 크리에이터를 위한 다양한 솔루션을 개발하며, AI 기술을 접목해 콘텐츠 제작의 미래를 만들어가고 있습니다.\n\nAI 엔지니어 포지션에서 함께 성장할 인재를 모집합니다. 우리는 머신러닝 모델을 실제 서비스에 적용하고, 데이터 기반으로 추천 시스템을 고도화하는 도전을 즐기는 분을 찾고 있습니다.",
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
        "positionIntro": "플로우테크는 빠르게 성장하는 B2B SaaS 스타트업으로, 기업의 업무 효율을 높이는 솔루션을 개발하며 시장을 만들어가고 있습니다.\n\n풀스택 개발자 포지션에서 함께 성장할 인재를 모집합니다. 우리는 프론트엔드부터 백엔드, 인프라까지 폭넓게 기여하고, 오너십을 가지고 일하는 것을 즐기는 분을 찾고 있습니다.",
        "tasks": ["프론트/백엔드 기능 개발", "인프라 관리"],
        "qualifications": ["React + Node.js 또는 Python 경험", "AWS 기본 지식"],
        "benefits": ["스톡옵션", "자율 출퇴근", "성장 지원금"],
    },
    {
        "id": 16,
        "companyName": "카카오",
        "companyLogo": "kakao.png",
        "jobTitle": "HR 파트너",
        "location": "경기 성남시",
        "employmentType": "정규직",
        "career": "경력 3년↑",
        "salary": "4,500~7,000만원",
        "deadline": "2026-07-20",
        "viewCount": 540,
        "createdAt": "2026-06-11T09:00:00+09:00",
        "category": "HR",
        "positionIntro": "카카오는 국민 메신저를 중심으로 다양한 라이프스타일 서비스를 운영하며, 수천만 사용자의 일상을 더 편리하게 만들어가고 있습니다.\n\nHR 파트너 포지션에서 함께 성장할 인재를 모집합니다. 우리는 조직의 성장 과제를 비즈니스 관점에서 함께 고민하고, 사람 중심의 문화를 만들어가는 것을 즐기는 분을 찾고 있습니다.",
        "tasks": ["사업부 HR 파트너링", "채용 기획 및 운영", "조직문화 프로그램 설계"],
        "qualifications": ["HR 실무 경험 3년 이상", "채용/조직개발 경험 보유"],
        "benefits": ["유연근무", "식대 지원", "교육비 지원"],
    },
    {
        "id": 17,
        "companyName": "네이버",
        "companyLogo": "naver.png",
        "jobTitle": "채용 담당자",
        "location": "경기 성남시",
        "employmentType": "정규직",
        "career": "경력 2년↑",
        "salary": "4,000~6,000만원",
        "deadline": "2026-08-05",
        "viewCount": 380,
        "createdAt": "2026-06-12T10:00:00+09:00",
        "category": "HR",
        "positionIntro": "네이버는 검색, 커머스, 콘텐츠를 아우르는 글로벌 IT 기업으로, 기술 혁신을 통해 더 나은 사용자 경험을 만들어가고 있습니다.\n\n채용 담당자 포지션에서 함께 성장할 인재를 모집합니다. 우리는 우수한 기술 인재를 발굴하고, 데이터 기반으로 채용 프로세스를 고도화하는 것을 즐기는 분을 찾고 있습니다.",
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
        "positionIntro": "원티드는 채용의 패러다임을 바꾸는 HR 테크 플랫폼으로, 기술과 데이터를 활용해 인재와 기업의 최적 매칭을 만들어가고 있습니다.\n\nHR 컨설턴트 포지션에서 함께 성장할 인재를 모집합니다. 우리는 기업 고객의 채용 고민을 함께 해결하고, 최적의 인재를 연결하는 과정에서 보람을 느끼는 분을 찾고 있습니다.",
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
    "APP": [
        {"questionNumber": 1, "questionText": "자기소개를 부탁드립니다.", "audioUrl": "https://cdn.hireup.com/interview/app_q1.mp3", "duration": 8},
        {"questionNumber": 2, "questionText": "iOS와 Android 개발의 차이점에 대해 설명해주세요.", "audioUrl": "https://cdn.hireup.com/interview/app_q2.mp3", "duration": 10},
        {"questionNumber": 3, "questionText": "앱 성능 최적화를 위해 사용한 방법을 말씀해주세요.", "audioUrl": "https://cdn.hireup.com/interview/app_q3.mp3", "duration": 10},
        {"questionNumber": 4, "questionText": "앱 배포 경험과 스토어 심사 과정에 대해 설명해주세요.", "audioUrl": "https://cdn.hireup.com/interview/app_q4.mp3", "duration": 12},
        {"questionNumber": 5, "questionText": "네이티브 앱과 크로스플랫폼 앱의 장단점을 설명해주세요.", "audioUrl": "https://cdn.hireup.com/interview/app_q5.mp3", "duration": 12},
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
    adbHost: Optional[str] = None


class PhoneVerifyBody(BaseModel):
    phone: Optional[str] = None
    code: Optional[str] = None


class SignupBody(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None


class ResumeBody(BaseModel):
    title: Optional[str] = None
    jobRole: Optional[str] = None
    oneLineIntro: Optional[str] = None
    intro: Optional[str] = None
    educations: Optional[List[Any]] = None
    careers: Optional[List[Any]] = None
    projects: Optional[List[Any]] = None
    skills: Optional[List[str]] = None


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

    code = str(secrets.randbelow(900000) + 100000)
    phone_codes[phone] = {"code": code, "expires_at": time.time() + 180}
    message = f"[Web] 인증번호 [{code}]입니다."

    def send_sms_via_console(host: str, port: int, phone: str, message: str):
        token_path = os.path.expanduser("~/.emulator_console_auth_token")
        token = ""
        if os.path.exists(token_path):
            with open(token_path, "r") as f:
                token = f.read().strip()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((host, port))
            time.sleep(0.5)
            buf = b""
            while True:
                try:
                    chunk = s.recv(4096)
                    buf += chunk
                    if b"OK" in chunk:
                        break
                except socket.timeout:
                    break
            if token:
                s.sendall(f"auth {token}\n".encode("utf-8"))
                time.sleep(0.3)
                s.recv(1024)
            s.sendall(f"sms send {phone} {message}\n".encode("utf-8"))
            time.sleep(0.3)
            s.recv(1024)

    try:
        send_sms_via_console("127.0.0.1", 5554, phone, message)
    except Exception:
        pass

    return ok({"expiresIn": 180}, "인증번호가 발송되었습니다.")


@app.post("/auth/phone/verify")
def phone_verify(body: PhoneVerifyBody):
    phone = body.phone or ""
    code = body.code or ""

    if not phone:
        return fail("인증 실패", [{"code": "REQUIRED", "field": "phone", "message": "휴대폰 번호를 입력해주세요."}], 400)
    if not code:
        return fail("인증 실패", [{"code": "REQUIRED", "field": "code", "message": "인증번호를 입력해주세요."}], 400)

    entry = phone_codes.get(phone)
    if not entry:
        return fail("인증 실패", [{"code": "NOT_FOUND", "field": "phone", "message": "인증번호를 먼저 요청해주세요."}], 400)
    if time.time() > entry["expires_at"]:
        return fail("인증 실패", [{"code": "EXPIRED", "field": "code", "message": "인증번호가 만료되었습니다. 다시 요청해주세요."}], 400)
    if entry["code"] != code:
        return fail("인증 실패", [{"code": "INVALID_CODE", "field": "code", "message": "인증번호가 일치하지 않습니다."}], 400)

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
        {**q, "audioUrl": str(request.base_url) + f"interview-audio/{q['audioUrl'].split('/')[-1]}"}
        for q in questions
    ]
    return ok({"jobRole": jobRole, "total": len(result), "questions": result})


# ── 프로필 ────────────────────────────────────────────────────

@app.get("/profile")
def get_profile(user=Depends(get_user)):
    if not user:
        return fail("인증이 필요합니다.", [{"code": "UNAUTHORIZED", "message": "로그인이 필요합니다."}], 401)

    uid = user["id"]
    return ok({
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "intro": user.get("intro", ""),
        },
        "stats": {
            "bookmarkCount": bookmarks_count.get(uid, 0),
            "interviewCount": interviews_count.get(uid, 0),
            "resumeCount": len(resumes_db.get(uid, {})),
        },
    })


# ── 이력서 ────────────────────────────────────────────────────

@app.get("/resumes")
def list_resumes(user=Depends(get_user)):
    if not user:
        return fail("인증이 필요합니다.", [{"code": "UNAUTHORIZED", "message": "로그인이 필요합니다."}], 401)

    uid = user["id"]
    items = [
        {
            "id": r["id"],
            "title": r.get("title", ""),
            "updatedAt": r.get("updatedAt", ""),
            "skills": r.get("skills", []),
        }
        for r in resumes_db.get(uid, {}).values()
    ]
    return ok({"items": items})


@app.put("/resumes")
def save_resume(
    body: ResumeBody,
    id: Optional[int] = Query(None),
    user=Depends(get_user),
):
    global _next_resume_id

    if not user:
        return fail("인증이 필요합니다.", [{"code": "UNAUTHORIZED", "message": "로그인이 필요합니다."}], 401)

    errors = []

    if body.oneLineIntro and len(body.oneLineIntro) > 50:
        errors.append({"code": "INVALID_LENGTH", "field": "oneLineIntro", "message": "한 줄 소개는 50자 이내로 입력해주세요."})

    if body.intro and len(body.intro) > 300:
        errors.append({"code": "INVALID_LENGTH", "field": "intro", "message": "소개는 300자 이내로 입력해주세요."})

    educations = body.educations or []
    for edu in educations:
        if not (edu.get("schoolName") if isinstance(edu, dict) else None):
            errors.append({"code": "REQUIRED", "field": "educations.schoolName", "message": "학교명을 입력해주세요."})
            break

    careers = body.careers or []
    for career in careers:
        if not (career.get("companyName") if isinstance(career, dict) else None):
            errors.append({"code": "REQUIRED", "field": "careers.companyName", "message": "회사명을 입력해주세요."})
            break

    projects = body.projects or []
    for proj in projects:
        if not (proj.get("name") if isinstance(proj, dict) else None):
            errors.append({"code": "REQUIRED", "field": "projects.name", "message": "프로젝트명을 입력해주세요."})
            break

    skills = body.skills or []
    if len(skills) != len(set(skills)):
        errors.append({"code": "DUPLICATE", "field": "skills", "message": "이미 추가된 기술입니다."})

    if errors:
        return fail("이력서 저장 실패", errors, 400)

    uid = user["id"]
    if uid not in resumes_db:
        resumes_db[uid] = {}

    now = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%dT%H:%M:%S+09:00")

    resume_data = {
        "title": body.title,
        "jobRole": body.jobRole,
        "oneLineIntro": body.oneLineIntro,
        "intro": body.intro,
        "educations": educations,
        "careers": careers,
        "projects": projects,
        "skills": skills,
        "updatedAt": now,
    }

    if id is not None:
        if id not in resumes_db[uid]:
            return fail(
                "이력서를 찾을 수 없습니다.",
                [{"code": "NOT_FOUND", "field": "id", "message": "존재하지 않는 이력서입니다."}],
                404,
            )
        resumes_db[uid][id] = {**resume_data, "id": id}
        return ok({"id": id}, "이력서가 저장되었습니다.")

    new_id = _next_resume_id
    _next_resume_id += 1
    resumes_db[uid][new_id] = {**resume_data, "id": new_id}
    return JSONResponse(
        {"success": True, "message": "이력서가 저장되었습니다.", "data": {"id": new_id}},
        status_code=201,
    )
