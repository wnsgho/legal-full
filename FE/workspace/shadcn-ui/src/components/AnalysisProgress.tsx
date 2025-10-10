import React, { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { CheckCircle, AlertCircle } from "lucide-react";
import { AnalysisResult, AnalysisStatus, RiskLevel } from "@/types";
import { api } from "@/services/api";
import { useToast } from "@/hooks/use-toast";

interface AnalysisProgressProps {
  currentAnalysis?: {
    id: string;
    progress: number;
    stage: string;
  };
  pipelineId?: string;
  contractId?: string; // 계약서 ID 추가
  onAnalysisComplete?: (result: AnalysisResult) => void;
}

const AnalysisProgress: React.FC<AnalysisProgressProps> = ({
  currentAnalysis,
  pipelineId,
  contractId,
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
    if (!pipelineId) {
      console.log(
        "🔍 AnalysisProgress: pipelineId가 없어서 폴링을 시작하지 않습니다."
      );
      return;
    }

    console.log(
      `🔍 AnalysisProgress: 파이프라인 상태 폴링 시작 - ID: ${pipelineId}`
    );

    const pollInterval = setInterval(async () => {
      try {
        console.log(`🔍 파이프라인 상태 확인 중 - ID: ${pipelineId}`);
        const response = await api.getPipelineStatus(pipelineId);
        console.log(`🔍 파이프라인 상태 응답:`, response);

        if (response.success) {
          const newStatus = {
            status: response.status,
            progress: response.progress,
            message: response.message,
          };

          console.log(`🔍 파이프라인 상태 업데이트:`, newStatus);
          setPipelineStatus(newStatus);

          // 파이프라인 완료 시
          if (response.status === "completed") {
            console.log(`✅ 파이프라인 완료 감지 - ID: ${pipelineId}`);
            clearInterval(pollInterval);

            // 즉시 완료 상태로 업데이트
            setPipelineStatus({
              status: "completed",
              progress: 100,
              message:
                "✅ 파이프라인 실행이 성공적으로 완료되었습니다. RAG 시스템이 준비되었습니다.",
            });

            toast({
              title: "✅ 분석 완료",
              description:
                "계약서 분석이 성공적으로 완료되었습니다. 이제 질문을 할 수 있습니다.",
            });

            // 분석 완료 콜백 호출
            if (onAnalysisComplete) {
              const mockResult: AnalysisResult = {
                id: pipelineId,
                contractId: contractId || pipelineId, // contractId 사용, 없으면 pipelineId 사용
                status: AnalysisStatus.COMPLETED,
                riskLevel: RiskLevel.MEDIUM,
                riskClauses: [],
                summary:
                  "파이프라인 분석이 완료되었습니다. RAG 시스템이 준비되었습니다.",
                recommendations: [],
                aiModel: "GPT-4",
                confidence: 0.9,
                createdAt: new Date(),
                processingTimeMs: 30000,
              };
              onAnalysisComplete(mockResult);
            }
          } else if (response.status === "failed") {
            console.log(`❌ 파이프라인 실패 감지 - ID: ${pipelineId}`);
            clearInterval(pollInterval);

            // 즉시 실패 상태로 업데이트
            setPipelineStatus({
              status: "failed",
              progress: 0,
              message:
                "❌ 파이프라인 실행이 실패했습니다. 로그를 확인하고 다시 시도해주세요.",
            });

            toast({
              title: "❌ 분석 실패",
              description:
                "파이프라인 실행 중 오류가 발생했습니다. 다시 시도해주세요.",
              variant: "destructive",
            });
          }
        }
      } catch (error: unknown) {
        console.error("Pipeline status polling error:", error);

        // 404 오류 시 폴링 중단 (서버 재시작 등으로 파이프라인 ID가 없어진 경우)
        if (
          (error as { response?: { status?: number }; message?: string })
            ?.response?.status === 404 ||
          (
            error as { response?: { status?: number }; message?: string }
          )?.message?.includes("404")
        ) {
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
    }, 1000); // 1초마다 폴링 (더 빠른 반응)

    return () => {
      console.log(
        `🔍 AnalysisProgress: 파이프라인 상태 폴링 중단 - ID: ${pipelineId}`
      );
      clearInterval(pollInterval);
    };
  }, [pipelineId, onAnalysisComplete, toast]);

  // 현재 분석 상태 업데이트
  const currentAnalysisStatus = pipelineStatus || currentAnalysis;

  return (
    <div className="space-y-6">
      {/* Current Analysis Progress */}
      {currentAnalysisStatus && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              {pipelineStatus?.status === "completed" ? (
                <CheckCircle className="h-4 w-4 text-green-500" />
              ) : pipelineStatus?.status === "failed" ? (
                <AlertCircle className="h-4 w-4 text-red-500" />
              ) : (
                <div className="h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              )}
              <span>
                {pipelineStatus?.status === "completed"
                  ? "✅ 분석 완료"
                  : pipelineStatus?.status === "failed"
                  ? "❌ 분석 실패"
                  : "분석 진행 중"}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>
                    {"message" in currentAnalysisStatus
                      ? currentAnalysisStatus.message
                      : currentAnalysisStatus.stage}
                  </span>
                  <span>{currentAnalysisStatus.progress}%</span>
                </div>
                <Progress
                  value={currentAnalysisStatus.progress}
                  className="h-2"
                />
              </div>
              <div className="text-sm text-gray-600">
                {pipelineStatus?.status === "completed"
                  ? "🎉 계약서 분석이 완료되었습니다! 이제 챗봇을 사용하여 질문할 수 있습니다."
                  : pipelineStatus?.status === "failed"
                  ? "❌ 분석 중 오류가 발생했습니다. 다시 시도해주세요."
                  : "AI가 계약서를 분석하고 있습니다. 잠시만 기다려주세요."}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AnalysisProgress;
