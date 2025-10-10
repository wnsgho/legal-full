import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { api } from "@/services/api";

interface RiskAnalysisResult {
  analysis_id: string;
  file_based_id: string;
  file_id: string;
  contract_name: string;
  analysis_result: {
    overall_risk_score: number;
    overall_risk_level: string;
    part_results: Array<{
      part_number: number;
      part_title: string;
      risk_score: number;
      risk_level: string;
      checklist_results: Array<{
        item: string;
        status: string;
        risk_level: string;
        risk_score: number;
        analysis: string;
        recommendation: string;
        explanation?: string;
      }>;
      relevant_clauses: string[];
      risk_clauses: string[];
      recommendations: string[];
    }>;
  };
  created_at: string;
}

interface RiskAnalysisResultsProps {
  fileId?: string;
  onClose?: () => void;
}

const RiskAnalysisResults: React.FC<RiskAnalysisResultsProps> = ({
  fileId,
  onClose,
}) => {
  const [results, setResults] = useState<RiskAnalysisResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedParts, setExpandedParts] = useState<Set<string>>(new Set());

  useEffect(() => {
    const fetchResults = async () => {
      try {
        setLoading(true);
        // data 폴더에서 저장된 분석 결과 조회
        const response = fileId
          ? await api.getSavedRiskAnalysisByFile(fileId)
          : await api.getSavedRiskAnalysis();

        if (response.success && response.data) {
          let filteredResults: RiskAnalysisResult[] =
            (response.data as { results?: RiskAnalysisResult[] }).results ||
            (response.data as RiskAnalysisResult[]);

          // 특정 파일 ID가 지정된 경우 해당 파일의 결과만 필터링
          if (fileId) {
            filteredResults = filteredResults.filter(
              (result: RiskAnalysisResult) => result.file_id === fileId
            );
          }

          setResults(filteredResults);
        }
      } catch (error) {
        console.error("위험 분석 결과 조회 실패:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, [fileId]);

  const togglePartExpansion = (analysisId: string, partNumber: number) => {
    const key = `${analysisId}-${partNumber}`;
    const newExpanded = new Set(expandedParts);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedParts(newExpanded);
  };

  const getRiskLevelFromScore = (score: number): string => {
    if (score >= 4) return "HIGH";
    if (score >= 2.5) return "MEDIUM";
    return "LOW";
  };

  const getRiskLevelColor = (level: string | undefined, score?: number) => {
    // level이 없으면 score를 기반으로 계산
    const actualLevel =
      level || (score !== undefined ? getRiskLevelFromScore(score) : undefined);

    if (!actualLevel) {
      return "bg-gray-100 text-gray-800 border-gray-200";
    }

    switch (actualLevel.toUpperCase()) {
      case "HIGH":
        return "bg-red-100 text-red-800 border-red-200";
      case "MEDIUM":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "LOW":
        return "bg-green-100 text-green-800 border-green-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const getRiskLevelIcon = (level: string | undefined, score?: number) => {
    // level이 없으면 score를 기반으로 계산
    const actualLevel =
      level || (score !== undefined ? getRiskLevelFromScore(score) : undefined);

    if (!actualLevel) {
      return <XCircle className="h-4 w-4 text-gray-600" />;
    }

    switch (actualLevel.toUpperCase()) {
      case "HIGH":
        return <AlertTriangle className="h-4 w-4 text-red-600" />;
      case "MEDIUM":
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      case "LOW":
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      default:
        return <XCircle className="h-4 w-4 text-gray-600" />;
    }
  };

  const getChecklistStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case "pass":
      case "passed":
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case "fail":
      case "failed":
        return <XCircle className="h-4 w-4 text-red-600" />;
      default:
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">위험 분석 결과를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (results.length === 0) {
    return null; // 아무것도 렌더링하지 않음
  }

  return (
    <div className="space-y-6">
      {results.map((result) => (
        <Card key={result.analysis_id} className="border-l-4 border-l-blue-500">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg">
                  {result.contract_name}
                </CardTitle>
                <p className="text-sm text-gray-600">
                  분석일: {new Date(result.created_at).toLocaleString("ko-KR")}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge
                  className={getRiskLevelColor(
                    result.analysis_result.overall_risk_level,
                    result.analysis_result.overall_risk_score
                  )}
                >
                  {getRiskLevelIcon(
                    result.analysis_result.overall_risk_level,
                    result.analysis_result.overall_risk_score
                  )}
                  <span className="ml-1">
                    {result.analysis_result.overall_risk_level ||
                      getRiskLevelFromScore(
                        result.analysis_result.overall_risk_score
                      )}{" "}
                    ({result.analysis_result.overall_risk_score.toFixed(1)})
                  </span>
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {result.analysis_result.part_results.map((part) => (
                <Card key={part.part_number} className="border">
                  <Collapsible>
                    <CollapsibleTrigger asChild>
                      <Button
                        variant="ghost"
                        className="w-full justify-between p-4"
                        onClick={() =>
                          togglePartExpansion(
                            result.analysis_id,
                            part.part_number
                          )
                        }
                      >
                        <div className="flex items-center gap-3">
                          {expandedParts.has(
                            `${result.analysis_id}-${part.part_number}`
                          ) ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                          <span className="font-medium">
                            Part {part.part_number}: {part.part_title}
                          </span>
                        </div>
                        <Badge
                          className={getRiskLevelColor(
                            part.risk_level,
                            part.risk_score
                          )}
                        >
                          {getRiskLevelIcon(part.risk_level, part.risk_score)}
                          <span className="ml-1">
                            {part.risk_level ||
                              getRiskLevelFromScore(part.risk_score)}{" "}
                            ({part.risk_score.toFixed(1)})
                          </span>
                        </Badge>
                      </Button>
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <div className="p-4 border-t bg-gray-50">
                        {/* 체크리스트 결과 */}
                        <div className="mb-4">
                          <h4 className="font-semibold mb-2">
                            체크리스트 결과
                          </h4>
                          <div className="space-y-2">
                            {part.checklist_results.map((item, index) => (
                              <div
                                key={index}
                                className="flex items-start gap-2 p-2 bg-white rounded border"
                              >
                                <div className="flex-shrink-0 mt-0.5">
                                  {getChecklistStatusIcon(item.status)}
                                </div>
                                <div className="flex-1">
                                  <p className="font-medium text-sm">
                                    {item.item}
                                  </p>

                                  {/* 분석 내용 */}
                                  {item.analysis && (
                                    <div className="mt-2 p-3 bg-blue-50 rounded-lg border border-blue-200">
                                      <h5 className="text-xs font-semibold text-blue-800 mb-1">
                                        📊 분석
                                      </h5>
                                      <p className="text-xs text-blue-700">
                                        {item.analysis}
                                      </p>
                                    </div>
                                  )}

                                  {/* 추천사항 */}
                                  {item.recommendation && (
                                    <div className="mt-2 p-3 bg-green-50 rounded-lg border border-green-200">
                                      <h5 className="text-xs font-semibold text-green-800 mb-1">
                                        💡 추천사항
                                      </h5>
                                      <p className="text-xs text-green-700">
                                        {item.recommendation}
                                      </p>
                                    </div>
                                  )}

                                  {/* 기존 설명 (fallback) */}
                                  {item.explanation && !item.analysis && (
                                    <p className="text-xs text-gray-600 mt-1">
                                      {item.explanation}
                                    </p>
                                  )}

                                  <Badge
                                    variant="outline"
                                    className={`text-xs mt-2 ${getRiskLevelColor(
                                      item.risk_level,
                                      item.risk_score
                                    )}`}
                                  >
                                    {item.risk_level ||
                                      getRiskLevelFromScore(item.risk_score)}
                                  </Badge>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* 위험 조항 */}
                        {part.risk_clauses && part.risk_clauses.length > 0 && (
                          <div className="mb-4">
                            <h4 className="font-semibold mb-2 text-red-700">
                              ⚠️ 위험 조항
                            </h4>
                            <div className="space-y-2">
                              {part.risk_clauses.map((clause, index) => (
                                <div
                                  key={index}
                                  className="p-3 bg-red-50 rounded border border-red-200"
                                >
                                  <p className="text-sm text-red-800">
                                    {clause}
                                  </p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* 관련 조항 */}
                        {part.relevant_clauses &&
                          part.relevant_clauses.length > 0 && (
                            <div className="mb-4">
                              <h4 className="font-semibold mb-2 text-blue-700">
                                📋 관련 조항
                              </h4>
                              <div className="space-y-2">
                                {part.relevant_clauses.map((clause, index) => (
                                  <div
                                    key={index}
                                    className="p-3 bg-blue-50 rounded-lg border border-blue-200"
                                  >
                                    <p className="text-sm text-blue-800">
                                      {clause}
                                    </p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                        {/* 권고사항 */}
                        {part.recommendations.length > 0 && (
                          <div>
                            <h4 className="font-semibold mb-2">권고사항</h4>
                            <div className="space-y-2">
                              {part.recommendations.map(
                                (recommendation, index) => (
                                  <div
                                    key={index}
                                    className="p-2 bg-blue-50 rounded border border-blue-200"
                                  >
                                    <p className="text-sm">{recommendation}</p>
                                  </div>
                                )
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </CollapsibleContent>
                  </Collapsible>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

export default RiskAnalysisResults;
