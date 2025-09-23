// API 서비스 레이어
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// API 응답 타입 정의
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
}

export interface PipelineResponse {
  success: boolean;
  message: string;
  data?: {
    pipeline_id: string;
    keyword: string;
    file_info: {
      filename: string;
      file_path: string;
      upload_time: string;
      file_size: number;
    };
  };
}

export interface PipelineStatusResponse {
  success: boolean;
  status: string;
  progress: number;
  message: string;
  data?: {
    status: string;
    progress: number;
    message: string;
    start_time?: string;
    end_time?: string;
    file_info?: any;
    keyword?: string;
  };
}

export interface ChatResponse {
  success: boolean;
  answer: string;
  context_count: number;
  processing_time: number;
}

export interface FileUploadResponse {
  success: boolean;
  file_id: string;
  filename: string;
  message: string;
}

export interface FileInfo {
  file_id: string;
  filename: string;
  upload_time: string;
  file_size: number;
}

export interface SystemStatus {
  rag_system_loaded: boolean;
  neo4j_connected: boolean;
  timestamp: string;
}

// API 클라이언트 클래스
class ApiClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;

    // FormData 사용 시 Content-Type 헤더를 설정하지 않음 (브라우저가 자동 설정)
    const isFormData = options.body instanceof FormData;

    const defaultOptions: RequestInit = {
      headers: isFormData
        ? {}
        : {
            "Content-Type": "application/json",
            ...options.headers,
          },
    };

    // FormData가 아닌 경우에만 기본 헤더 병합
    if (!isFormData) {
      defaultOptions.headers = {
        ...defaultOptions.headers,
        ...options.headers,
      };
    } else {
      // FormData인 경우 사용자 정의 헤더만 사용
      defaultOptions.headers = options.headers || {};
    }

    try {
      const response = await fetch(url, { ...defaultOptions, ...options });

      if (!response.ok) {
        const error = new Error(
          `HTTP error! status: ${response.status}`
        ) as any;
        error.response = { status: response.status };
        throw error;
      }

      const data = await response.json();
      return data;
    } catch (error: any) {
      console.error("API request failed:", error);
      // response 정보를 에러에 포함
      if (!error.response && error.message?.includes("HTTP error!")) {
        const statusMatch = error.message.match(/status: (\d+)/);
        if (statusMatch) {
          error.response = { status: parseInt(statusMatch[1]) };
        }
      }
      throw error;
    }
  }

  // 파일 업로드 및 파이프라인 관련
  async uploadAndRunPipeline(
    file: File,
    startStep: number = 1
  ): Promise<ApiResponse<PipelineResponse>> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("start_step", startStep.toString());

    console.log("📤 Uploading file:", file.name, "Size:", file.size);
    console.log("📤 Start step:", startStep);

    return this.request<PipelineResponse>("/upload-and-run", {
      method: "POST",
      body: formData,
      // FormData 사용 시 헤더 제거 (브라우저가 자동으로 multipart/form-data 설정)
    });
  }

  async uploadContract(file: File): Promise<ApiResponse<FileUploadResponse>> {
    const formData = new FormData();
    formData.append("file", file);

    return this.request<FileUploadResponse>("/upload/contract", {
      method: "POST",
      body: formData,
      headers: {}, // FormData 사용 시 Content-Type 헤더 제거
    });
  }

  async runPipelineWithFile(
    fileId: string,
    startStep: number = 1
  ): Promise<ApiResponse<PipelineResponse>> {
    const formData = new FormData();
    formData.append("file_id", fileId);
    formData.append("start_step", startStep.toString());

    return this.request<PipelineResponse>("/pipeline/run-with-file", {
      method: "POST",
      body: formData,
      headers: {}, // FormData 사용 시 Content-Type 헤더 제거
    });
  }

  async getPipelineStatus(
    pipelineId: string
  ): Promise<ApiResponse<PipelineStatusResponse>> {
    return this.request<PipelineStatusResponse>(
      `/pipeline/status/${pipelineId}`
    );
  }

  async getFiles(): Promise<ApiResponse<{ files: FileInfo[] }>> {
    return this.request<{ files: FileInfo[] }>("/files");
  }

  async deleteFile(fileId: string): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>(`/files/${fileId}`, {
      method: "DELETE",
    });
  }

  // AI 분석 및 챗봇 관련
  async sendChatMessage(
    question: string,
    maxTokens: number = 8192,
    temperature: number = 0.5
  ): Promise<ApiResponse<ChatResponse>> {
    return this.request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({
        question,
        max_tokens: maxTokens,
        temperature,
      }),
    });
  }

  async analyzeRisks(
    question: string,
    maxTokens: number = 8192,
    temperature: number = 0.5
  ): Promise<ApiResponse<ChatResponse>> {
    return this.request<ChatResponse>("/analyze-risks", {
      method: "POST",
      body: JSON.stringify({
        question,
        max_tokens: maxTokens,
        temperature,
      }),
    });
  }

  async autoAnalyzeRisks(
    question: string,
    maxTokens: number = 8192,
    temperature: number = 0.5
  ): Promise<ApiResponse<ChatResponse>> {
    return this.request<ChatResponse>("/analysis/auto-risk", {
      method: "POST",
      body: JSON.stringify({
        question,
        max_tokens: maxTokens,
        temperature,
      }),
    });
  }

  async getChatHistory(
    limit: number = 10
  ): Promise<ApiResponse<{ history: any[] }>> {
    return this.request<{ history: any[] }>(`/chat/history?limit=${limit}`);
  }

  async clearChatHistory(): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>("/chat/history", {
      method: "DELETE",
    });
  }

  // 시스템 상태 관련
  async getHealth(): Promise<
    ApiResponse<{ status: string; timestamp: string; version: string }>
  > {
    return this.request<{ status: string; timestamp: string; version: string }>(
      "/health"
    );
  }

  async getStatus(): Promise<ApiResponse<{ status: SystemStatus }>> {
    return this.request<{ status: SystemStatus }>("/status");
  }
}

// API 클라이언트 인스턴스 생성
export const apiClient = new ApiClient();

// 편의 함수들
export const api = {
  // 파일 업로드 및 파이프라인
  uploadAndRunPipeline: (file: File, startStep?: number) =>
    apiClient.uploadAndRunPipeline(file, startStep),

  uploadContract: (file: File) => apiClient.uploadContract(file),

  runPipelineWithFile: (fileId: string, startStep?: number) =>
    apiClient.runPipelineWithFile(fileId, startStep),

  getPipelineStatus: (pipelineId: string) =>
    apiClient.getPipelineStatus(pipelineId),

  getFiles: () => apiClient.getFiles(),

  deleteFile: (fileId: string) => apiClient.deleteFile(fileId),

  // AI 분석 및 챗봇
  sendChatMessage: (
    question: string,
    maxTokens?: number,
    temperature?: number
  ) => apiClient.sendChatMessage(question, maxTokens, temperature),

  analyzeRisks: (question: string, maxTokens?: number, temperature?: number) =>
    apiClient.analyzeRisks(question, maxTokens, temperature),

  autoAnalyzeRisks: (
    question: string,
    maxTokens?: number,
    temperature?: number
  ) => apiClient.autoAnalyzeRisks(question, maxTokens, temperature),

  getChatHistory: (limit?: number) => apiClient.getChatHistory(limit),

  clearChatHistory: () => apiClient.clearChatHistory(),

  // 시스템 상태
  getHealth: () => apiClient.getHealth(),

  getStatus: () => apiClient.getStatus(),
};
