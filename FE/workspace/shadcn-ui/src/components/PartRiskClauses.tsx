import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronUp, AlertTriangle, Shield } from "lucide-react";
import { useState } from "react";

interface PartRiskClause {
  part_title: string;
  risk_level: string;
  risk_score: number;
  risk_clauses: string[];
  recommendations: string[];
}

interface PartRiskClausesProps {
  partResults: Array<{
    part_title?: string;
    risk_level?: string;
    risk_score?: number;
    risk_clauses?: string[];
    relevant_clauses?: string[];
    recommendations?: string[];
  }>;
  title?: string;
  showRecommendations?: boolean;
}

const PartRiskClauses: React.FC<PartRiskClausesProps> = ({
  partResults,
  title = "파트별 위험 조항",
  showRecommendations = true,
}) => {
  const [expandedParts, setExpandedParts] = useState<Set<number>>(new Set());

  const togglePartExpansion = (partIndex: number) => {
    const newExpanded = new Set(expandedParts);
    if (newExpanded.has(partIndex)) {
      newExpanded.delete(partIndex);
    } else {
      newExpanded.add(partIndex);
    }
    setExpandedParts(newExpanded);
  };

  const getRiskLevelColor = (riskLevel: string) => {
    switch (riskLevel) {
      case "CRITICAL":
        return "bg-red-100 text-red-800 border-red-200";
      case "HIGH":
        return "bg-orange-100 text-orange-800 border-orange-200";
      case "MEDIUM":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "LOW":
        return "bg-green-100 text-green-800 border-green-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const getRiskLevelIcon = (riskLevel: string) => {
    switch (riskLevel) {
      case "CRITICAL":
      case "HIGH":
        return <AlertTriangle className="h-4 w-4 text-red-600" />;
      case "MEDIUM":
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      case "LOW":
        return <Shield className="h-4 w-4 text-green-600" />;
      default:
        return <Shield className="h-4 w-4 text-gray-600" />;
    }
  };

  const getRiskLevelText = (riskLevel: string) => {
    switch (riskLevel) {
      case "CRITICAL":
        return "매우 위험";
      case "HIGH":
        return "높음";
      case "MEDIUM":
        return "보통";
      case "LOW":
        return "낮음";
      default:
        return "알 수 없음";
    }
  };

  if (!partResults || partResults.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <Shield className="h-12 w-12 mx-auto mb-3 text-gray-300" />
            <p className="text-sm font-medium mb-1">분석된 파트가 없습니다</p>
            <p className="text-xs text-gray-500">
              위험 분석을 먼저 실행해주세요.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5" />
          {title}
          <Badge variant="outline" className="ml-2">
            {partResults.length}개 파트
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {partResults.map((part, index) => {
            const isExpanded = expandedParts.has(index);
            // risk_clauses가 있으면 사용하고, 없으면 relevant_clauses 사용
            const riskClauses =
              part.risk_clauses || part.relevant_clauses || [];
            const recommendations = part.recommendations || [];
            const riskLevel = part.risk_level || "UNKNOWN";
            const riskScore = part.risk_score || 0;

            return (
              <div key={index} className="border rounded-lg overflow-hidden">
                {/* 파트 헤더 */}
                <div
                  className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => togglePartExpansion(index)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {getRiskLevelIcon(riskLevel)}
                      <div>
                        <h4 className="font-medium text-sm">
                          {part.part_title || `파트 ${index + 1}`}
                        </h4>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge
                            variant="outline"
                            className={`text-xs ${getRiskLevelColor(
                              riskLevel
                            )}`}
                          >
                            {getRiskLevelText(riskLevel)}
                          </Badge>
                          <span className="text-xs text-gray-500">
                            위험도: {riskScore.toFixed(1)}/5.0
                          </span>
                          {riskClauses.length > 0 && (
                            <Badge variant="secondary" className="text-xs">
                              {riskClauses.length}개 조항
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {riskClauses.length > 0 && (
                        <Badge variant="destructive" className="text-xs">
                          {riskClauses.length}개 위험조항
                        </Badge>
                      )}
                      {isExpanded ? (
                        <ChevronUp className="h-4 w-4 text-gray-500" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-gray-500" />
                      )}
                    </div>
                  </div>
                </div>

                {/* 파트 상세 내용 */}
                {isExpanded && (
                  <div className="border-t bg-gray-50 p-4 space-y-4">
                    {/* 위험 조항들 */}
                    {riskClauses.length > 0 ? (
                      <div>
                        <h5 className="font-medium text-sm mb-3 flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4 text-red-600" />
                          검색된 관련 조항 ({riskClauses.length}개)
                        </h5>
                        <div className="space-y-2">
                          {riskClauses
                            .slice(0, 10)
                            .map((clause, clauseIndex) => (
                              <div
                                key={clauseIndex}
                                className="p-3 bg-red-50 rounded-lg border border-red-200"
                              >
                                <div className="flex items-start gap-2">
                                  <span className="text-red-600 font-bold text-sm">
                                    {clauseIndex + 1}.
                                  </span>
                                  <p className="text-sm text-red-800 font-medium">
                                    {clause}
                                  </p>
                                </div>
                              </div>
                            ))}
                          {riskClauses.length > 10 && (
                            <div className="text-center py-2">
                              <span className="text-xs text-gray-500">
                                ... 외 {riskClauses.length - 10}개 조항 더 있음
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className="p-3 bg-green-50 rounded-lg border border-green-200">
                        <div className="flex items-center gap-2">
                          <Shield className="h-4 w-4 text-green-600" />
                          <p className="text-sm text-green-800 font-medium">
                            이 파트에서는 관련 조항이 발견되지 않았습니다.
                          </p>
                        </div>
                      </div>
                    )}

                    {/* 권고사항들 */}
                    {showRecommendations && recommendations.length > 0 && (
                      <div>
                        <h5 className="font-medium text-sm mb-3 flex items-center gap-2">
                          <Shield className="h-4 w-4 text-blue-600" />
                          권고사항 ({recommendations.length}개)
                        </h5>
                        <div className="space-y-2">
                          {recommendations.map((recommendation, recIndex) => (
                            <div
                              key={recIndex}
                              className="p-3 bg-blue-50 rounded-lg border border-blue-200"
                            >
                              <div className="flex items-start gap-2">
                                <span className="text-blue-600 font-bold text-sm">
                                  {recIndex + 1}.
                                </span>
                                <p className="text-sm text-blue-800">
                                  {recommendation}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
};

export default PartRiskClauses;
