import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ArrowRight, Plus, Minus, Edit, TrendingUp, TrendingDown } from 'lucide-react';
import { AnalysisResult, RiskClause, RiskLevel, ComparisonResult } from '@/types';

interface ComparisonViewProps {
  analysisResults: AnalysisResult[];
  onCompare: (analysisId1: string, analysisId2: string) => ComparisonResult;
}

const ComparisonView: React.FC<ComparisonViewProps> = ({
  analysisResults,
  onCompare
}) => {
  const [selectedAnalysis1, setSelectedAnalysis1] = useState<string>('');
  const [selectedAnalysis2, setSelectedAnalysis2] = useState<string>('');
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null);

  const handleCompare = () => {
    if (selectedAnalysis1 && selectedAnalysis2) {
      const result = onCompare(selectedAnalysis1, selectedAnalysis2);
      setComparisonResult(result);
    }
  };

  const getRiskLevelColor = (riskLevel: RiskLevel) => {
    switch (riskLevel) {
      case RiskLevel.CRITICAL:
        return 'bg-red-100 text-red-800 border-red-200';
      case RiskLevel.HIGH:
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case RiskLevel.MEDIUM:
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case RiskLevel.LOW:
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getRiskLevelLabel = (riskLevel: RiskLevel) => {
    const labels = {
      [RiskLevel.CRITICAL]: '매우 높음',
      [RiskLevel.HIGH]: '높음',
      [RiskLevel.MEDIUM]: '보통',
      [RiskLevel.LOW]: '낮음'
    };
    return labels[riskLevel];
  };

  const analysis1 = analysisResults.find(a => a.id === selectedAnalysis1);
  const analysis2 = analysisResults.find(a => a.id === selectedAnalysis2);

  return (
    <div className="space-y-6">
      {/* Comparison Setup */}
      <Card>
        <CardHeader>
          <CardTitle>계약서 분석 비교</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            <div>
              <label className="block text-sm font-medium mb-2">기준 분석</label>
              <Select value={selectedAnalysis1} onValueChange={setSelectedAnalysis1}>
                <SelectTrigger>
                  <SelectValue placeholder="첫 번째 분석 선택" />
                </SelectTrigger>
                <SelectContent>
                  {analysisResults.map((analysis) => (
                    <SelectItem key={analysis.id} value={analysis.id}>
                      분석 #{analysis.id.slice(-6)} ({analysis.createdAt.toLocaleDateString('ko-KR')})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="flex justify-center">
              <ArrowRight className="h-6 w-6 text-gray-400" />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">비교 대상</label>
              <Select value={selectedAnalysis2} onValueChange={setSelectedAnalysis2}>
                <SelectTrigger>
                  <SelectValue placeholder="두 번째 분석 선택" />
                </SelectTrigger>
                <SelectContent>
                  {analysisResults
                    .filter(a => a.id !== selectedAnalysis1)
                    .map((analysis) => (
                      <SelectItem key={analysis.id} value={analysis.id}>
                        분석 #{analysis.id.slice(-6)} ({analysis.createdAt.toLocaleDateString('ko-KR')})
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          
          <div className="mt-4">
            <Button 
              onClick={handleCompare}
              disabled={!selectedAnalysis1 || !selectedAnalysis2}
              className="w-full md:w-auto"
            >
              비교 분석 시작
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Side by Side Analysis Overview */}
      {analysis1 && analysis2 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>기준 분석</span>
                <Badge className={getRiskLevelColor(analysis1.riskLevel)}>
                  {getRiskLevelLabel(analysis1.riskLevel)}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">위험 조항 수</span>
                  <span className="font-medium">{analysis1.riskClauses.length}개</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">신뢰도</span>
                  <span className="font-medium">{Math.round(analysis1.confidence * 100)}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">분석 일시</span>
                  <span className="font-medium">{analysis1.createdAt.toLocaleDateString('ko-KR')}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>비교 대상</span>
                <Badge className={getRiskLevelColor(analysis2.riskLevel)}>
                  {getRiskLevelLabel(analysis2.riskLevel)}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">위험 조항 수</span>
                  <span className="font-medium">{analysis2.riskClauses.length}개</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">신뢰도</span>
                  <span className="font-medium">{Math.round(analysis2.confidence * 100)}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">분석 일시</span>
                  <span className="font-medium">{analysis2.createdAt.toLocaleDateString('ko-KR')}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Comparison Results */}
      {comparisonResult && (
        <Card>
          <CardHeader>
            <CardTitle>비교 분석 결과</CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="summary" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="summary">요약</TabsTrigger>
                <TabsTrigger value="added">추가된 조항</TabsTrigger>
                <TabsTrigger value="removed">제거된 조항</TabsTrigger>
                <TabsTrigger value="modified">수정된 조항</TabsTrigger>
              </TabsList>
              
              <TabsContent value="summary" className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="text-center p-4 bg-green-50 rounded-lg">
                    <Plus className="h-8 w-8 mx-auto mb-2 text-green-600" />
                    <p className="text-2xl font-bold text-green-600">{comparisonResult.differences.added.length}</p>
                    <p className="text-sm text-green-700">추가된 조항</p>
                  </div>
                  <div className="text-center p-4 bg-red-50 rounded-lg">
                    <Minus className="h-8 w-8 mx-auto mb-2 text-red-600" />
                    <p className="text-2xl font-bold text-red-600">{comparisonResult.differences.removed.length}</p>
                    <p className="text-sm text-red-700">제거된 조항</p>
                  </div>
                  <div className="text-center p-4 bg-blue-50 rounded-lg">
                    <Edit className="h-8 w-8 mx-auto mb-2 text-blue-600" />
                    <p className="text-2xl font-bold text-blue-600">{comparisonResult.differences.modified.length}</p>
                    <p className="text-sm text-blue-700">수정된 조항</p>
                  </div>
                </div>
                
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="font-semibold mb-2">비교 요약</h4>
                  <p className="text-sm text-gray-700">{comparisonResult.summary}</p>
                </div>
              </TabsContent>
              
              <TabsContent value="added">
                <div className="space-y-3">
                  {comparisonResult.differences.added.length === 0 ? (
                    <p className="text-center text-gray-500 py-8">추가된 조항이 없습니다.</p>
                  ) : (
                    comparisonResult.differences.added.map((clause) => (
                      <div key={clause.id} className="border-l-4 border-green-400 bg-green-50 p-3 rounded">
                        <div className="flex items-center space-x-2 mb-2">
                          <Badge className={getRiskLevelColor(clause.riskLevel)}>
                            {getRiskLevelLabel(clause.riskLevel)}
                          </Badge>
                          <Plus className="h-4 w-4 text-green-600" />
                        </div>
                        <p className="text-sm font-medium mb-1">{clause.text}</p>
                        <p className="text-xs text-gray-600">{clause.explanation}</p>
                      </div>
                    ))
                  )}
                </div>
              </TabsContent>
              
              <TabsContent value="removed">
                <div className="space-y-3">
                  {comparisonResult.differences.removed.length === 0 ? (
                    <p className="text-center text-gray-500 py-8">제거된 조항이 없습니다.</p>
                  ) : (
                    comparisonResult.differences.removed.map((clause) => (
                      <div key={clause.id} className="border-l-4 border-red-400 bg-red-50 p-3 rounded">
                        <div className="flex items-center space-x-2 mb-2">
                          <Badge className={getRiskLevelColor(clause.riskLevel)}>
                            {getRiskLevelLabel(clause.riskLevel)}
                          </Badge>
                          <Minus className="h-4 w-4 text-red-600" />
                        </div>
                        <p className="text-sm font-medium mb-1">{clause.text}</p>
                        <p className="text-xs text-gray-600">{clause.explanation}</p>
                      </div>
                    ))
                  )}
                </div>
              </TabsContent>
              
              <TabsContent value="modified">
                <div className="space-y-3">
                  {comparisonResult.differences.modified.length === 0 ? (
                    <p className="text-center text-gray-500 py-8">수정된 조항이 없습니다.</p>
                  ) : (
                    comparisonResult.differences.modified.map((clause) => (
                      <div key={clause.id} className="border-l-4 border-blue-400 bg-blue-50 p-3 rounded">
                        <div className="flex items-center space-x-2 mb-2">
                          <Badge className={getRiskLevelColor(clause.riskLevel)}>
                            {getRiskLevelLabel(clause.riskLevel)}
                          </Badge>
                          <Edit className="h-4 w-4 text-blue-600" />
                        </div>
                        <p className="text-sm font-medium mb-1">{clause.text}</p>
                        <p className="text-xs text-gray-600">{clause.explanation}</p>
                      </div>
                    ))
                  )}
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ComparisonView;