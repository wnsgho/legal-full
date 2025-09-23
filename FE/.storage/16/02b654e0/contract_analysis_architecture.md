# 계약서 분석 AI 서비스 시스템 아키텍처

## Implementation approach

이 계약서 분석 AI 서비스는 React + TypeScript 기반의 프론트엔드와 Node.js/Python 기반의 마이크로서비스 아키텍처로 구현됩니다. 주요 기술적 도전과제는 대용량 문서 처리, 실시간 AI 분석, 그리고 보안입니다.

**핵심 기술 스택:**
- Frontend: React 18, TypeScript, Shadcn-ui, Tailwind CSS, Zustand (상태관리)
- Backend: Node.js (Express), Python (FastAPI for AI services)
- Database: PostgreSQL (메인), Redis (캐싱/세션)
- File Storage: AWS S3 또는 MinIO
- AI Integration: OpenAI GPT-4, Anthropic Claude, Custom NLP models
- Infrastructure: Docker, Kubernetes, NGINX
- Security: JWT, bcrypt, AES-256 encryption

**선택 이유:**
- React + TypeScript: 타입 안전성과 개발자 경험 최적화
- 마이크로서비스: AI 분석 서비스의 독립적 확장 가능
- PostgreSQL: 복잡한 관계형 데이터와 JSON 지원
- Redis: 실시간 분석 상태 추적과 세션 관리
- Python FastAPI: AI/ML 라이브러리 생태계 활용

## Data structures and interfaces

### 프론트엔드 컴포넌트 구조

```typescript
// Core Types
interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  subscription: SubscriptionPlan;
  createdAt: Date;
}

interface Contract {
  id: string;
  userId: string;
  fileName: string;
  fileSize: number;
  fileType: string;
  uploadedAt: Date;
  status: ContractStatus;
  s3Key: string;
  ocrText?: string;
}

interface AnalysisResult {
  id: string;
  contractId: string;
  status: AnalysisStatus;
  riskLevel: RiskLevel;
  riskClauses: RiskClause[];
  summary: string;
  recommendations: string[];
  aiModel: string;
  confidence: number;
  createdAt: Date;
}

interface RiskClause {
  id: string;
  text: string;
  riskLevel: RiskLevel;
  category: ClauseCategory;
  position: TextPosition;
  explanation: string;
  recommendation: string;
}

// Enums
enum UserRole {
  USER = 'user',
  ADMIN = 'admin',
  ENTERPRISE = 'enterprise'
}

enum ContractStatus {
  UPLOADING = 'uploading',
  UPLOADED = 'uploaded',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

enum AnalysisStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

enum RiskLevel {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}
```

### 백엔드 API 설계

```typescript
// Authentication Service
class AuthService {
  async register(userData: RegisterRequest): Promise<AuthResponse>
  async login(credentials: LoginRequest): Promise<AuthResponse>
  async refreshToken(token: string): Promise<AuthResponse>
  async logout(userId: string): Promise<void>
  async resetPassword(email: string): Promise<void>
}

// Contract Service
class ContractService {
  async uploadContract(file: File, userId: string): Promise<Contract>
  async getContracts(userId: string, pagination: Pagination): Promise<Contract[]>
  async getContract(contractId: string, userId: string): Promise<Contract>
  async deleteContract(contractId: string, userId: string): Promise<void>
  async downloadContract(contractId: string, userId: string): Promise<Buffer>
}

// Analysis Service
class AnalysisService {
  async startAnalysis(contractId: string, params: AnalysisParams): Promise<AnalysisResult>
  async getAnalysisResult(analysisId: string): Promise<AnalysisResult>
  async getAnalysisHistory(userId: string): Promise<AnalysisResult[]>
  async compareAnalyses(analysisId1: string, analysisId2: string): Promise<ComparisonResult>
  async retryAnalysis(analysisId: string): Promise<AnalysisResult>
}

// AI Chat Service
class ChatService {
  async sendMessage(contractId: string, message: string, userId: string): Promise<ChatResponse>
  async getChatHistory(contractId: string, userId: string): Promise<ChatMessage[]>
  async clearChatHistory(contractId: string, userId: string): Promise<void>
}

// OCR Service
class OCRService {
  async extractText(fileBuffer: Buffer, fileType: string): Promise<OCRResult>
  async validateOCRResult(ocrResult: OCRResult): Promise<ValidationResult>
}

// File Storage Service
class FileStorageService {
  async uploadFile(file: Buffer, key: string): Promise<string>
  async downloadFile(key: string): Promise<Buffer>
  async deleteFile(key: string): Promise<void>
  async generateSignedUrl(key: string, expiry: number): Promise<string>
}
```

### 데이터베이스 스키마

```sql
-- Users Table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  name VARCHAR(255) NOT NULL,
  role user_role DEFAULT 'user',
  subscription_plan subscription_plan DEFAULT 'free',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  last_login TIMESTAMP,
  is_active BOOLEAN DEFAULT true
);

-- Contracts Table
CREATE TABLE contracts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  file_name VARCHAR(255) NOT NULL,
  file_size BIGINT NOT NULL,
  file_type VARCHAR(50) NOT NULL,
  s3_key VARCHAR(500) NOT NULL,
  status contract_status DEFAULT 'uploaded',
  ocr_text TEXT,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Analysis Results Table
CREATE TABLE analysis_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_id UUID REFERENCES contracts(id) ON DELETE CASCADE,
  status analysis_status DEFAULT 'pending',
  risk_level risk_level,
  summary TEXT,
  recommendations TEXT[],
  ai_model VARCHAR(100),
  confidence DECIMAL(3,2),
  processing_time_ms INTEGER,
  created_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP
);

-- Risk Clauses Table
CREATE TABLE risk_clauses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id UUID REFERENCES analysis_results(id) ON DELETE CASCADE,
  clause_text TEXT NOT NULL,
  risk_level risk_level NOT NULL,
  category clause_category NOT NULL,
  start_position INTEGER,
  end_position INTEGER,
  explanation TEXT,
  recommendation TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Chat Messages Table
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_id UUID REFERENCES contracts(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  message TEXT NOT NULL,
  response TEXT,
  is_user_message BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Analysis Comparisons Table
CREATE TABLE analysis_comparisons (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  analysis_id_1 UUID REFERENCES analysis_results(id),
  analysis_id_2 UUID REFERENCES analysis_results(id),
  comparison_result JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

-- User Sessions Table (Redis Alternative)
CREATE TABLE user_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  session_token VARCHAR(500) NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

## Program call flow

### 계약서 업로드 및 분석 플로우

```
participant U as User
participant F as Frontend
participant A as Auth Service
participant C as Contract Service
participant O as OCR Service
participant AI as AI Analysis Service
participant S as File Storage
participant DB as Database
participant R as Redis

U->>F: 파일 드래그 앤 드롭
F->>F: 파일 유효성 검사
F->>A: JWT 토큰 검증
A->>DB: 사용자 세션 확인
DB-->>A: 세션 유효성 응답
A-->>F: 인증 성공

F->>C: uploadContract(file, userId)
C->>S: uploadFile(fileBuffer, s3Key)
S-->>C: 업로드 완료 URL
C->>DB: INSERT INTO contracts
DB-->>C: contract 생성 완료
C-->>F: Contract 객체 반환

F->>U: 업로드 완료 알림
U->>F: 분석 시작 버튼 클릭
F->>C: startAnalysis(contractId, params)
C->>DB: INSERT INTO analysis_results (status: pending)

alt 이미지 파일인 경우
  C->>O: extractText(fileBuffer, fileType)
  O->>O: OCR 처리 (Tesseract/AWS Textract)
  O-->>C: OCR 결과 반환
  C->>DB: UPDATE contracts SET ocr_text
end

C->>AI: analyzeContract(contractText, params)
C->>R: SET analysis:status:{id} "in_progress"
C-->>F: 분석 시작 응답

AI->>AI: GPT-4/Claude API 호출
AI->>AI: 위험 조항 식별
AI->>AI: 리스크 레벨 계산
AI->>AI: 권장사항 생성

AI-->>C: 분석 결과 반환
C->>DB: UPDATE analysis_results
C->>DB: INSERT INTO risk_clauses (bulk)
C->>R: SET analysis:status:{id} "completed"
C->>F: WebSocket으로 완료 알림

F->>F: 분석 결과 UI 업데이트
F->>U: 분석 완료 알림
```

### AI 채팅 인터페이스 플로우

```
participant U as User
participant F as Frontend
participant CH as Chat Service
participant AI as AI Service
participant DB as Database
participant R as Redis

U->>F: 채팅 메시지 입력
F->>CH: sendMessage(contractId, message, userId)
CH->>DB: SELECT contract, analysis_result
CH->>DB: INSERT INTO chat_messages (user message)

CH->>R: GET chat:context:{contractId}
R-->>CH: 이전 대화 컨텍스트
CH->>AI: generateResponse(message, context, contractData)
AI->>AI: GPT-4 API 호출 (계약서 컨텍스트 포함)
AI-->>CH: AI 응답 반환

CH->>DB: UPDATE chat_messages SET response
CH->>R: SET chat:context:{contractId} (업데이트된 컨텍스트)
CH-->>F: ChatResponse 반환
F->>U: AI 응답 표시
```

### 계약서 비교 분석 플로우

```
participant U as User
participant F as Frontend
participant A as Analysis Service
participant AI as AI Service
participant DB as Database

U->>F: 비교할 두 분석 선택
F->>A: compareAnalyses(analysisId1, analysisId2)
A->>DB: SELECT analysis_results, risk_clauses (for both)
A->>AI: compareContracts(analysis1, analysis2)

AI->>AI: 조항별 차이점 분석
AI->>AI: 위험도 변화 계산
AI->>AI: 비교 요약 생성

AI-->>A: 비교 결과 반환
A->>DB: INSERT INTO analysis_comparisons
A-->>F: ComparisonResult 반환
F->>U: 비교 결과 시각화 표시
```

## 파일 처리 및 저장 방식

### 파일 업로드 전략
- **청크 업로드**: 대용량 파일을 위한 멀티파트 업로드
- **진행률 추적**: WebSocket을 통한 실시간 업로드 상태
- **파일 검증**: 바이러스 스캔, 파일 형식 검증, 크기 제한

### 저장소 아키텍처
```
AWS S3 / MinIO
├── contracts/
│   ├── {userId}/
│   │   ├── original/
│   │   │   └── {contractId}.{ext}
│   │   ├── processed/
│   │   │   └── {contractId}_ocr.txt
│   │   └── thumbnails/
│   │       └── {contractId}_thumb.jpg
├── exports/
│   └── {userId}/
│       └── {exportId}.pdf
└── temp/
    └── {sessionId}/
        └── {tempFileId}.{ext}
```

### OCR 처리 파이프라인
1. **이미지 전처리**: 해상도 최적화, 노이즈 제거
2. **텍스트 추출**: Tesseract OCR + AWS Textract 하이브리드
3. **후처리**: 맞춤법 검사, 법률 용어 보정
4. **신뢰도 검증**: OCR 결과 품질 평가

## AI 분석 서비스 통합 방안

### AI 모델 아키텍처
```python
class ContractAnalyzer:
    def __init__(self):
        self.primary_model = GPT4Client()
        self.secondary_model = ClaudeClient()
        self.fallback_model = CustomNLPModel()
    
    async def analyze_contract(self, text: str, params: AnalysisParams) -> AnalysisResult:
        # 1차: GPT-4로 기본 분석
        primary_result = await self.primary_model.analyze(text, params)
        
        # 2차: Claude로 교차 검증 (고위험 케이스)
        if primary_result.risk_level >= RiskLevel.HIGH:
            secondary_result = await self.secondary_model.analyze(text, params)
            result = self.merge_results(primary_result, secondary_result)
        else:
            result = primary_result
            
        # 3차: 커스텀 모델로 법률 용어 검증
        result = await self.fallback_model.validate_legal_terms(result)
        
        return result
```

### 프롬프트 엔지니어링
```python
ANALYSIS_PROMPT_TEMPLATE = """
계약서 분석 전문가로서 다음 계약서를 분석해주세요:

{contract_text}

분석 기준:
1. 위험도 평가 (Critical/High/Medium/Low)
2. 비표준 조항 식별
3. 법적 리스크 요소
4. 권장 수정사항

출력 형식:
- JSON 구조로 반환
- 각 조항별 상세 분석
- 신뢰도 점수 포함
"""

CHAT_PROMPT_TEMPLATE = """
계약서 상담 전문가로서 사용자의 질문에 답변해주세요.

계약서 컨텍스트:
{contract_summary}

분석 결과:
{analysis_result}

사용자 질문: {user_question}

답변 시 주의사항:
- 법률 자문이 아닌 정보 제공임을 명시
- 구체적이고 실용적인 조언 제공
- 관련 조항 인용 포함
"""
```

## 보안 및 권한 관리

### 인증/인가 시스템
```typescript
// JWT 기반 인증
interface JWTPayload {
  userId: string;
  email: string;
  role: UserRole;
  permissions: Permission[];
  iat: number;
  exp: number;
}

// 권한 관리
enum Permission {
  READ_OWN_CONTRACTS = 'read_own_contracts',
  WRITE_OWN_CONTRACTS = 'write_own_contracts',
  DELETE_OWN_CONTRACTS = 'delete_own_contracts',
  ADMIN_READ_ALL = 'admin_read_all',
  ADMIN_WRITE_ALL = 'admin_write_all',
  ENTERPRISE_BATCH_UPLOAD = 'enterprise_batch_upload'
}

class AuthorizationService {
  checkPermission(user: User, resource: string, action: string): boolean {
    // RBAC (Role-Based Access Control) 구현
    const requiredPermission = this.getRequiredPermission(resource, action);
    return user.permissions.includes(requiredPermission);
  }
}
```

### 데이터 보안
- **암호화**: AES-256으로 민감한 데이터 암호화
- **전송 보안**: TLS 1.3, HTTPS 강제
- **접근 제어**: IP 화이트리스트, 지역 제한
- **감사 로그**: 모든 데이터 접근 기록

### 개인정보보호
```sql
-- GDPR 준수를 위한 데이터 익명화
CREATE TABLE data_retention_policies (
  id UUID PRIMARY KEY,
  table_name VARCHAR(100),
  retention_days INTEGER,
  anonymization_fields TEXT[],
  created_at TIMESTAMP DEFAULT NOW()
);

-- 데이터 삭제 요청 처리
CREATE TABLE deletion_requests (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  requested_at TIMESTAMP DEFAULT NOW(),
  processed_at TIMESTAMP,
  status deletion_status DEFAULT 'pending'
);
```

## 성능 최적화 방안

### 프론트엔드 최적화
```typescript
// 코드 스플리팅
const AnalysisPage = lazy(() => import('./pages/AnalysisPage'));
const ComparisonPage = lazy(() => import('./pages/ComparisonPage'));

// 메모이제이션
const MemoizedRiskClauseList = memo(RiskClauseList);

// 가상화 (대량 데이터)
const VirtualizedContractList = () => {
  return (
    <FixedSizeList
      height={600}
      itemCount={contracts.length}
      itemSize={80}
    >
      {ContractItem}
    </FixedSizeList>
  );
};

// 상태 관리 최적화 (Zustand)
const useContractStore = create<ContractState>((set, get) => ({
  contracts: [],
  loading: false,
  addContract: (contract) => 
    set((state) => ({ contracts: [...state.contracts, contract] })),
  updateContract: (id, updates) =>
    set((state) => ({
      contracts: state.contracts.map(c => 
        c.id === id ? { ...c, ...updates } : c
      )
    }))
}));
```

### 백엔드 최적화
```typescript
// 데이터베이스 연결 풀링
const pool = new Pool({
  host: process.env.DB_HOST,
  port: parseInt(process.env.DB_PORT),
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  max: 20, // 최대 연결 수
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Redis 캐싱 전략
class CacheService {
  async getAnalysisResult(analysisId: string): Promise<AnalysisResult | null> {
    const cached = await redis.get(`analysis:${analysisId}`);
    if (cached) return JSON.parse(cached);
    
    const result = await db.getAnalysisResult(analysisId);
    if (result) {
      await redis.setex(`analysis:${analysisId}`, 3600, JSON.stringify(result));
    }
    return result;
  }
}

// 비동기 작업 큐 (Bull Queue)
const analysisQueue = new Queue('contract analysis', {
  redis: { port: 6379, host: 'localhost' }
});

analysisQueue.process('analyze-contract', async (job) => {
  const { contractId, userId } = job.data;
  return await performAnalysis(contractId, userId);
});
```

### 인프라 최적화
```yaml
# Docker Compose 설정
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
    
  api-gateway:
    build: ./api-gateway
    ports:
      - "8000:8000"
    depends_on:
      - auth-service
      - contract-service
      
  auth-service:
    build: ./services/auth
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
    
  contract-service:
    build: ./services/contract
    environment:
      - DATABASE_URL=postgresql://...
      - S3_BUCKET=contracts-bucket
    
  ai-service:
    build: ./services/ai
    deploy:
      replicas: 3
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=contract_analysis
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
      
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
```

### 모니터링 및 로깅
```typescript
// 성능 메트릭 수집
class MetricsService {
  async recordAnalysisTime(duration: number, model: string) {
    await prometheus.histogram('analysis_duration_seconds', {
      model,
      buckets: [1, 5, 10, 30, 60, 120]
    }).observe(duration);
  }
  
  async recordAPILatency(endpoint: string, duration: number) {
    await prometheus.histogram('api_request_duration_seconds', {
      endpoint,
      buckets: [0.1, 0.5, 1, 2, 5]
    }).observe(duration);
  }
}

// 구조화된 로깅
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: 'contract-analysis' },
  transports: [
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' }),
    new winston.transports.Console({
      format: winston.format.simple()
    })
  ]
});
```

## Anything UNCLEAR

다음 사항들에 대한 추가 명확화가 필요합니다:

1. **AI 모델 비용 최적화**: GPT-4 vs Claude vs 오픈소스 모델의 비용 대비 성능 기준
2. **실시간 처리 요구사항**: WebSocket vs Server-Sent Events vs Polling 방식 선택
3. **다국어 지원 범위**: 초기 버전에서 지원할 언어와 OCR 정확도 목표
4. **규제 준수 요구사항**: 금융권, 의료계약 등 특수 분야의 추가 보안 요구사항
5. **확장성 목표**: 동시 사용자 수, 일일 처리 계약서 수량 목표
6. **데이터 백업 전략**: RTO/RPO 목표와 재해복구 시나리오
7. **써드파티 통합**: 기존 계약 관리 시스템과의 연동 필요성
8. **모바일 앱 개발**: PWA vs 네이티브 앱 개발 계획

이러한 요소들이 명확해지면 더 구체적인 기술적 구현 방안과 성능 목표를 수립할 수 있습니다.