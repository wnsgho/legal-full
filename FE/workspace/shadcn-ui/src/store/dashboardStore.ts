import create from 'zustand';
import {
  Contract,
  AnalysisResult,
  ChatMessage,
  ComparisonResult,
  RiskClause,
  ContractStatus,
  AnalysisStatus,
  RiskLevel,
} from '@/types';
import { api } from '@/services/api';
import { mockContracts, mockAnalysisResults } from '@/lib/mockData';

interface DashboardState {
  contracts: Contract[];
  analysisResults: AnalysisResult[];
  chatMessages: ChatMessage[];
  isUploading: boolean;
  uploadProgress: number;
  currentAnalysis?: {
    id: string;
    progress: number;
    stage: string;
  };
  selectedContract: string;
  viewMode: 'original' | 'summary';
  currentPipelineId?: string;
  systemStatus: {
    rag_system_loaded: boolean;
    neo4j_connected: boolean;
  } | null;

  checkSystemStatus: () => void;
  checkPipelineExists: () => void;
  handlePipelineStart: (pipelineId: string, fileInfo: any) => void;
  handleAnalysisComplete: (result: AnalysisResult) => void;
  handleFileUpload: (files: File[]) => void;
  handleRetryAnalysis: (analysisId: string) => void;
  handleViewResult: (analysisId: string) => void;
  handleCompare: (analysisId1: string, analysisId2: string) => ComparisonResult;
  handleSendMessage: (message: string) => void;
  handleClearChatHistory: () => void;
  handleClauseClick: (clause: RiskClause) => void;
  handleViewAnalysis: (analysisId: string) => void;
  handleDeleteAnalysis: (analysisId: string) => void;
  handleDownloadReport: (analysisId: string) => void;
  handleArchiveAnalysis: (analysisId: string) => void;
  setSelectedContract: (contractId: string) => void;
  setViewMode: (viewMode: 'original' | 'summary') => void;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  contracts: mockContracts,
  analysisResults: mockAnalysisResults,
  chatMessages: [],
  isUploading: false,
  uploadProgress: 0,
  currentAnalysis: undefined,
  selectedContract: "1",
  viewMode: 'original',
  currentPipelineId: undefined,
  systemStatus: null,

  checkSystemStatus: async () => {
    try {
      const response = await api.getStatus();
      if (response.success && response.data) {
        set({ systemStatus: response.data.status });
      }
    } catch (error) {
      console.error("System status check failed:", error);
    }
  },

  checkPipelineExists: async () => {
    const { currentPipelineId } = get();
    if (!currentPipelineId) return;

    try {
      await api.getPipelineStatus(currentPipelineId);
    } catch (error: any) {
      if (error.response?.status === 404 || error.message?.includes("404")) {
        console.warn(
          `Pipeline ${currentPipelineId} not found, clearing current pipeline`
        );
        set({ currentPipelineId: undefined, currentAnalysis: undefined });
        // toast can be called from the component
      }
    }
  },

  handlePipelineStart: (pipelineId: string, fileInfo: any) => {
    set({
      currentPipelineId: pipelineId,
      currentAnalysis: {
        id: pipelineId,
        progress: 0,
        stage: "파이프라인 시작 중...",
      },
    });

    const newContract: Contract = {
      id: pipelineId,
      userId: "user1",
      fileName: fileInfo.filename,
      fileSize: fileInfo.file_size,
      fileType: "application/json",
      uploadedAt: new Date(fileInfo.upload_time),
      status: ContractStatus.PROCESSING,
      s3Key: fileInfo.file_path,
    };

    set((state) => ({ contracts: [newContract, ...state.contracts] }));
  },

  handleAnalysisComplete: (result: AnalysisResult) => {
    set((state) => ({
      analysisResults: [result, ...state.analysisResults],
      currentAnalysis: undefined,
      currentPipelineId: undefined,
    }));
  },

  handleFileUpload: (files: File[]) => {
    // This is a mock handler, will be replaced with real logic
    console.log("Files uploaded:", files);
  },
  handleRetryAnalysis: (analysisId: string) => {
    console.log("Retrying analysis:", analysisId);
  },
  handleViewResult: (analysisId: string) => {
    console.log("Viewing result:", analysisId);
  },
  handleCompare: (analysisId1: string, analysisId2: string): ComparisonResult => {
    // This is a mock handler, will be replaced with real logic
    return {} as ComparisonResult;
  },
  handleSendMessage: (message: string) => {
    // This is a mock handler, will be replaced with real logic
    console.log("Message sent:", message);
  },
  handleClearChatHistory: () => {
    set({ chatMessages: [] });
  },
  handleClauseClick: (clause: RiskClause) => {
    console.log("Clause clicked:", clause);
  },
  handleViewAnalysis: (analysisId: string) => {
    console.log("View analysis:", analysisId);
  },
  handleDeleteAnalysis: (analysisId: string) => {
    set((state) => ({
      analysisResults: state.analysisResults.filter((a) => a.id !== analysisId),
    }));
  },
  handleDownloadReport: (analysisId: string) => {
    console.log("Download report:", analysisId);
  },
  handleArchiveAnalysis: (analysisId: string) => {
    console.log("Archive analysis:", analysisId);
  },
  setSelectedContract: (contractId: string) => {
    set({ selectedContract: contractId });
  },
  setViewMode: (viewMode: 'original' | 'summary') => {
    set({ viewMode });
  },
}));
