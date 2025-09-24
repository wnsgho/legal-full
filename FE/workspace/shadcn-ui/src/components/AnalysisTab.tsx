import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileText } from "lucide-react";
import RiskClauses from "@/components/RiskClauses";
import { AnalysisResult, RiskClause } from "@/types";
import { contractSampleText } from "@/lib/mockData";

interface AnalysisTabProps {
  viewMode: "original" | "summary";
  setViewMode: (viewMode: "original" | "summary") => void;
  currentAnalysisResult: AnalysisResult | undefined;
  handleClauseClick: (clause: RiskClause) => void;
}

const AnalysisTab: React.FC<AnalysisTabProps> = ({
  viewMode,
  setViewMode,
  currentAnalysisResult,
  handleClauseClick,
}) => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">분석 결과</h2>
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

      {currentAnalysisResult ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <Card>
              <CardHeader>
                <CardTitle>
                  계약서 {viewMode === "original" ? "원문" : "요약"}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto text-sm leading-relaxed">
                  {viewMode === "original" ? (
                    <pre className="whitespace-pre-wrap font-sans">
                      {contractSampleText}
                    </pre>
                  ) : (
                    <div>
                      <h4 className="font-semibold mb-2">분석 요약</h4>
                      <p className="mb-4">
                        {currentAnalysisResult.summary}
                      </p>
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
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
          <div>
            <RiskClauses
              riskClauses={currentAnalysisResult.riskClauses}
              contractText={contractSampleText}
              onClauseClick={handleClauseClick}
              onRiskAnalysisComplete={(analysis) => {
                console.log("Risk analysis completed:", analysis);
              }}
            />
          </div>
        </div>
      ) : (
        <Card>
          <CardContent className="p-8 text-center">
            <FileText className="h-16 w-16 mx-auto mb-4 text-gray-300" />
            <p className="text-lg font-medium mb-2">
              분석 결과가 없습니다
            </p>
            <p className="text-sm text-gray-500">
              계약서를 업로드하고 분석을 시작해보세요.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AnalysisTab;
