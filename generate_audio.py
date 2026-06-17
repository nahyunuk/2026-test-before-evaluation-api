from gtts import gTTS
import os

questions = {
    "fe_q1": "자기소개를 부탁드립니다.",
    "fe_q2": "React의 Virtual DOM에 대해 설명해주세요.",
    "fe_q3": "상태 관리 라이브러리를 사용해 본 경험이 있으신가요?",
    "fe_q4": "크로스 브라우저 호환성 이슈를 해결한 경험을 말씀해주세요.",
    "fe_q5": "웹 성능 최적화 방법에 대해 아는 것을 말씀해주세요.",
    "be_q1": "자기소개를 부탁드립니다.",
    "be_q2": "RESTful API 설계 원칙에 대해 설명해주세요.",
    "be_q3": "데이터베이스 인덱스에 대해 설명해주세요.",
    "be_q4": "동시성 처리 방법에 대해 아는 것을 말씀해주세요.",
    "be_q5": "마이크로서비스 아키텍처의 장단점을 설명해주세요.",
    "data_q1": "자기소개를 부탁드립니다.",
    "data_q2": "데이터 분석 프로세스에 대해 설명해주세요.",
    "data_q3": "사용해본 데이터 시각화 도구를 말씀해주세요.",
    "data_q4": "SQL 쿼리 최적화 경험이 있으신가요?",
    "data_q5": "머신러닝 모델을 활용한 프로젝트 경험을 말씀해주세요.",
    "pm_q1": "자기소개를 부탁드립니다.",
    "pm_q2": "제품 로드맵을 어떻게 수립하시나요?",
    "pm_q3": "개발팀과 협업할 때 어려웠던 점을 말씀해주세요.",
    "pm_q4": "지표를 기반으로 의사결정을 한 경험을 설명해주세요.",
    "pm_q5": "본인이 성장시킨 서비스의 성과 지표를 공유해주세요.",
    "ds_q1": "자기소개를 부탁드립니다.",
    "ds_q2": "UX 리서치 방법론에 대해 설명해주세요.",
    "ds_q3": "디자인 시스템을 구축한 경험이 있으신가요?",
    "ds_q4": "개발자와 소통할 때 사용하는 방법을 말씀해주세요.",
    "ds_q5": "사용자 피드백을 디자인에 반영한 사례를 공유해주세요.",
}

out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "interview")
os.makedirs(out_dir, exist_ok=True)

for filename, text in questions.items():
    path = os.path.join(out_dir, f"{filename}.mp3")
    tts = gTTS(text=text, lang="ko")
    tts.save(path)
    print(f"created {filename}.mp3")

print(f"\ntotal: {len(questions)} files")
