import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Shield, FileText, AlertTriangle, CheckCircle } from "lucide-react";
import { api } from "@/services/api";
import { useToast } from "@/hooks/use-toast";

interface StandaloneRiskAnalysisProps {
  onAnalysisComplete?: (result: any) => void;
}

const StandaloneRiskAnalysis: React.FC<StandaloneRiskAnalysisProps> = ({
  onAnalysisComplete,
}) => {
  const [contractText, setContractText] = useState("");
  const [contractName, setContractName] = useState("");
  const [selectedParts, setSelectedParts] = useState("all");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
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

  const handleAnalyze = async () => {
    if (!contractText.trim()) {
      toast({
        title: "입력 오류",
        description: "계약서 내용을 입력해주세요.",
        variant: "destructive",
      });
      return;
    }

    setIsAnalyzing(true);
    try {
      const response = await api.analyzeContractRisk(
        contractText,
        contractName || "계약서",
        selectedParts
      );

      if (response.success) {
        setAnalysisResult(response.data.analysis_result);
        onAnalysisComplete?.(response.data);
        toast({
          title: "위험 분석 완료",
          description: "계약서 위험 분석이 완료되었습니다.",
        });
      } else {
        throw new Error(response.message || "분석 실패");
      }
    } catch (error) {
      console.error("위험 분석 실패:", error);
      toast({
        title: "분석 실패",
        description:
          error instanceof Error
            ? error.message
            : "위험 분석 중 오류가 발생했습니다.",
        variant: "destructive",
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case "CRITICAL":
        return "bg-red-500";
      case "HIGH":
        return "bg-orange-500";
      case "MEDIUM":
        return "bg-yellow-500";
      case "LOW":
        return "bg-green-500";
      default:
        return "bg-gray-500";
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

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Shield className="h-5 w-5" />
            <span>독립적인 위험 분석</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="contract-name">계약서명</Label>
            <Input
              id="contract-name"
              value={contractName}
              onChange={(e) => setContractName(e.target.value)}
              placeholder="계약서명을 입력하세요"
              className="mt-1"
            />
          </div>

          <div>
            <Label htmlFor="contract-text">계약서 내용</Label>
            <Textarea
              id="contract-text"
              value={contractText}
              onChange={(e) => setContractText(e.target.value)}
              placeholder="계약서 내용을 입력하세요..."
              className="mt-1 min-h-[200px]"
            />
          </div>

          <div>
            <Label htmlFor="selected-parts">분석할 파트 선택</Label>
            <select
              id="selected-parts"
              value={selectedParts}
              onChange={(e) => setSelectedParts(e.target.value)}
              className="mt-1 w-full p-2 border border-gray-300 rounded-md"
            >
              {partOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <Button
            onClick={handleAnalyze}
            disabled={isAnalyzing || !contractText.trim()}
            className="w-full"
          >
            {isAnalyzing ? "분석 중..." : "위험 분석 시작"}
          </Button>
        </CardContent>
      </Card>

      {analysisResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <FileText className="h-5 w-5" />
              <span>분석 결과</span>
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

export default StandaloneRiskAnalysis;
