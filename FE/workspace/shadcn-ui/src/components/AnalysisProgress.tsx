import React, { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Clock, CheckCircle, AlertCircle, RefreshCw, Eye } from "lucide-react";
import { AnalysisResult, AnalysisStatus, RiskLevel } from "@/types";
import { api } from "@/services/api";
import { useToast } from "@/hooks/use-toast";

interface AnalysisProgressProps {
  analysisResults: AnalysisResult[];
  onRetryAnalysis: (analysisId: string) => void;
  onViewResult: (analysisId: string) => void;
  currentAnalysis?: {
    id: string;
    progress: number;
    stage: string;
  };
  pipelineId?: string;
  onAnalysisComplete?: (result: AnalysisResult) => void;
}

const AnalysisProgress: React.FC<AnalysisProgressProps> = ({
  analysisResults,
  onRetryAnalysis,
  onViewResult,
  currentAnalysis,
  pipelineId,
  onAnalysisComplete,
}) => {
  const [pipelineStatus, setPipelineStatus] = useState<{
    status: string;
    progress: number;
    message: string;
  } | null>(null);
  const { toast } = useToast();

  // 파이프라인 상태 폴링
  useEffect(() => {
    if (!pipelineId) return;

    const pollInterval = setInterval(async () => {
      try {
        const response = await api.getPipelineStatus(pipelineId);
        if (response.success && response.data) {
          setPipelineStatus({
            status: response.data.status,
            progress: response.data.progress,
            message: response.data.message,
          });

          // 파이프라인 완료 시
          if (response.data.status === "completed") {
            clearInterval(pollInterval);
            toast({
              title: "분석 완료",
              description: "계약서 분석이 완료되었습니다.",
            });

            // 분석 완료 콜백 호출
            if (onAnalysisComplete) {
              const mockResult: AnalysisResult = {
                id: pipelineId,
                contractId: pipelineId,
                status: AnalysisStatus.COMPLETED,
                riskLevel: RiskLevel.MEDIUM,
                riskClauses: [],
                summary: "파이프라인 분석이 완료되었습니다.",
                recommendations: [],
                aiModel: "GPT-4",
                confidence: 0.9,
                createdAt: new Date(),
                processingTimeMs: 30000,
              };
              onAnalysisComplete(mockResult);
            }
          } else if (response.data.status === "failed") {
            clearInterval(pollInterval);
            toast({
              title: "분석 실패",
              description: "파이프라인 실행 중 오류가 발생했습니다.",
              variant: "destructive",
            });
          }
        }
      } catch (error: any) {
        console.error("Pipeline status polling error:", error);

        // 404 오류 시 폴링 중단 (서버 재시작 등으로 파이프라인 ID가 없어진 경우)
        if (error.response?.status === 404 || error.message?.includes("404")) {
          console.warn(`Pipeline ${pipelineId} not found, stopping polling`);
          clearInterval(pollInterval);
          setPipelineStatus(null);
          toast({
            title: "파이프라인 상태 확인 불가",
            description: "서버가 재시작되었거나 파이프라인이 만료되었습니다.",
            variant: "destructive",
          });
        }
      }
    }, 2000); // 2초마다 폴링

    return () => clearInterval(pollInterval);
  }, [pipelineId, onAnalysisComplete, toast]);

  // 현재 분석 상태 업데이트
  const currentAnalysisStatus = pipelineStatus || currentAnalysis;
  const getStatusIcon = (status: AnalysisStatus) => {
    switch (status) {
      case AnalysisStatus.COMPLETED:
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case AnalysisStatus.IN_PROGRESS:
        return (
          <div className="h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        );
      case AnalysisStatus.FAILED:
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: AnalysisStatus) => {
    const variants = {
      [AnalysisStatus.COMPLETED]: "default",
      [AnalysisStatus.IN_PROGRESS]: "secondary",
      [AnalysisStatus.PENDING]: "outline",
      [AnalysisStatus.FAILED]: "destructive",
    } as const;

    const labels = {
      [AnalysisStatus.COMPLETED]: "완료",
      [AnalysisStatus.IN_PROGRESS]: "분석중",
      [AnalysisStatus.PENDING]: "대기중",
      [AnalysisStatus.FAILED]: "실패",
    };

    return <Badge variant={variants[status]}>{labels[status]}</Badge>;
  };

  const getRiskLevelBadge = (riskLevel: RiskLevel) => {
    const colors = {
      [RiskLevel.LOW]: "bg-green-100 text-green-800",
      [RiskLevel.MEDIUM]: "bg-yellow-100 text-yellow-800",
      [RiskLevel.HIGH]: "bg-orange-100 text-orange-800",
      [RiskLevel.CRITICAL]: "bg-red-100 text-red-800",
    };

    const labels = {
      [RiskLevel.LOW]: "낮음",
      [RiskLevel.MEDIUM]: "보통",
      [RiskLevel.HIGH]: "높음",
      [RiskLevel.CRITICAL]: "매우 높음",
    };

    return <Badge className={colors[riskLevel]}>{labels[riskLevel]}</Badge>;
  };

  const formatProcessingTime = (timeMs?: number) => {
    if (!timeMs) return "-";
    const seconds = Math.floor(timeMs / 1000);
    return `${seconds}초`;
  };

  return (
    <div className="space-y-6">
      {/* Current Analysis Progress */}
      {currentAnalysisStatus && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <div className="h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span>분석 진행 중</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>
                    {currentAnalysisStatus.message ||
                      currentAnalysisStatus.stage}
                  </span>
                  <span>{currentAnalysisStatus.progress}%</span>
                </div>
                <Progress
                  value={currentAnalysisStatus.progress}
                  className="h-2"
                />
              </div>
              <div className="text-sm text-gray-600">
                AI가 계약서를 분석하고 있습니다. 잠시만 기다려주세요.
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Analysis Results */}
      <Card>
        <CardHeader>
          <CardTitle>분석 결과</CardTitle>
        </CardHeader>
        <CardContent>
          {analysisResults.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Clock className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>아직 분석된 계약서가 없습니다.</p>
              <p className="text-sm">
                계약서를 업로드하고 분석을 시작해보세요.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {analysisResults.map((result) => (
                <div
                  key={result.id}
                  className="border rounded-lg p-4 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(result.status)}
                      <div>
                        <p className="font-medium">
                          분석 #{result.id.slice(-6)}
                        </p>
                        <p className="text-sm text-gray-500">
                          {result.createdAt.toLocaleDateString("ko-KR")}{" "}
                          {result.createdAt.toLocaleTimeString("ko-KR")}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {getStatusBadge(result.status)}
                      {result.status === AnalysisStatus.COMPLETED &&
                        getRiskLevelBadge(result.riskLevel)}
                    </div>
                  </div>

                  {result.status === AnalysisStatus.COMPLETED && (
                    <div className="bg-gray-50 rounded-lg p-3 space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">위험 조항</span>
                        <span className="font-medium">
                          {result.riskClauses.length}개 발견
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">신뢰도</span>
                        <span className="font-medium">
                          {Math.round(result.confidence * 100)}%
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">처리 시간</span>
                        <span className="font-medium">
                          {formatProcessingTime(result.processingTimeMs)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">AI 모델</span>
                        <span className="font-medium">{result.aiModel}</span>
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-2">
                    <div className="text-sm text-gray-500">
                      {result.status === AnalysisStatus.COMPLETED &&
                        result.summary && (
                          <p className="line-clamp-2">{result.summary}</p>
                        )}
                    </div>
                    <div className="flex space-x-2">
                      {result.status === AnalysisStatus.FAILED && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onRetryAnalysis(result.id)}
                        >
                          <RefreshCw className="h-4 w-4 mr-1" />
                          재시도
                        </Button>
                      )}
                      {result.status === AnalysisStatus.COMPLETED && (
                        <Button
                          variant="default"
                          size="sm"
                          onClick={() => onViewResult(result.id)}
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          상세 보기
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AnalysisProgress;
