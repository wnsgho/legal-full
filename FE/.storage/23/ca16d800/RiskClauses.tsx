import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AlertTriangle, Info, Eye, Filter } from 'lucide-react';
import { RiskClause, RiskLevel, ClauseCategory } from '@/types';

interface RiskClausesProps {
  riskClauses: RiskClause[];
  contractText: string;
  onClauseClick: (clause: RiskClause) => void;
}

const RiskClauses: React.FC<RiskClausesProps> = ({
  riskClauses,
  contractText,
  onClauseClick
}) => {
  const [selectedRiskLevel, setSelectedRiskLevel] = useState<RiskLevel | 'all'>('all');
  const [selectedCategory, setSelectedCategory] = useState<ClauseCategory | 'all'>('all');

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

  const getRiskLevelIcon = (riskLevel: RiskLevel) => {
    switch (riskLevel) {
      case RiskLevel.CRITICAL:
      case RiskLevel.HIGH:
        return <AlertTriangle className="h-4 w-4" />;
      default:
        return <Info className="h-4 w-4" />;
    }
  };

  const getCategoryLabel = (category: ClauseCategory) => {
    const labels = {
      [ClauseCategory.TERMINATION]: '계약 해지',
      [ClauseCategory.LIABILITY]: '책임 제한',
      [ClauseCategory.PAYMENT]: '대금 지급',
      [ClauseCategory.INTELLECTUAL_PROPERTY]: '지적재산권',
      [ClauseCategory.CONFIDENTIALITY]: '비밀유지',
      [ClauseCategory.COMPLIANCE]: '규정 준수',
      [ClauseCategory.DISPUTE_RESOLUTION]: '분쟁 해결'
    };
    return labels[category] || category;
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

  const filteredClauses = riskClauses.filter(clause => {
    const riskMatch = selectedRiskLevel === 'all' || clause.riskLevel === selectedRiskLevel;
    const categoryMatch = selectedCategory === 'all' || clause.category === selectedCategory;
    return riskMatch && categoryMatch;
  });

  const riskLevelCounts = riskClauses.reduce((acc, clause) => {
    acc[clause.riskLevel] = (acc[clause.riskLevel] || 0) + 1;
    return acc;
  }, {} as Record<RiskLevel, number>);

  const highlightClauseInText = (text: string, clause: RiskClause) => {
    const { start, end } = clause.position;
    const before = text.substring(0, start);
    const highlighted = text.substring(start, end);
    const after = text.substring(end);
    
    return (
      <div className="whitespace-pre-wrap">
        {before}
        <mark className={`px-1 py-0.5 rounded ${getRiskLevelColor(clause.riskLevel)}`}>
          {highlighted}
        </mark>
        {after}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Risk Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>위험 조항 요약</span>
            <Badge variant="outline">{riskClauses.length}개 발견</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(riskLevelCounts).map(([level, count]) => (
              <div key={level} className="text-center">
                <div className={`inline-flex items-center justify-center w-12 h-12 rounded-full ${getRiskLevelColor(level as RiskLevel)}`}>
                  {getRiskLevelIcon(level as RiskLevel)}
                </div>
                <p className="mt-2 text-sm font-medium">{getRiskLevelLabel(level as RiskLevel)}</p>
                <p className="text-2xl font-bold">{count}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex items-center space-x-2">
              <Filter className="h-4 w-4 text-gray-500" />
              <span className="text-sm font-medium">필터:</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600">위험도:</span>
              <select
                value={selectedRiskLevel}
                onChange={(e) => setSelectedRiskLevel(e.target.value as RiskLevel | 'all')}
                className="text-sm border rounded px-2 py-1"
              >
                <option value="all">전체</option>
                <option value={RiskLevel.CRITICAL}>매우 높음</option>
                <option value={RiskLevel.HIGH}>높음</option>
                <option value={RiskLevel.MEDIUM}>보통</option>
                <option value={RiskLevel.LOW}>낮음</option>
              </select>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600">카테고리:</span>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value as ClauseCategory | 'all')}
                className="text-sm border rounded px-2 py-1"
              >
                <option value="all">전체</option>
                {Object.values(ClauseCategory).map(category => (
                  <option key={category} value={category}>
                    {getCategoryLabel(category)}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Risk Clauses List */}
      <Card>
        <CardHeader>
          <CardTitle>위험 조항 상세</CardTitle>
        </CardHeader>
        <CardContent>
          {filteredClauses.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Info className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>선택한 조건에 해당하는 위험 조항이 없습니다.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredClauses.map((clause) => (
                <div key={clause.id} className="border rounded-lg p-4 space-y-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <Badge className={getRiskLevelColor(clause.riskLevel)}>
                          {getRiskLevelLabel(clause.riskLevel)}
                        </Badge>
                        <Badge variant="outline">
                          {getCategoryLabel(clause.category)}
                        </Badge>
                      </div>
                      <p className="text-sm font-medium text-gray-900 mb-2">
                        "{clause.text}"
                      </p>
                      <p className="text-sm text-gray-600 mb-2">
                        {clause.explanation}
                      </p>
                      <div className="bg-blue-50 border-l-4 border-blue-400 p-3 rounded">
                        <p className="text-sm text-blue-800">
                          <strong>권장사항:</strong> {clause.recommendation}
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex justify-between items-center pt-2">
                    <span className="text-xs text-gray-500">
                      위치: {clause.position.start} - {clause.position.end}
                    </span>
                    <div className="flex space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onClauseClick(clause)}
                      >
                        <Eye className="h-4 w-4 mr-1" />
                        원문에서 보기
                      </Button>
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button variant="default" size="sm">
                            상세 보기
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
                          <DialogHeader>
                            <DialogTitle className="flex items-center space-x-2">
                              <Badge className={getRiskLevelColor(clause.riskLevel)}>
                                {getRiskLevelLabel(clause.riskLevel)}
                              </Badge>
                              <span>{getCategoryLabel(clause.category)} 조항</span>
                            </DialogTitle>
                          </DialogHeader>
                          <Tabs defaultValue="analysis" className="w-full">
                            <TabsList>
                              <TabsTrigger value="analysis">분석 결과</TabsTrigger>
                              <TabsTrigger value="context">원문 컨텍스트</TabsTrigger>
                            </TabsList>
                            <TabsContent value="analysis" className="space-y-4">
                              <div>
                                <h4 className="font-semibold mb-2">조항 내용</h4>
                                <div className="bg-gray-50 p-3 rounded border">
                                  <p className="text-sm">{clause.text}</p>
                                </div>
                              </div>
                              <div>
                                <h4 className="font-semibold mb-2">위험 분석</h4>
                                <p className="text-sm text-gray-700">{clause.explanation}</p>
                              </div>
                              <div>
                                <h4 className="font-semibold mb-2">권장 조치</h4>
                                <div className="bg-blue-50 border-l-4 border-blue-400 p-3 rounded">
                                  <p className="text-sm text-blue-800">{clause.recommendation}</p>
                                </div>
                              </div>
                            </TabsContent>
                            <TabsContent value="context">
                              <div>
                                <h4 className="font-semibold mb-2">계약서 원문 (하이라이트 적용)</h4>
                                <div className="bg-gray-50 p-4 rounded border text-sm leading-relaxed max-h-96 overflow-y-auto">
                                  {highlightClauseInText(contractText, clause)}
                                </div>
                              </div>
                            </TabsContent>
                          </Tabs>
                        </DialogContent>
                      </Dialog>
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

export default RiskClauses;