import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FileText, BarChart3, Shield, Clock } from "lucide-react";
import { AnalysisResult, Contract, RiskLevel } from "@/types";

interface SummaryDashboardTabProps {
  contracts: Contract[];
  analysisResults: AnalysisResult[];
}

const SummaryDashboardTab: React.FC<SummaryDashboardTabProps> = ({
  contracts,
  analysisResults,
}) => {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <FileText className="h-8 w-8 text-blue-500" />
              <div className="ml-4">
                <p className="text-2xl font-bold">{contracts.length}</p>
                <p className="text-sm text-gray-600">업로드된 계약서</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <BarChart3 className="h-8 w-8 text-green-500" />
              <div className="ml-4">
                <p className="text-2xl font-bold">
                  {analysisResults.length}
                </p>
                <p className="text-sm text-gray-600">완료된 분석</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <Shield className="h-8 w-8 text-red-500" />
              <div className="ml-4">
                <p className="text-2xl font-bold">
                  {analysisResults.reduce(
                    (sum, a) => sum + a.riskClauses.length,
                    0
                  )}
                </p>
                <p className="text-sm text-gray-600">발견된 위험 조항</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <Clock className="h-8 w-8 text-purple-500" />
              <div className="ml-4">
                <p className="text-2xl font-bold">
                  {Math.round(
                    analysisResults.reduce(
                      (sum, a) => sum + (a.processingTimeMs || 0),
                      0
                    ) / 1000
                  )}
                  s
                </p>
                <p className="text-sm text-gray-600">총 분석 시간</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>최근 분석 활동</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {analysisResults.slice(0, 5).map((result) => (
                <div
                  key={result.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div>
                    <p className="font-medium text-sm">
                      분석 #{result.id.slice(-6)}
                    </p>
                    <p className="text-xs text-gray-500">
                      {result.createdAt.toLocaleDateString("ko-KR")}
                    </p>
                  </div>
                  <Badge
                    className={
                      result.riskLevel === RiskLevel.CRITICAL
                        ? "bg-red-100 text-red-800"
                        : result.riskLevel === RiskLevel.HIGH
                        ? "bg-orange-100 text-orange-800"
                        : result.riskLevel === RiskLevel.MEDIUM
                        ? "bg-yellow-100 text-yellow-800"
                        : "bg-green-100 text-green-800"
                    }
                  >
                    {result.riskLevel === RiskLevel.CRITICAL
                      ? "매우 높음"
                      : result.riskLevel === RiskLevel.HIGH
                      ? "높음"
                      : result.riskLevel === RiskLevel.MEDIUM
                      ? "보통"
                      : "낮음"}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>위험도 분포</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                RiskLevel.CRITICAL,
                RiskLevel.HIGH,
                RiskLevel.MEDIUM,
                RiskLevel.LOW,
              ].map((level) => {
                const count = analysisResults.filter(
                  (a) => a.riskLevel === level
                ).length;
                const percentage =
                  analysisResults.length > 0
                    ? (count / analysisResults.length) * 100
                    : 0;
                const label =
                  level === RiskLevel.CRITICAL
                    ? "매우 높음"
                    : level === RiskLevel.HIGH
                    ? "높음"
                    : level === RiskLevel.MEDIUM
                    ? "보통"
                    : "낮음";
                const color =
                  level === RiskLevel.CRITICAL
                    ? "bg-red-500"
                    : level === RiskLevel.HIGH
                    ? "bg-orange-500"
                    : level === RiskLevel.MEDIUM
                    ? "bg-yellow-500"
                    : "bg-green-500";

                return (
                  <div
                    key={level}
                    className="flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-2">
                      <div
                        className={`w-3 h-3 rounded-full ${color}`}
                      ></div>
                      <span className="text-sm">{label}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-20 bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${color}`}
                          style={{ width: `${percentage}%` }}
                        ></div>
                      </div>
                      <span className="text-sm font-medium w-8">
                        {count}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default SummaryDashboardTab;
