import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Shield,
  Database,
  Search,
  FileText,
  AlertTriangle,
  CheckCircle,
} from "lucide-react";
import { api } from "@/services/api";
import { useToast } from "@/hooks/use-toast";

interface RagContract {
  file_id: string;
  filename: string;
  uploaded_at: string;
  file_size: number;
  file_type: string;
}

interface RagRiskAnalysisProps {
  onAnalysisComplete?: (result: any) => void;
}

const RagRiskAnalysis: React.FC<RagRiskAnalysisProps> = ({
  onAnalysisComplete,
}) => {
  const [ragContracts, setRagContracts] = useState<RagContract[]>([]);
  const [selectedContract, setSelectedContract] = useState<string>("");
  const [selectedParts, setSelectedParts] = useState("all");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [isLoadingContracts, setIsLoadingContracts] = useState(false);
  const { toast } = useToast();

  const partOptions = [
    { value: "all", label: "전체 파트 (1-10)" },
    { value: "1", label: "1. 거래의 기본 골격" },
    { value: "2", label: "2. 거래 대상 자산의 정의 및 소유권" },
    { value: "3", label: "3. 거래대금 산정 및 지급 메커니즘" },
    { value: "4", label: "4. 재무 상태 및 부채에 관한 진술 및 보장" },
    { value: "5", label: "5. 영업, 자산 및 법규 준수에 관한 진술 및 보장" },
    { value: "6", label: "6. 계약 체결 후 종결까지의 운영" },
    { value: "7", label: "7. 계약 위반 시 구제수단 및 손해배상" },
    { value: "8", label: "8. 계약의 종료, 해제 및 위약금" },
    { value: "9", label: "9. 거래종결 후 의무 및 제한사항" },
    { value: "10", label: "10. 분쟁 해결 및 계약 해석 원칙" },
  ];

  // RAG 계약서 목록 로드
  const fetchRagContracts = async () => {
    setIsLoadingContracts(true);
    try {
      const response = await api.getRagContracts();
      if (response.success) {
        setRagContracts(response.data);
        if (response.data.length > 0 && !selectedContract) {
          setSelectedContract(response.data[0].file_id);
        }
      } else {
        throw new Error(response.message || "RAG 계약서 목록 조회 실패");
      }
    } catch (error) {
      console.error("RAG 계약서 목록 조회 실패:", error);
      toast({
        title: "조회 실패",
        description:
          error instanceof Error
            ? error.message
            : "RAG 계약서 목록을 불러올 수 없습니다.",
        variant: "destructive",
      });
    } finally {
      setIsLoadingContracts(false);
    }
  };

  useEffect(() => {
    fetchRagContracts();
  }, []);

  const handleAnalyze = async () => {
    if (!selectedContract) {
      toast({
        title: "선택 오류",
        description: "분석할 계약서를 선택해주세요.",
        variant: "destructive",
      });
      return;
    }

    setIsAnalyzing(true);
    try {
      const response = await api.analyzeUploadedFileRisk(
        selectedContract,
        selectedParts
      );

      if (response.success) {
        setAnalysisResult(response.data.analysis_result);
        onAnalysisComplete?.(response.data);
        toast({
          title: "RAG 위험 분석 완료",
          description: "하이브리드 검색을 통한 위험 분석이 완료되었습니다.",
        });
      } else {
        throw new Error(response.message || "분석 실패");
      }
    } catch (error) {
      console.error("RAG 위험 분석 실패:", error);
      toast({
        title: "분석 실패",
        description:
          error instanceof Error
            ? error.message
            : "RAG 위험 분석 중 오류가 발생했습니다.",
        variant: "destructive",
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getRiskLevelBadgeVariant = (level: string) => {
    switch (level) {
      case "CRITICAL":
      case "HIGH":
        return "destructive";
      case "MEDIUM":
        return "secondary";
      default:
        return "outline";
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Database className="h-5 w-5" />
            <span>RAG 기반 하이브리드 위험 분석</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* RAG 계약서 선택 */}
          <div>
            <label className="block text-sm font-medium mb-2">
              RAG 구축된 계약서 선택
            </label>
            {isLoadingContracts ? (
              <div className="p-4 text-center text-gray-500">
                RAG 계약서 목록을 불러오는 중...
              </div>
            ) : ragContracts.length === 0 ? (
              <div className="p-4 text-center text-gray-500 border rounded-lg">
                <Database className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                <p>RAG가 구축된 계약서가 없습니다.</p>
                <p className="text-sm">
                  파일을 업로드하고 파이프라인을 실행해주세요.
                </p>
              </div>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {ragContracts.map((contract) => (
                  <div
                    key={contract.file_id}
                    className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                      selectedContract === contract.file_id
                        ? "border-blue-500 bg-blue-50"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                    onClick={() => setSelectedContract(contract.file_id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="font-medium text-sm">
                          {contract.filename}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {formatFileSize(contract.file_size)} •{" "}
                          {formatDate(contract.uploaded_at)}
                        </div>
                      </div>
                      {selectedContract === contract.file_id && (
                        <CheckCircle className="h-5 w-5 text-blue-500" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 분석 파트 선택 */}
          <div>
            <label className="block text-sm font-medium mb-2">
              분석할 파트 선택
            </label>
            <select
              value={selectedParts}
              onChange={(e) => setSelectedParts(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md"
            >
              {partOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* 분석 시작 버튼 */}
          <Button
            onClick={handleAnalyze}
            disabled={
              isAnalyzing || !selectedContract || ragContracts.length === 0
            }
            className="w-full"
          >
            {isAnalyzing ? (
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>하이브리드 분석 중...</span>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <Search className="h-4 w-4" />
                <span>RAG 하이브리드 위험 분석 시작</span>
              </div>
            )}
          </Button>

          {/* RAG 시스템 정보 */}
          {ragContracts.length > 0 && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center space-x-2 text-green-700">
                <CheckCircle className="h-4 w-4" />
                <span className="text-sm font-medium">
                  RAG 시스템이 활성화되어 하이브리드 검색이 가능합니다
                </span>
              </div>
              <p className="text-xs text-green-600 mt-1">
                • Concept extraction • Neo4j 검색 • HiPPO-RAG2 • Re-ranking
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 분석 결과 */}
      {analysisResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <FileText className="h-5 w-5" />
              <span>하이브리드 분석 결과</span>
              <Badge variant="outline" className="ml-auto">
                RAG 하이브리드
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* 전체 위험도 요약 */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">
                    {analysisResult.overall_risk_score?.toFixed(1) || "N/A"}
                  </div>
                  <div className="text-sm text-gray-600">전체 위험도</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {analysisResult.part_results?.length || 0}
                  </div>
                  <div className="text-sm text-gray-600">분석 파트</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {analysisResult.total_analysis_time?.toFixed(1) || "N/A"}초
                  </div>
                  <div className="text-sm text-gray-600">분석 시간</div>
                </div>
              </div>

              {/* 파트별 분석 결과 */}
              <div className="space-y-4">
                <h4 className="font-semibold text-lg">파트별 위험 분석</h4>
                {analysisResult.part_results?.map(
                  (part: any, index: number) => (
                    <div key={index} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h5 className="font-medium">{part.part_title}</h5>
                        <Badge
                          variant={getRiskLevelBadgeVariant(part.risk_level)}
                        >
                          {part.risk_level}
                        </Badge>
                      </div>
                      <div className="text-sm text-gray-600 mb-2">
                        위험도: {part.risk_score?.toFixed(1)}/5.0
                      </div>
                      {part.recommendations &&
                        part.recommendations.length > 0 && (
                          <div className="mt-2">
                            <h6 className="font-medium text-sm mb-1">
                              권고사항:
                            </h6>
                            <ul className="text-sm text-gray-600 space-y-1">
                              {part.recommendations
                                .slice(0, 3)
                                .map((rec: string, recIndex: number) => (
                                  <li
                                    key={recIndex}
                                    className="flex items-start"
                                  >
                                    <span className="mr-2">•</span>
                                    <span>{rec}</span>
                                  </li>
                                ))}
                            </ul>
                          </div>
                        )}
                    </div>
                  )
                )}
              </div>

              {/* 분석 요약 */}
              {analysisResult.summary && (
                <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                  <h4 className="font-semibold mb-2">분석 요약</h4>
                  <div className="text-sm text-gray-600">
                    <p>
                      총 {analysisResult.summary.total_parts_analyzed}개 파트
                      분석
                    </p>
                    <p>
                      고위험 파트: {analysisResult.summary.high_risk_parts}개
                    </p>
                    {analysisResult.summary.critical_issues &&
                      analysisResult.summary.critical_issues.length > 0 && (
                        <p className="text-red-600 font-medium">
                          중요 이슈:{" "}
                          {analysisResult.summary.critical_issues.join(", ")}
                        </p>
                      )}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default RagRiskAnalysis;
