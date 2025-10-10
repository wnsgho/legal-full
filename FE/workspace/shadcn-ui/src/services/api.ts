const API_BASE_URL = "http://localhost:8000";

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
  }

  // RAG 기반 채팅 메시지 전송
  async sendChatMessage(
    message: string,
    fileId?: string,
    chatMode: "rag" | "openai" = "rag"
  ): Promise<ChatResponse> {
    const response = await fetch(`${this.baseUrl}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
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
    const response = await fetch(`${this.baseUrl}/chat/openai-basic`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
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
      `${this.baseUrl}/chat/openai-basic/${fileId}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
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
    const response = await fetch(`${this.baseUrl}/chat/history`, {
      method: "DELETE",
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // 파일 목록 조회
  async getFiles(): Promise<{ success: boolean; data: FileInfo[] }> {
    const response = await fetch(`${this.baseUrl}/files`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // 파일 내용 조회
  async getFileContent(
    fileId: string
  ): Promise<{ success: boolean; data: { content: string } }> {
    const response = await fetch(`${this.baseUrl}/files/${fileId}/content`);

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
    const response = await fetch(`${this.baseUrl}/status`);

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
    const response = await fetch(`${this.baseUrl}/risk-analysis/saved`);

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
    const response = await fetch(`${this.baseUrl}/risk-analysis/gpt-results`);

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
        headers: {
          "Content-Type": "application/json",
        },
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
      `${this.baseUrl}/pipeline/status/${pipelineId}`
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
    const response = await fetch(`${this.baseUrl}/risk-analysis/${pipelineId}`);

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
      headers: {
        "Content-Type": "application/json",
      },
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
      headers: {
        "Content-Type": "application/json",
      },
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

    const response = await fetch(`${this.baseUrl}/upload/contract`, {
      method: "POST",
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
    startStep: number = 1
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
    formData.append("file", file);
    formData.append("start_step", startStep.toString());

    const response = await fetch(`${this.baseUrl}/upload-and-run`, {
      method: "POST",
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

    const response = await fetch(`${this.baseUrl}/pipeline/run-with-file`, {
      method: "POST",
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
    const response = await fetch(`${this.baseUrl}/files/${fileId}`, {
      method: "DELETE",
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
        headers: {
          "Content-Type": "application/json",
        },
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
    const response = await fetch(`${this.baseUrl}/risk-analysis/rag-contracts`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }
}

export const api = new ApiService();
