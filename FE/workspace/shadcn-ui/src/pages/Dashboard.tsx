import React, { useState, useEffect, useCallback } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Link } from "react-router-dom";
import {
  Upload,
  BarChart3,
  MessageSquare,
  FileText,
  Shield,
  Users,
  Clock,
  Database,
  Network,
} from "lucide-react";
import FileUpload from "@/components/FileUpload";
import AnalysisProgress from "@/components/AnalysisProgress";
import RiskClauses from "@/components/RiskClauses";
import ChatInterface from "@/components/ChatInterface";
import ComparisonChatInterface from "@/components/ComparisonChatInterface";
import RagRiskAnalysis from "@/components/RagRiskAnalysis";
import MarkdownViewer from "@/components/MarkdownViewer";
import RiskAnalysisResults from "@/components/RiskAnalysisResults";
import PartRiskClauses from "@/components/PartRiskClauses";
import SigmaKnowledgeGraph from "@/components/SigmaKnowledgeGraph";
import ErrorBoundary from "@/components/ErrorBoundary";
import {
  mockContracts,
  mockAnalysisResults,
  contractSampleText,
} from "@/lib/mockData";
import {
  Contract,
  AnalysisResult,
  ChatMessage,
  RiskClause,
  ContractStatus,
  AnalysisStatus,
  RiskLevel,
} from "@/types";
import { api } from "@/services/api";
import { useToast } from "@/hooks/use-toast";

const Dashboard: React.FC = () => {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [analysisResults, setAnalysisResults] = useState<AnalysisResult[]>([]);
  const [selectedContractContent, setSelectedContractContent] =
    useState<string>("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [currentAnalysis, setCurrentAnalysis] = useState<
    | {
        id: string;
        progress: number;
        stage: string;
      }
    | undefined
  >();
  const [selectedContract, setSelectedContract] = useState<string>("");
  const [viewMode, setViewMode] = useState<"original" | "summary">("original");
  const [showRiskAnalysisDetails, setShowRiskAnalysisDetails] =
    useState<boolean>(false);
  const [showGptAnalysisDetails, setShowGptAnalysisDetails] =
    useState<boolean>(false);
  const [showRawText, setShowRawText] = useState<boolean>(false);
  const [currentPipelineId, setCurrentPipelineId] = useState<
    string | undefined
  >();
  const [systemStatus, setSystemStatus] = useState<{
    rag_system_loaded: boolean;
    neo4j_connected: boolean;
  } | null>(null);
  interface RiskAnalysisResult {
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

  const [riskAnalysisResults, setRiskAnalysisResults] = useState<
    RiskAnalysisResult[]
  >([]);
  const [activeTab, setActiveTab] = useState<string>("upload");

  const [gptAnalysisResults, setGptAnalysisResults] = useState<
    RiskAnalysisResult[]
  >([]);

  const [isGptAnalyzing, setIsGptAnalyzing] = useState<boolean>(false);

  // 위험 분석 결과에서 위험 조항들을 추출하는 함수
  const getRiskClausesFromAnalysis = (): string[] => {
    const allRiskClauses: string[] = [];

    riskAnalysisResults.forEach((result) => {
      if (result.analysis_result?.part_results) {
        result.analysis_result.part_results.forEach((part) => {
          if (part.risk_clauses || part.relevant_clauses) {
            allRiskClauses.push(
              ...(part.risk_clauses || part.relevant_clauses)
            );
          }
        });
      }
    });

    // 중복 제거
    return [...new Set(allRiskClauses)];
  };
  const { toast } = useToast();

  // 위험 분석 결과 조회
  const fetchRiskAnalysisResults = useCallback(async () => {
    try {
      console.log("🔍 위험 분석 결과 조회 시작");
      const response = await api.getSavedRiskAnalysis();
      console.log("🔍 API 응답:", response);
      if (response.success && response.data) {
        const results =
          (response.data as { results?: RiskAnalysisResult[] }).results ||
          response.data;
        console.log("🔍 로드된 결과:", results);
        setRiskAnalysisResults(results as RiskAnalysisResult[]);
      }
    } catch (error) {
      console.error("위험 분석 결과 조회 실패:", error);
    }
  }, []);

  // GPT 분석 결과 조회
  const fetchGptAnalysisResults = useCallback(async () => {
    try {
      console.log("🔍 GPT 분석 결과 조회 시작");
      const response = await api.getGptAnalysisResults();
      console.log("🔍 GPT API 응답:", response);
      if (response.success && response.data) {
        const results =
          (response.data as { results?: RiskAnalysisResult[] }).results ||
          response.data;
        console.log("🔍 GPT 로드된 결과:", results);
        setGptAnalysisResults(results as RiskAnalysisResult[]);
      } else {
        console.log("🔍 GPT 분석 결과 없음, 빈 배열로 초기화");
        setGptAnalysisResults([]);
      }
    } catch (error) {
      console.error("GPT 분석 결과 조회 실패:", error);
      // 오류 발생 시 빈 배열로 초기화
      setGptAnalysisResults([]);
    }
  }, []);

  // 시스템 상태 확인
  useEffect(() => {
    const checkSystemStatus = async () => {
      try {
        const response = await api.getStatus();
        if (response.success && response.data) {
          setSystemStatus(response.data.status);
        }
      } catch (error) {
        console.error("System status check failed:", error);
      }
    };

    checkSystemStatus();
  }, []);

  // 파일 목록 로드 함수
  const loadFiles = async () => {
    try {
      console.log("📁 파일 목록 조회 시작...");
      const filesResponse = await api.getFiles();
      console.log("📁 파일 목록 응답:", filesResponse);
      console.log("📁 응답 성공 여부:", filesResponse.success);
      console.log("📁 응답 데이터:", filesResponse.data);
      console.log("📁 응답 데이터 타입:", typeof filesResponse.data);

      if (filesResponse.success && filesResponse.data) {
        console.log("📁 파일 목록 데이터:", filesResponse.data);
        console.log("📁 파일 개수:", filesResponse.data.length);

        const fileContracts: Contract[] = filesResponse.data.map((file) => ({
          id: file.file_id,
          userId: "user1",
          fileName: file.filename,
          fileSize: file.file_size,
          fileType: "application/json",
          uploadedAt: new Date(file.upload_time),
          status: ContractStatus.UPLOADED,
          s3Key: file.file_path || "",
        }));
        console.log("📁 변환된 계약서 목록:", fileContracts);
        console.log("📁 변환된 계약서 개수:", fileContracts.length);
        setContracts(fileContracts);

        // 첫 번째 계약서를 기본 선택으로 설정
        if (fileContracts.length > 0) {
          console.log("📁 첫 번째 계약서 선택:", fileContracts[0].id);
          setSelectedContract(fileContracts[0].id);
        } else {
          console.log("📁 변환된 계약서가 없음");
        }
      } else {
        console.log("📁 파일 목록 조회 실패 또는 데이터 없음");
        console.log("📁 success:", filesResponse.success);
        console.log("📁 data:", filesResponse.data);
        console.log(
          "📁 data.files:",
          (filesResponse.data as { files?: unknown[] })?.files
        );
      }
    } catch (error) {
      console.error("파일 목록 로드 실패:", error);
      console.error("에러 상세:", error);
    }
  };

  // 컴포넌트 마운트 시 초기 데이터 로드
  useEffect(() => {
    console.log("🚀 컴포넌트 마운트 - 초기 데이터 로드 시작");
    loadFiles();
    fetchRiskAnalysisResults();
    fetchGptAnalysisResults();
  }, [fetchRiskAnalysisResults, fetchGptAnalysisResults]);

  // 현재 파이프라인 상태 확인 (서버 재시작 감지)
  useEffect(() => {
    if (!currentPipelineId) return;

    const checkPipelineExists = async () => {
      try {
        await api.getPipelineStatus(currentPipelineId);
      } catch (error: unknown) {
        // 404 오류 시 현재 파이프라인 ID 초기화
        if (
          (error as { response?: { status?: number }; message?: string })
            ?.response?.status === 404 ||
          (
            error as { response?: { status?: number }; message?: string }
          )?.message?.includes("404")
        ) {
          console.warn(
            `Pipeline ${currentPipelineId} not found, clearing current pipeline`
          );
          setCurrentPipelineId(undefined);
          setCurrentAnalysis(undefined);
          toast({
            title: "파이프라인 상태 초기화",
            description:
              "서버가 재시작되어 이전 파이프라인 정보가 초기화되었습니다.",
          });
        }
      }
    };

    // 컴포넌트 마운트 시 한 번 확인
    checkPipelineExists();
  }, [currentPipelineId, toast]);

  // 파이프라인 시작 핸들러
  const handlePipelineStart = (
    pipelineId: string,
    fileInfo: Record<string, unknown>
  ) => {
    setCurrentPipelineId(pipelineId);
    setCurrentAnalysis({
      id: pipelineId,
      progress: 0,
      stage: "파이프라인 시작 중...",
    });

    // 새로운 계약서 추가
    const newContract: Contract = {
      id: pipelineId,
      userId: "user1",
      fileName: fileInfo.filename as string,
      fileSize: fileInfo.file_size as number,
      fileType: "application/json",
      uploadedAt: new Date(fileInfo.upload_time as string),
      status: ContractStatus.PROCESSING,
      s3Key: fileInfo.file_path as string,
    };

    setContracts((prev) => [newContract, ...prev]);
  };

  // 분석 완료 핸들러
  const handleAnalysisComplete = (result: AnalysisResult) => {
    setAnalysisResults((prev) => [result, ...prev]);
    setCurrentAnalysis(undefined);
    setCurrentPipelineId(undefined);
  };

  // 선택된 계약서 내용 조회
  const fetchContractContent = async (contractId: string) => {
    try {
      console.log("📄 계약서 내용 조회 시작:", contractId);
      const response = await api.getFileContent(contractId);
      console.log("📄 계약서 내용 응답:", response);

      if (response.success && response.data) {
        const content = (response.data as Record<string, unknown>)
          .content as string;
        console.log("📄 계약서 내용 길이:", content.length);
        setSelectedContractContent(content);
      } else {
        console.log("📄 계약서 내용 조회 실패");
        setSelectedContractContent("계약서 내용을 불러올 수 없습니다.");
      }
    } catch (error) {
      console.error("계약서 내용 조회 실패:", error);
      setSelectedContractContent("계약서 내용을 불러올 수 없습니다.");
    }
  };

  // 선택된 계약서가 변경될 때 내용 조회
  useEffect(() => {
    if (selectedContract) {
      fetchContractContent(selectedContract);
    } else {
      setSelectedContractContent(contractSampleText);
    }
  }, [selectedContract]);

  // 파이프라인 완료 시 위험 분석 결과 조회 (분석 탭 활성화 시에만)
  useEffect(() => {
    if (currentPipelineId && activeTab === "analysis") {
      const checkRiskAnalysis = async () => {
        try {
          const response = await api.getRiskAnalysisResult(currentPipelineId);
          if (response.success) {
            setRiskAnalysisResults((prev) => [
              response.data as RiskAnalysisResult,
              ...prev,
            ]);
            toast({
              title: "위험 분석 완료",
              description: "계약서 위험 분석이 완료되었습니다.",
            });
          }
        } catch (error) {
          // 위험 분석 결과가 아직 없는 경우 (정상)
          console.log("위험 분석 결과 아직 없음");
        }
      };

      // 분석 탭이 활성화될 때만 한 번 확인
      checkRiskAnalysis();
    }
  }, [currentPipelineId, activeTab, toast]);

  // Mock handlers
  const handleFileUpload = (files: File[]) => {
    setIsUploading(true);
    setUploadProgress(0);

    // Simulate upload progress
    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsUploading(false);

          // Add new contracts
          const newContracts = files.map((file, index) => ({
            id: `new_${Date.now()}_${index}`,
            userId: "user1",
            fileName: file.name,
            fileSize: file.size,
            fileType: file.type,
            uploadedAt: new Date(),
            status: ContractStatus.UPLOADED,
            s3Key: `contracts/user1/${file.name}`,
          }));

          setContracts((prev) => [...prev, ...newContracts]);

          // Start analysis simulation
          setTimeout(() => {
            startAnalysisSimulation(newContracts[0].id);
          }, 1000);

          return 100;
        }
        return prev + 10;
      });
    }, 200);
  };

  const startAnalysisSimulation = (contractId: string) => {
    const analysisId = `analysis_${Date.now()}`;
    setCurrentAnalysis({
      id: analysisId,
      progress: 0,
      stage: "AI 모델 초기화 중...",
    });

    const stages = [
      "계약서 텍스트 추출 중...",
      "자연어 처리 중...",
      "위험 조항 식별 중...",
      "법률 조항 분석 중...",
      "권장사항 생성 중...",
      "분석 완료",
    ];

    let currentStage = 0;
    const interval = setInterval(() => {
      setCurrentAnalysis((prev) => {
        if (!prev) return undefined;

        const newProgress = prev.progress + 16;
        if (newProgress >= 100) {
          clearInterval(interval);

          // Add completed analysis
          const newAnalysis: AnalysisResult = {
            id: analysisId,
            contractId,
            status: AnalysisStatus.COMPLETED,
            riskLevel: RiskLevel.HIGH,
            riskClauses: mockAnalysisResults[0].riskClauses,
            summary:
              "새로 업로드된 계약서에 대한 AI 분석이 완료되었습니다. 총 4개의 위험 조항이 발견되었으며, 특히 손해배상 조항에 주의가 필요합니다.",
            recommendations: [
              "손해배상액 조항 재검토 필요",
              "계약 기간 명확화 권장",
              "분쟁 해결 방법 개선 검토",
            ],
            aiModel: "GPT-4",
            confidence: 0.94,
            createdAt: new Date(),
            processingTimeMs: 18000,
          };

          setAnalysisResults((prev) => [newAnalysis, ...prev]);
          setCurrentAnalysis(undefined);
          return undefined;
        }

        return {
          ...prev,
          progress: newProgress,
          stage: stages[Math.min(currentStage, stages.length - 1)],
        };
      });
      currentStage++;
    }, 1000);
  };

  const handleRetryAnalysis = (analysisId: string) => {
    console.log("Retrying analysis:", analysisId);
  };

  const handleViewResult = (analysisId: string) => {
    console.log("Viewing result:", analysisId);
  };

  const handleSendMessage = (message: string) => {
    // AI 응답이 포함된 경우 (ChatInterface에서 전달됨)
    if (message.startsWith("AI: ")) {
      const aiResponse = message.substring(4); // "AI: " 제거
      const aiMessage: ChatMessage = {
        id: `ai_${Date.now()}`,
        contractId: selectedContract,
        message: "",
        response: aiResponse,
        isUserMessage: false,
        createdAt: new Date(),
      };
      setChatMessages((prev) => [...prev, aiMessage]);
    } else {
      // 사용자 메시지인 경우
      const newMessage: ChatMessage = {
        id: `msg_${Date.now()}`,
        contractId: selectedContract,
        message,
        isUserMessage: true,
        createdAt: new Date(),
      };
      setChatMessages((prev) => [...prev, newMessage]);
    }
  };

  const handleClearChatHistory = () => {
    setChatMessages([]);
  };

  const handleClauseClick = (clause: RiskClause) => {
    console.log("Clause clicked:", clause);
  };

  const handleViewAnalysis = (analysisId: string) => {
    console.log("View analysis:", analysisId);
  };

  const handleDeleteAnalysis = (analysisId: string) => {
    setAnalysisResults((prev) => prev.filter((a) => a.id !== analysisId));
  };

  const handleDownloadReport = (analysisId: string) => {
    console.log("Download report:", analysisId);
  };

  const handleArchiveAnalysis = (analysisId: string) => {
    console.log("Archive analysis:", analysisId);
  };

  // GPT 분석 시작 핸들러
  const handleGptAnalysis = async () => {
    if (!selectedContract) {
      toast({
        title: "계약서 선택 필요",
        description: "GPT 분석을 위해 계약서를 먼저 선택해주세요.",
        variant: "destructive",
      });
      return;
    }

    setIsGptAnalyzing(true);

    try {
      console.log("🤖 GPT 분석 시작:", selectedContract);
      toast({
        title: "GPT 분석 시작",
        description: "GPT 전용 위험 분석을 시작합니다...",
      });

      const response = await api.analyzeGptOnly(selectedContract);

      if (response.success && response.data) {
        setGptAnalysisResults((prev) => [
          response.data as RiskAnalysisResult,
          ...prev,
        ]);
        toast({
          title: "GPT 분석 완료",
          description: "GPT 전용 위험 분석이 완료되었습니다.",
        });
      } else {
        throw new Error("GPT 분석 실패");
      }
    } catch (error) {
      console.error("GPT 분석 실패:", error);
      toast({
        title: "GPT 분석 실패",
        description: "GPT 분석 중 오류가 발생했습니다.",
        variant: "destructive",
      });
    } finally {
      setIsGptAnalyzing(false);
    }
  };

  const currentAnalysisResult = analysisResults.find(
    (a) => a.contractId === selectedContract
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <Shield className="h-8 w-8 text-blue-600" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">
                  계약서 분석 AI
                </h1>
                <p className="text-sm text-gray-500">
                  스마트 계약서 리스크 분석 서비스
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {systemStatus && (
                <div className="flex items-center space-x-2">
                  <Badge
                    variant={
                      systemStatus.rag_system_loaded ? "default" : "destructive"
                    }
                    className="text-xs"
                  >
                    RAG:{" "}
                    {systemStatus.rag_system_loaded ? "연결됨" : "연결 안됨"}
                  </Badge>
                  <Badge
                    variant={
                      systemStatus.neo4j_connected ? "default" : "destructive"
                    }
                    className="text-xs"
                  >
                    Neo4j:{" "}
                    {systemStatus.neo4j_connected ? "연결됨" : "연결 안됨"}
                  </Badge>
                </div>
              )}

              <Badge variant="outline" className="text-xs">
                <Users className="h-3 w-3 mr-1" />
                Pro 플랜
              </Badge>
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <span className="text-sm font-medium text-blue-600">김</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs
          value={activeTab}
          onValueChange={(value) => {
            setActiveTab(value);
            if (value === "analysis" || value === "risk-analysis") {
              fetchRiskAnalysisResults();
              fetchGptAnalysisResults();
            }
          }}
          className="space-y-6"
        >
          <TabsList className="grid w-full grid-cols-6">
            <TabsTrigger value="upload" className="flex items-center space-x-2">
              <Upload className="h-4 w-4" />
              <span>업로드</span>
            </TabsTrigger>
            <TabsTrigger
              value="analysis"
              className="flex items-center space-x-2"
            >
              <BarChart3 className="h-4 w-4" />
              <span>분석 결과</span>
            </TabsTrigger>
            <TabsTrigger
              value="risk-analysis"
              className="flex items-center space-x-2"
            >
              <Shield className="h-4 w-4" />
              <span>위험 분석</span>
            </TabsTrigger>
            <TabsTrigger
              value="rag-risk"
              className="flex items-center space-x-2"
            >
              <Database className="h-4 w-4" />
              <span>RAG 분석</span>
            </TabsTrigger>
            <TabsTrigger value="chat" className="flex items-center space-x-2">
              <MessageSquare className="h-4 w-4" />
              <span>AI 상담</span>
            </TabsTrigger>
            <TabsTrigger
              value="comparison"
              className="flex items-center space-x-2"
            >
              <MessageSquare className="h-4 w-4" />
              <span>AI 비교</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="upload" className="space-y-6">
            <FileUpload
              onFileUpload={handleFileUpload}
              uploadedContracts={contracts}
              isUploading={isUploading}
              uploadProgress={uploadProgress}
              onPipelineStart={handlePipelineStart}
            />
            <ErrorBoundary>
              <div className="h-[1200px] border rounded-lg overflow-hidden">
                <SigmaKnowledgeGraph
                  width="100%"
                  height="100%"
                  limit={5000}
                  autoLoad={true}
                />
              </div>
            </ErrorBoundary>
          </TabsContent>

          <TabsContent value="analysis" className="space-y-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900">분석 결과</h2>
              <div className="flex items-center space-x-4">
                {contracts.length > 0 && (
                  <div className="flex items-center space-x-2">
                    <label className="text-sm font-medium text-gray-700">
                      계약서 선택:
                    </label>
                    <select
                      value={selectedContract}
                      onChange={(e) => setSelectedContract(e.target.value)}
                      className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {contracts.map((contract) => (
                        <option key={contract.id} value={contract.id}>
                          {contract.fileName}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                <div className="flex items-center space-x-2">
                  <Button
                    variant={viewMode === "original" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setViewMode("original")}
                  >
                    원문 보기
                  </Button>
                  <Button
                    variant={viewMode === "summary" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setViewMode("summary")}
                  >
                    요약 보기
                  </Button>
                </div>
              </div>
            </div>

            {contracts.length > 0 ? (
              <>
                {/* 위험 분석 결과 섹션 */}
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-4">위험 분석 결과</h3>
                  <RiskAnalysisResults fileId={selectedContract} />
                </div>

                {/* 파트별 위험 조항 섹션 */}
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-4">
                    파트별 위험 조항
                  </h3>
                  <PartRiskClauses
                    partResults={riskAnalysisResults.flatMap(
                      (result) => result.analysis_result?.part_results || []
                    )}
                    title="하이브리드 분석 - 파트별 위험 조항"
                    showRecommendations={true}
                  />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div>
                    {viewMode === "original" ? (
                      <MarkdownViewer
                        content={selectedContractContent}
                        title="계약서 원문"
                        showRaw={showRawText}
                        onToggleRaw={setShowRawText}
                      />
                    ) : currentAnalysisResult ? (
                      <Card>
                        <CardHeader>
                          <CardTitle>분석 요약</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-4">
                            <div>
                              <h4 className="font-semibold mb-2">분석 요약</h4>
                              <p className="mb-4">
                                {currentAnalysisResult.summary}
                              </p>
                            </div>
                            <div>
                              <h4 className="font-semibold mb-2">
                                주요 권장사항
                              </h4>
                              <ul className="list-disc list-inside space-y-1">
                                {currentAnalysisResult.recommendations.map(
                                  (rec, index) => (
                                    <li key={index} className="text-sm">
                                      {rec}
                                    </li>
                                  )
                                )}
                              </ul>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ) : (
                      <Card>
                        <CardHeader>
                          <CardTitle>분석 요약</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="text-center py-8">
                            <p className="text-gray-500">
                              선택된 계약서에 대한 분석 결과가 없습니다.
                            </p>
                          </div>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                  <div>
                    {currentAnalysisResult ? (
                      <RiskClauses
                        riskClauses={currentAnalysisResult.riskClauses}
                        contractText={selectedContractContent}
                        onClauseClick={handleClauseClick}
                        onRiskAnalysisComplete={(analysis) => {
                          console.log("Risk analysis completed:", analysis);
                        }}
                      />
                    ) : (
                      <Card>
                        <CardHeader>
                          <CardTitle className="flex items-center gap-2">
                            <span>⚠️ 위험 조항</span>
                            <Badge variant="destructive">
                              {getRiskClausesFromAnalysis().length}개
                            </Badge>
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          {getRiskClausesFromAnalysis().length > 0 ? (
                            <div className="space-y-3">
                              {getRiskClausesFromAnalysis().map(
                                (clause, index) => (
                                  <div
                                    key={index}
                                    className="p-3 bg-red-50 rounded-lg border border-red-200"
                                  >
                                    <p className="text-sm text-red-800 font-medium">
                                      {clause}
                                    </p>
                                  </div>
                                )
                              )}
                            </div>
                          ) : (
                            <div className="text-center py-8">
                              <p className="text-gray-500">
                                분석 결과가 없어 위험 조항을 표시할 수 없습니다.
                              </p>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <Card>
                <CardContent className="p-8 text-center">
                  <FileText className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                  <p className="text-lg font-medium mb-2">
                    업로드된 계약서가 없습니다
                  </p>
                  <p className="text-sm text-gray-500">
                    계약서를 업로드하고 분석을 시작해보세요.
                  </p>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="risk-analysis" className="space-y-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900">
                위험 분석 결과
              </h2>
              <Button onClick={fetchRiskAnalysisResults} variant="outline">
                새로고침
              </Button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* 우리의 결과물 (하이브리드 분석) */}
              <div className="space-y-4">
                <div className="flex items-center space-x-2 mb-4">
                  <Database className="h-5 w-5 text-blue-600" />
                  <h3 className="text-lg font-semibold text-gray-900">
                    하이브리드 분석 결과
                  </h3>
                  <Badge
                    variant="default"
                    className="bg-blue-100 text-blue-800"
                  >
                    지식그래프 + LLM
                  </Badge>
                </div>

                {/* 하이브리드 분석 파트별 위험 조항 */}
                {riskAnalysisResults.length > 0 && (
                  <div className="mb-6">
                    <PartRiskClauses
                      partResults={riskAnalysisResults.flatMap(
                        (result) => result.analysis_result?.part_results || []
                      )}
                      title="하이브리드 분석 - 파트별 위험 조항"
                      showRecommendations={true}
                    />
                  </div>
                )}

                {riskAnalysisResults.length > 0 ? (
                  <div className="space-y-4">
                    {riskAnalysisResults.map((result, index) => (
                      <Card key={result.analysis_id || index}>
                        <CardHeader>
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-base">
                              {result.contract_name}
                            </CardTitle>
                            <Badge variant="outline">
                              {new Date(result.created_at).toLocaleDateString()}
                            </Badge>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-3">
                            <div className="grid grid-cols-2 gap-3">
                              <div className="text-center">
                                <div className="text-xl font-bold text-red-600">
                                  {result.analysis_result?.overall_risk_score?.toFixed(
                                    1
                                  ) || "N/A"}
                                </div>
                                <div className="text-xs text-gray-600">
                                  전체 위험도
                                </div>
                              </div>
                              <div className="text-center">
                                <div className="text-xl font-bold text-blue-600">
                                  {result.analysis_result?.part_results
                                    ?.length || 0}
                                </div>
                                <div className="text-xs text-gray-600">
                                  분석 파트
                                </div>
                              </div>
                            </div>

                            <div className="space-y-2">
                              <div className="flex items-center justify-between">
                                <h4 className="font-medium text-sm">
                                  파트별 위험 분석
                                </h4>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="text-xs h-6 px-2"
                                  onClick={() =>
                                    setShowRiskAnalysisDetails(true)
                                  }
                                >
                                  상세 보기
                                </Button>
                              </div>
                              {result.analysis_result?.part_results
                                ?.slice(0, 2)
                                .map((part, partIndex: number) => (
                                  <div
                                    key={partIndex}
                                    className="border rounded-lg p-3"
                                  >
                                    <div className="flex items-center justify-between mb-2">
                                      <h5 className="font-medium text-sm">
                                        {part.part_title}
                                      </h5>
                                      <Badge
                                        variant={
                                          part.risk_level === "CRITICAL"
                                            ? "destructive"
                                            : part.risk_level === "HIGH"
                                            ? "destructive"
                                            : part.risk_level === "MEDIUM"
                                            ? "secondary"
                                            : "outline"
                                        }
                                        className="text-xs"
                                      >
                                        {part.risk_level}
                                      </Badge>
                                    </div>
                                    <div className="text-xs text-gray-600 mb-2">
                                      위험도: {part.risk_score?.toFixed(1)}/5.0
                                    </div>
                                    {/* 위험 조항 미리보기 */}
                                    {(part.risk_clauses ||
                                      part.relevant_clauses) &&
                                      (
                                        part.risk_clauses ||
                                        part.relevant_clauses
                                      ).length > 0 && (
                                        <div className="mt-2">
                                          <div className="text-xs text-red-600 font-medium mb-1">
                                            관련 조항 (
                                            {
                                              (
                                                part.risk_clauses ||
                                                part.relevant_clauses
                                              ).length
                                            }
                                            개):
                                          </div>
                                          <div className="space-y-1">
                                            {(
                                              part.risk_clauses ||
                                              part.relevant_clauses
                                            )
                                              .slice(0, 2)
                                              .map((clause, clauseIndex) => (
                                                <div
                                                  key={clauseIndex}
                                                  className="text-xs text-red-700 bg-red-50 p-2 rounded"
                                                >
                                                  • {clause}
                                                </div>
                                              ))}
                                            {(
                                              part.risk_clauses ||
                                              part.relevant_clauses
                                            ).length > 2 && (
                                              <div className="text-xs text-gray-500">
                                                ... 외{" "}
                                                {(
                                                  part.risk_clauses ||
                                                  part.relevant_clauses
                                                ).length - 2}
                                                개
                                              </div>
                                            )}
                                          </div>
                                        </div>
                                      )}
                                  </div>
                                ))}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <Card>
                    <CardContent className="p-6 text-center">
                      <Database className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                      <p className="text-sm font-medium mb-1">
                        하이브리드 분석 결과가 없습니다
                      </p>
                      <p className="text-xs text-gray-500">
                        RAG 시스템을 통한 분석 결과가 여기에 표시됩니다.
                      </p>
                    </CardContent>
                  </Card>
                )}
              </div>

              {/* OpenAI GPT만 사용한 결과물 */}
              <div className="space-y-4">
                <div className="flex items-center space-x-2 mb-4">
                  <Shield className="h-5 w-5 text-green-600" />
                  <h3 className="text-lg font-semibold text-gray-900">
                    GPT 전용 분석 결과
                  </h3>
                  <Badge
                    variant="default"
                    className="bg-green-100 text-green-800"
                  >
                    GPT Only
                  </Badge>
                </div>

                {gptAnalysisResults.length > 0 ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="font-medium text-sm">GPT 분석 결과</h4>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleGptAnalysis}
                        disabled={!selectedContract || isGptAnalyzing}
                        className="text-xs"
                      >
                        {isGptAnalyzing ? (
                          <>
                            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-gray-600 mr-2"></div>
                            분석 중...
                          </>
                        ) : (
                          "새로 분석하기"
                        )}
                      </Button>
                    </div>
                    {gptAnalysisResults.map((result, index) => (
                      <Card key={result.analysis_id || index}>
                        <CardHeader>
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-base">
                              {result.contract_name}
                            </CardTitle>
                            <Badge variant="outline">
                              {new Date(result.created_at).toLocaleDateString()}
                            </Badge>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-3">
                            <div className="grid grid-cols-2 gap-3">
                              <div className="text-center">
                                <div className="text-xl font-bold text-red-600">
                                  {result.analysis_result?.overall_risk_score?.toFixed(
                                    1
                                  ) || "N/A"}
                                </div>
                                <div className="text-xs text-gray-600">
                                  전체 위험도
                                </div>
                              </div>
                              <div className="text-center">
                                <div className="text-xl font-bold text-blue-600">
                                  {result.analysis_result?.part_results
                                    ?.length || 0}
                                </div>
                                <div className="text-xs text-gray-600">
                                  분석 파트
                                </div>
                              </div>
                            </div>

                            <div className="space-y-2">
                              <div className="flex items-center justify-between">
                                <h4 className="font-medium text-sm">
                                  GPT 분석 결과
                                </h4>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="text-xs h-6 px-2"
                                  onClick={() =>
                                    setShowGptAnalysisDetails(true)
                                  }
                                >
                                  상세 보기
                                </Button>
                              </div>
                              {result.analysis_result?.part_results
                                ?.slice(0, 2)
                                .map((part, partIndex: number) => (
                                  <div
                                    key={partIndex}
                                    className="border rounded-lg p-3"
                                  >
                                    <div className="flex items-center justify-between mb-2">
                                      <h5 className="font-medium text-sm">
                                        {part.part_title}
                                      </h5>
                                      <Badge
                                        variant={
                                          part.risk_level === "CRITICAL"
                                            ? "destructive"
                                            : part.risk_level === "HIGH"
                                            ? "destructive"
                                            : part.risk_level === "MEDIUM"
                                            ? "secondary"
                                            : "outline"
                                        }
                                        className="text-xs"
                                      >
                                        {part.risk_level}
                                      </Badge>
                                    </div>
                                    <div className="text-xs text-gray-600 mb-2">
                                      위험도: {part.risk_score?.toFixed(1)}/5.0
                                    </div>
                                  </div>
                                ))}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <Card>
                    <CardContent className="p-6 text-center">
                      <Shield className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                      <p className="text-sm font-medium mb-1">
                        GPT 전용 분석 결과가 없습니다
                      </p>
                      <p className="text-xs text-gray-500">
                        OpenAI GPT만을 사용한 분석 결과가 여기에 표시됩니다.
                      </p>
                      <Button
                        variant="outline"
                        size="sm"
                        className="mt-3"
                        onClick={handleGptAnalysis}
                        disabled={!selectedContract || isGptAnalyzing}
                      >
                        {isGptAnalyzing ? (
                          <>
                            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-gray-600 mr-2"></div>
                            분석 중...
                          </>
                        ) : (
                          "GPT 분석 시작"
                        )}
                      </Button>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="rag-risk" className="space-y-6">
            <RagRiskAnalysis
              onAnalysisComplete={(result) => {
                // RAG 분석 완료 시 위험 분석 결과에 추가
                setRiskAnalysisResults((prev) => [result, ...prev]);
                toast({
                  title: "RAG 하이브리드 분석 완료",
                  description:
                    "하이브리드 검색을 통한 위험 분석이 완료되었습니다.",
                });
              }}
            />
          </TabsContent>

          <TabsContent value="chat" className="space-y-4">
            {contracts.length > 0 && (
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <label className="text-sm font-medium text-gray-700">
                    계약서 선택:
                  </label>
                  <select
                    value={selectedContract}
                    onChange={(e) => setSelectedContract(e.target.value)}
                    className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {contracts.map((contract) => (
                      <option key={contract.id} value={contract.id}>
                        {contract.fileName}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}
            <ChatInterface
              contractId={selectedContract}
              messages={chatMessages}
              onSendMessage={handleSendMessage}
              onClearHistory={handleClearChatHistory}
            />
          </TabsContent>

          <TabsContent value="comparison" className="space-y-4">
            {contracts.length > 0 && (
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <label className="text-sm font-medium text-gray-700">
                    계약서 선택:
                  </label>
                  <select
                    value={selectedContract}
                    onChange={(e) => setSelectedContract(e.target.value)}
                    className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {contracts.map((contract) => (
                      <option key={contract.id} value={contract.id}>
                        {contract.fileName}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}
            <ComparisonChatInterface
              contractId={selectedContract}
              messages={chatMessages}
              onSendMessage={handleSendMessage}
              onClearHistory={handleClearChatHistory}
            />
          </TabsContent>
        </Tabs>

        {/* 위험 분석 상세 보기 모달 */}
        {showRiskAnalysisDetails && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full mx-4 max-h-[90vh] overflow-hidden">
              <div className="flex items-center justify-between p-6 border-b">
                <h2 className="text-xl font-semibold">
                  하이브리드 분석 상세 결과
                </h2>
                <Button
                  variant="outline"
                  onClick={() => setShowRiskAnalysisDetails(false)}
                >
                  닫기
                </Button>
              </div>
              <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
                <RiskAnalysisResults />
              </div>
            </div>
          </div>
        )}

        {/* GPT 분석 상세 보기 모달 */}
        {showGptAnalysisDetails && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full mx-4 max-h-[90vh] overflow-hidden">
              <div className="flex items-center justify-between p-6 border-b">
                <h2 className="text-xl font-semibold">GPT 분석 상세 결과</h2>
                <Button
                  variant="outline"
                  onClick={() => setShowGptAnalysisDetails(false)}
                >
                  닫기
                </Button>
              </div>
              <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
                {gptAnalysisResults.length > 0 ? (
                  <div className="space-y-6">
                    {gptAnalysisResults.map((result, index) => (
                      <Card key={result.analysis_id || index}>
                        <CardHeader>
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-lg">
                              {result.contract_name}
                            </CardTitle>
                            <Badge variant="outline">
                              {new Date(result.created_at).toLocaleDateString()}
                            </Badge>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                              <div className="text-center">
                                <div className="text-2xl font-bold text-red-600">
                                  {result.analysis_result?.overall_risk_score?.toFixed(
                                    1
                                  ) || "N/A"}
                                </div>
                                <div className="text-sm text-gray-600">
                                  전체 위험도
                                </div>
                              </div>
                              <div className="text-center">
                                <div className="text-2xl font-bold text-blue-600">
                                  {result.analysis_result?.part_results
                                    ?.length || 0}
                                </div>
                                <div className="text-sm text-gray-600">
                                  분석 파트
                                </div>
                              </div>
                              <div className="text-center">
                                <div className="text-2xl font-bold text-green-600">
                                  {result.analysis_result?.total_analysis_time?.toFixed(
                                    1
                                  ) || "N/A"}
                                  초
                                </div>
                                <div className="text-sm text-gray-600">
                                  분석 시간
                                </div>
                              </div>
                            </div>

                            <div className="space-y-3">
                              <h4 className="font-semibold">
                                GPT 분석 상세 결과
                              </h4>
                              {result.analysis_result?.part_results?.map(
                                (part, partIndex: number) => (
                                  <div
                                    key={partIndex}
                                    className="border rounded-lg p-4"
                                  >
                                    <div className="flex items-center justify-between mb-2">
                                      <h5 className="font-medium">
                                        {part.part_title}
                                      </h5>
                                      <Badge
                                        variant={
                                          part.risk_level === "CRITICAL"
                                            ? "destructive"
                                            : part.risk_level === "HIGH"
                                            ? "destructive"
                                            : part.risk_level === "MEDIUM"
                                            ? "secondary"
                                            : "outline"
                                        }
                                      >
                                        {part.risk_level}
                                      </Badge>
                                    </div>
                                    <div className="text-sm text-gray-600 mb-2">
                                      위험도: {part.risk_score?.toFixed(1)}/5.0
                                    </div>
                                    {(part.risk_clauses ||
                                      part.relevant_clauses) &&
                                      (
                                        part.risk_clauses ||
                                        part.relevant_clauses
                                      ).length > 0 && (
                                        <div className="mt-2">
                                          <h6 className="font-medium text-sm mb-1">
                                            위험 조항:
                                          </h6>
                                          <ul className="text-sm text-gray-600 space-y-1">
                                            {(
                                              part.risk_clauses ||
                                              part.relevant_clauses
                                            ).map(
                                              (
                                                clause: string,
                                                clauseIndex: number
                                              ) => (
                                                <li
                                                  key={clauseIndex}
                                                  className="flex items-start"
                                                >
                                                  <span className="mr-2">
                                                    •
                                                  </span>
                                                  <span>{clause}</span>
                                                </li>
                                              )
                                            )}
                                          </ul>
                                        </div>
                                      )}
                                    {part.recommendations &&
                                      part.recommendations.length > 0 && (
                                        <div className="mt-2">
                                          <h6 className="font-medium text-sm mb-1">
                                            권고사항:
                                          </h6>
                                          <ul className="text-sm text-gray-600 space-y-1">
                                            {part.recommendations.map(
                                              (
                                                rec: string,
                                                recIndex: number
                                              ) => (
                                                <li
                                                  key={recIndex}
                                                  className="flex items-start"
                                                >
                                                  <span className="mr-2">
                                                    •
                                                  </span>
                                                  <span>{rec}</span>
                                                </li>
                                              )
                                            )}
                                          </ul>
                                        </div>
                                      )}
                                    {"analysis_content" in part &&
                                      part.analysis_content && (
                                        <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                                          <h6 className="font-medium text-sm mb-2">
                                            GPT 분석 내용:
                                          </h6>
                                          <div className="text-sm text-gray-700 whitespace-pre-wrap">
                                            {String(part.analysis_content)}
                                          </div>
                                        </div>
                                      )}
                                  </div>
                                )
                              )}
                            </div>

                            {result.analysis_result?.summary && (
                              <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                                <h4 className="font-semibold mb-2">
                                  분석 요약
                                </h4>
                                <div className="text-sm text-gray-600">
                                  <p>
                                    총{" "}
                                    {
                                      result.analysis_result.summary
                                        .total_parts_analyzed
                                    }
                                    개 파트 분석
                                  </p>
                                  <p>
                                    고위험 파트:{" "}
                                    {
                                      result.analysis_result.summary
                                        .high_risk_parts
                                    }
                                    개
                                  </p>
                                  {result.analysis_result.summary
                                    .critical_issues &&
                                    result.analysis_result.summary
                                      .critical_issues.length > 0 && (
                                      <p className="text-red-600 font-medium">
                                        중요 이슈:{" "}
                                        {result.analysis_result.summary.critical_issues.join(
                                          ", "
                                        )}
                                      </p>
                                    )}
                                  {"gpt_analysis" in
                                    result.analysis_result.summary &&
                                    result.analysis_result.summary
                                      .gpt_analysis && (
                                      <div className="mt-3 p-3 bg-blue-50 rounded-lg">
                                        <h5 className="font-medium text-sm mb-2">
                                          GPT 전체 분석:
                                        </h5>
                                        <div className="text-sm text-gray-700 whitespace-pre-wrap">
                                          {String(
                                            result.analysis_result.summary
                                              .gpt_analysis
                                          )}
                                        </div>
                                      </div>
                                    )}
                                </div>
                              </div>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Shield className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                    <p className="text-lg font-medium mb-2">
                      GPT 분석 결과가 없습니다
                    </p>
                    <p className="text-sm text-gray-500">
                      GPT 분석을 먼저 실행해주세요.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
