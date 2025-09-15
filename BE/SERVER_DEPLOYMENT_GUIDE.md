# 서버 배포 가이드

## 수정된 파일들

### 1. main_pipeline.py

- ✅ 상대 import → 절대 import 변경 완료
- ✅ subprocess.run cwd 설정 수정 완료
- ⚠️ 서버 배포 시 되돌려야 할 부분들:

```python
# 현재 (로컬 개발용)
load_dotenv('.env')
data_directory = os.getenv('DATA_DIRECTORY', "example_data")
cwd="."

# 서버 배포용으로 변경 필요
load_dotenv('../.env')
data_directory = os.getenv('DATA_DIRECTORY', "BE/example_data")
cwd="BE"
```

### 2. run_questions_v3_with_concept.py

- ✅ 상대 import → 절대 import 변경 완료
- ✅ Python 경로 설정 추가 완료
- ⚠️ 서버 배포 시 실행 방법:

```bash
# 현재 (로컬)
cd BE/experiment
python run_questions_v3_with_concept.py

# 서버 배포용 (두 가지 방법)
# 방법 1: 직접 실행
python BE/experiment/run_questions_v3_with_concept.py

# 방법 2: 모듈로 실행
python -m BE.experiment.run_questions_v3_with_concept
```

## 환경변수 설정

### .env 파일 (서버용)

```env
# OpenRouter API 설정
OPENAI_API_KEY=sk-or-v1-~~~
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL_NAME=openai/gpt-oss-120b:free

# Neo4j 설정
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j

# 데이터 디렉토리 (서버용)
DATA_DIRECTORY=BE/example_data
```

## 서버 배포 체크리스트

- [ ] main_pipeline.py의 cwd 설정을 "BE"로 변경
- [ ] main_pipeline.py의 .env 경로를 "../.env"로 변경
- [ ] main_pipeline.py의 DATA_DIRECTORY 기본값을 "BE/example_data"로 변경
- [ ] .env 파일을 프로젝트 루트에 배치
- [ ] Neo4j 데이터베이스 실행 확인
- [ ] OpenRouter API 키 설정 확인
- [ ] 필요한 Python 패키지 설치 확인

## 실행 방법

```bash
# 파이프라인 실행
python BE/main_pipeline.py contract_v5

# 채팅 시스템 실행
python -m BE.experiment.run_questions_v3_with_concept
```
