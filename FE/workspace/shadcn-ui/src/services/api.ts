// 환경 변수에서 API 베이스 URL 가져오기 (Vite는 import.meta.env 사용)
// 개발 환경에서는 항상 상대 경로를 사용하여 Vite 프록시 활용
// 프로덕션 환경에서는 환경변수나 절대 경로 사용

// 개발 환경 확인: Vite는 import.meta.env.MODE === 'development' 또는 import.meta.env.DEV 사용
// 개발 환경에서는 환경변수와 관계없이 항상 상대 경로 사용 (프록시 활용)
const isDevelopment =
  import.meta.env.DEV || import.meta.env.MODE === "development";

// API_BASE_URL 결정 로직:
// 1. 개발 환경: 항상 빈 문자열 (상대 경로) - Vite 프록시 사용
// 2. 프로덕션 환경:
//    - VITE_API_BASE_URL이 빈 문자열이거나 설정되지 않았으면 상대 경로 사용 (nginx 프록시)
//    - VITE_API_BASE_URL이 설정되어 있으면 해당 URL 사용
const envApiBaseUrl = import.meta.env.VITE_API_BASE_URL;
export const API_BASE_URL = isDevelopment
  ? "" // 개발 환경: 항상 빈 문자열 (상대 경로) - 프록시를 통해 백엔드로 전달
  : envApiBaseUrl && envApiBaseUrl.trim() !== ""
  ? envApiBaseUrl // 프로덕션: 환경변수가 설정되어 있으면 사용
  : ""; // 프로덕션: 환경변수가 없거나 빈 문자열이면 상대 경로 사용 (nginx 프록시)

// 디버깅: API_BASE_URL 확인 (개발/프로덕션 모두)
console.log("[API Config] ==========================================");
console.log("[API Config] MODE:", import.meta.env.MODE);
console.log("[API Config] DEV:", import.meta.env.DEV);
console.log(
  "[API Config] API_BASE_URL:",
  API_BASE_URL || "(empty - using relative paths for proxy)"
);
console.log(
  "[API Config] VITE_API_BASE_URL env:",
  import.meta.env.VITE_API_BASE_URL || "(not set)"
);
if (!API_BASE_URL) {
  console.log(
    "[API Config] ✅ Using relative paths - proxy will handle requests"
  );
} else {
  console.log("[API Config] ⚠️ Using absolute URL:", API_BASE_URL);
}
console.log("[API Config] ==========================================");

export interface ChatMessage {
  id: string;
  contractId: string;
  message: string;
  response?: string;
  isUserMessage: boolean;
  createdAt: Date;
}

export interface ChatResponse {
  success: boolean;
  answer: string;
  context_count: number;
  processing_time: number;
  model?: string;
  method?: string;
}

export interface FileInfo {
  file_id: string;
  filename: string;
  file_size: number;
  upload_time: string;
  file_path: string;
}

export interface Contract {
  id: string;
  userId: string;
  fileName: string;
  fileSize: number;
  fileType: string;
  uploadedAt: Date;
  status: string;
  s3Key: string;
}

export interface RiskAnalysisResult {
  analysis_id?: string;
  contract_name?: string;
  created_at?: string;
  analysis_result?: {
    overall_risk_score?: number;
    part_results?: Array<{
      part_title?: string;
      risk_level?: string;
      risk_score?: number;
      risk_clauses?: string[];
      relevant_clauses?: string[];
      recommendations?: string[];
    }>;
    total_analysis_time?: number;
    summary?: {
      total_parts_analyzed?: number;
      high_risk_parts?: number;
      critical_issues?: string[];
    };
  };
}

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;

    // 강제 디버깅: baseUrl이 어떻게 설정되었는지 확인
    console.log("[ApiService] ==========================================");
    console.log("[ApiService] Constructor called");
    console.log("[ApiService] API_BASE_URL:", API_BASE_URL);
    console.log("[ApiService] baseUrl parameter:", baseUrl);
    console.log("[ApiService] this.baseUrl:", this.baseUrl);
    console.log("[ApiService] import.meta.env.DEV:", import.meta.env.DEV);
    console.log("[ApiService] import.meta.env.MODE:", import.meta.env.MODE);
    console.log("[ApiService] ==========================================");

    // 개발 환경인데 localhost로 설정되어 있으면 경고
    if (
      this.baseUrl.includes("localhost") &&
      (import.meta.env.DEV || import.meta.env.MODE === "development")
    ) {
      console.error(
        "[ApiService] ⚠️ WARNING: Development mode but using localhost URL!"
      );
      console.error(
        "[ApiService] This will cause CORS errors. baseUrl should be empty string."
      );
    }
  }

  // 공통 헤더 생성 (ngrok 브라우저 경고 건너뛰기 포함)
  // FormData를 사용하는 경우 contentType을 null로 전달
  private getHeaders(
    contentType: string | null = "application/json"
  ): HeadersInit {
    const headers: HeadersInit = {
      "ngrok-skip-browser-warning": "69420",
    };
    if (contentType) {
      headers["Content-Type"] = contentType;
    }
    return headers;
  }

  // RAG 기반 채팅 메시지 전송
  async sendChatMessage(
    message: string,
    fileId?: string,
    chatMode: "rag" | "openai" = "rag"
  ): Promise<ChatResponse> {
    const url = `${this.baseUrl}/api/chat/`;
    console.log("[ApiService] sendChatMessage - Request URL:", url);
    const response = await fetch(url, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        question: message,
        max_tokens: 8192,
        temperature: 0.5,
        chat_mode: chatMode,
        file_id: fileId,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // RAG 기반 채팅 메시지 전송 (기존 호환성 유지)
  async sendRAGChatMessage(
    message: string,
    fileId?: string
  ): Promise<ChatResponse> {
    return this.sendChatMessage(message, fileId, "rag");
  }

  // OpenAI 기본 채팅 메시지 전송 (기존 호환성 유지)
  async sendOpenAIChatMessage(
    message: string,
    fileId?: string
  ): Promise<ChatResponse> {
    return this.sendChatMessage(message, fileId, "openai");
  }

  // OpenAI 기본 채팅 메시지 전송
  async sendOpenAIBasicMessage(message: string): Promise<ChatResponse> {
    const response = await fetch(`${this.baseUrl}/api/chat/openai-basic`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        question: message,
        max_tokens: 8192,
        temperature: 0.5,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // 특정 계약서를 위한 OpenAI 기본 채팅 메시지 전송
  async sendOpenAIBasicMessageWithFile(
    fileId: string,
    message: string
  ): Promise<ChatResponse> {
    const response = await fetch(
      `${this.baseUrl}/api/chat/openai-basic/${fileId}`,
      {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify({
          question: message,
          max_tokens: 8192,
          temperature: 0.5,
        }),
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // 채팅 기록 삭제
  async clearChatHistory(): Promise<{ success: boolean }> {
    const response = await fetch(`${this.baseUrl}/api/chat/history`, {
      method: "DELETE",
      headers: this.getHeaders(null),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // 파일 목록 조회
  async getFiles(): Promise<{ success: boolean; data: FileInfo[] }> {
    const response = await fetch(`${this.baseUrl}/api/files/`, {
      headers: this.getHeaders(null),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // 파일 내용 조회
  async getFileContent(
    fileId: string
  ): Promise<{ success: boolean; data: { content: string } }> {
    const response = await fetch(
      `${this.baseUrl}/api/files/${fileId}/content`,
      {
        headers: this.getHeaders(null),
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // 시스템 상태 확인
  async getStatus(): Promise<{
    success: boolean;
    data: { status: { rag_system_loaded: boolean; neo4j_connected: boolean } };
  }> {
    const response = await fetch(`${this.baseUrl}/api/status/`, {
      headers: this.getHeaders(null),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // 위험 분석 결과 조회
  async getSavedRiskAnalysis(): Promise<{
    success: boolean;
    data: { results: RiskAnalysisResult[] };
  }> {
    const response = await fetch(`${this.baseUrl}/risk-analysis/saved`, {
      headers: this.getHeaders(null),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // GPT 분석 결과 조회
  async getGptAnalysisResults(): Promise<{
    success: boolean;
    data: { results: RiskAnalysisResult[] };
  }> {
    const response = await fetch(`${this.baseUrl}/risk-analysis/gpt-results`, {
      headers: this.getHeaders(null),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // GPT 전용 분석 실행
  async analyzeGptOnly(
    fileId: string
  ): Promise<{ success: boolean; data: RiskAnalysisResult }> {
    const response = await fetch(
      `${this.baseUrl}/risk-analysis/analyze-gpt-only`,
      {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify({
          file_id: fileId,
        }),
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // 파이프라인 상태 확인
  async getPipelineStatus(pipelineId: string): Promise<{
    success: boolean;
    status: string;
    progress: number;
    message: string;
    data?: any;
  }> {
    const response = await fetch(
      `${this.baseUrl}/api/pipeline/status/${pipelineId}`,
      {
        headers: this.getHeaders(null),
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // 위험 분석 결과 조회 (특정 파이프라인)
  async getRiskAnalysisResult(
    pipelineId: string
  ): Promise<{ success: boolean; data: RiskAnalysisResult }> {
    const response = await fetch(
      `${this.baseUrl}/risk-analysis/${pipelineId}`,
      {
        headers: this.getHeaders(null),
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // Neo4j 통계 조회
  async getNeo4jStats(connectionInfo: {
    serverUrl: string;
    username: string;
    password: string;
    database: string;
  }): Promise<{
    success: boolean;
    nodeCount: number;
    relationshipCount: number;
    database: string;
  }> {
    const response = await fetch(`${this.baseUrl}/api/neo4j/stats`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(connectionInfo),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  async getSigmaGraphData(connectionInfo: {
    serverUrl: string;
    username: string;
    password: string;
    database: string;
    limit?: number;
  }): Promise<{
    success: boolean;
    nodes: Array<{
      id: number;
      labels: string[];
      properties: Record<string, unknown>;
    }>;
    relationships: Array<{
      id: number;
      type: string;
      start_node: number;
      end_node: number;
      properties: Record<string, unknown>;
    }>;
    database: string;
  }> {
    const response = await fetch(`${this.baseUrl}/api/neo4j/graph-data`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(connectionInfo),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // 파일 업로드
  async uploadContract(file: File): Promise<{
    success: boolean;
    file_id: string;
    filename: string;
    message: string;
  }> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${this.baseUrl}/api/files/upload/contract`, {
      method: "POST",
      headers: this.getHeaders(null), // FormData는 Content-Type을 자동으로 설정
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // 파일 업로드와 파이프라인 실행을 한 번에 처리
  async uploadAndRunPipeline(
    file: File,
    startStep: number = 1,
    neo4jDatabase?: string
  ): Promise<{
    success: boolean;
    message: string;
    data?: {
      pipeline_id: string;
      keyword: string;
      neo4j_database?: string;
      file_info: any;
    };
  }> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("start_step", startStep.toString());
    if (neo4jDatabase) {
      formData.append("neo4j_database", neo4jDatabase);
    }

    const response = await fetch(`${this.baseUrl}/api/files/upload-and-run`, {
      method: "POST",
      headers: this.getHeaders(null), // FormData는 Content-Type을 자동으로 설정
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // 업로드된 파일로 파이프라인 실행
  async runPipelineWithFile(
    fileId: string,
    startStep: number = 0
  ): Promise<{
    success: boolean;
    message: string;
    data?: {
      pipeline_id: string;
      keyword: string;
      file_info: any;
    };
  }> {
    const formData = new FormData();
    formData.append("file_id", fileId);
    formData.append("start_step", startStep.toString());

    const response = await fetch(`${this.baseUrl}/api/pipeline/run-with-file`, {
      method: "POST",
      headers: this.getHeaders(null), // FormData는 Content-Type을 자동으로 설정
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // 파일 삭제
  async deleteFile(fileId: string): Promise<{
    success: boolean;
    message: string;
  }> {
    const response = await fetch(`${this.baseUrl}/api/files/${fileId}`, {
      method: "DELETE",
      headers: this.getHeaders(null),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // 위험 분석 실행 (업로드된 파일)
  async analyzeUploadedFileRisk(
    fileId: string,
    selectedParts: string = "all"
  ): Promise<{
    success: boolean;
    message: string;
    data?: {
      analysis_id: string;
      analysis_result: any;
    };
  }> {
    const response = await fetch(
      `${this.baseUrl}/risk-analysis/analyze-uploaded-file`,
      {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify({
          file_id: fileId,
          selected_parts: selectedParts,
        }),
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // 특정 파일의 저장된 위험 분석 결과 조회
  async getSavedRiskAnalysisByFile(fileId: string): Promise<{
    success: boolean;
    data: RiskAnalysisResult;
  }> {
    const response = await fetch(
      `${this.baseUrl}/risk-analysis/saved/${fileId}`
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // RAG 구축된 계약서 목록 조회
  async getRagContracts(): Promise<{
    success: boolean;
    data: Array<{
      file_id: string;
      filename: string;
      uploaded_at: string;
      file_size: number;
      file_type: string;
    }>;
    total_count?: number;
  }> {
    const response = await fetch(
      `${this.baseUrl}/risk-analysis/rag-contracts`,
      {
        headers: this.getHeaders(null),
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // Neo4j 데이터베이스 목록 조회
  async getNeo4jDatabases(): Promise<{
    success: boolean;
    databases: Array<{
      name: string;
      status: string;
      default: boolean;
    }>;
  }> {
    const neo4jUri = import.meta.env.VITE_NEO4J_URI || "bolt://localhost:7687";
    const neo4jUser = import.meta.env.VITE_NEO4J_USER || "neo4j";
    const neo4jPassword = import.meta.env.VITE_NEO4J_PASSWORD || "";

    const response = await fetch(`${this.baseUrl}/api/neo4j/databases`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        serverUrl: neo4jUri,
        username: neo4jUser,
        password: neo4jPassword,
        database: "system",
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }
}

export const api = new ApiService();
