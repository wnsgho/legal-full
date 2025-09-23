import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { 
  Search, 
  Filter, 
  Download, 
  Eye, 
  Trash2, 
  Calendar,
  FileText,
  AlertTriangle,
  Clock,
  Archive
} from 'lucide-react';
import { AnalysisResult, Contract, RiskLevel, AnalysisStatus } from '@/types';

interface AnalysisHistoryProps {
  analysisResults: AnalysisResult[];
  contracts: Contract[];
  onViewAnalysis: (analysisId: string) => void;
  onDeleteAnalysis: (analysisId: string) => void;
  onDownloadReport: (analysisId: string) => void;
  onArchiveAnalysis: (analysisId: string) => void;
}

const AnalysisHistory: React.FC<AnalysisHistoryProps> = ({
  analysisResults,
  contracts,
  onViewAnalysis,
  onDeleteAnalysis,
  onDownloadReport,
  onArchiveAnalysis
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRiskLevel, setFilterRiskLevel] = useState<RiskLevel | 'all'>('all');
  const [filterStatus, setFilterStatus] = useState<AnalysisStatus | 'all'>('all');
  const [sortBy, setSortBy] = useState<'date' | 'risk' | 'name'>('date');

  const getRiskLevelColor = (riskLevel: RiskLevel) => {
    switch (riskLevel) {
      case RiskLevel.CRITICAL:
        return 'bg-red-100 text-red-800';
      case RiskLevel.HIGH:
        return 'bg-orange-100 text-orange-800';
      case RiskLevel.MEDIUM:
        return 'bg-yellow-100 text-yellow-800';
      case RiskLevel.LOW:
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
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

  const getStatusBadge = (status: AnalysisStatus) => {
    const variants = {
      [AnalysisStatus.COMPLETED]: 'default',
      [AnalysisStatus.IN_PROGRESS]: 'secondary',
      [AnalysisStatus.PENDING]: 'outline',
      [AnalysisStatus.FAILED]: 'destructive'
    } as const;

    const labels = {
      [AnalysisStatus.COMPLETED]: '완료',
      [AnalysisStatus.IN_PROGRESS]: '분석중',
      [AnalysisStatus.PENDING]: '대기중',
      [AnalysisStatus.FAILED]: '실패'
    };

    return (
      <Badge variant={variants[status]}>
        {labels[status]}
      </Badge>
    );
  };

  const getContractName = (contractId: string) => {
    const contract = contracts.find(c => c.id === contractId);
    return contract?.fileName || '알 수 없는 파일';
  };

  const filteredAndSortedResults = analysisResults
    .filter(result => {
      const contractName = getContractName(result.contractId);
      const matchesSearch = contractName.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           result.id.includes(searchTerm);
      const matchesRiskLevel = filterRiskLevel === 'all' || result.riskLevel === filterRiskLevel;
      const matchesStatus = filterStatus === 'all' || result.status === filterStatus;
      
      return matchesSearch && matchesRiskLevel && matchesStatus;
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'date':
          return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
        case 'risk':
          const riskOrder = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL];
          return riskOrder.indexOf(b.riskLevel) - riskOrder.indexOf(a.riskLevel);
        case 'name':
          return getContractName(a.contractId).localeCompare(getContractName(b.contractId));
        default:
          return 0;
      }
    });

  const stats = {
    total: analysisResults.length,
    completed: analysisResults.filter(r => r.status === AnalysisStatus.COMPLETED).length,
    highRisk: analysisResults.filter(r => r.riskLevel === RiskLevel.HIGH || r.riskLevel === RiskLevel.CRITICAL).length,
    thisWeek: analysisResults.filter(r => {
      const weekAgo = new Date();
      weekAgo.setDate(weekAgo.getDate() - 7);
      return r.createdAt > weekAgo;
    }).length
  };

  return (
    <div className="space-y-6">
      {/* Statistics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <FileText className="h-8 w-8 mx-auto mb-2 text-blue-500" />
            <p className="text-2xl font-bold">{stats.total}</p>
            <p className="text-sm text-gray-600">전체 분석</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <Clock className="h-8 w-8 mx-auto mb-2 text-green-500" />
            <p className="text-2xl font-bold">{stats.completed}</p>
            <p className="text-sm text-gray-600">완료된 분석</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-red-500" />
            <p className="text-2xl font-bold">{stats.highRisk}</p>
            <p className="text-sm text-gray-600">고위험 계약서</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <Calendar className="h-8 w-8 mx-auto mb-2 text-purple-500" />
            <p className="text-2xl font-bold">{stats.thisWeek}</p>
            <p className="text-sm text-gray-600">이번 주 분석</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Search */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="계약서 이름 또는 분석 ID로 검색..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Select value={filterRiskLevel} onValueChange={(value) => setFilterRiskLevel(value as RiskLevel | 'all')}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="위험도" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">모든 위험도</SelectItem>
                  <SelectItem value={RiskLevel.CRITICAL}>매우 높음</SelectItem>
                  <SelectItem value={RiskLevel.HIGH}>높음</SelectItem>
                  <SelectItem value={RiskLevel.MEDIUM}>보통</SelectItem>
                  <SelectItem value={RiskLevel.LOW}>낮음</SelectItem>
                </SelectContent>
              </Select>
              <Select value={filterStatus} onValueChange={(value) => setFilterStatus(value as AnalysisStatus | 'all')}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="상태" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">모든 상태</SelectItem>
                  <SelectItem value={AnalysisStatus.COMPLETED}>완료</SelectItem>
                  <SelectItem value={AnalysisStatus.IN_PROGRESS}>분석중</SelectItem>
                  <SelectItem value={AnalysisStatus.PENDING}>대기중</SelectItem>
                  <SelectItem value={AnalysisStatus.FAILED}>실패</SelectItem>
                </SelectContent>
              </Select>
              <Select value={sortBy} onValueChange={(value) => setSortBy(value as 'date' | 'risk' | 'name')}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="정렬" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="date">날짜순</SelectItem>
                  <SelectItem value="risk">위험도순</SelectItem>
                  <SelectItem value="name">이름순</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Analysis Results */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>분석 기록</span>
            <Badge variant="outline">{filteredAndSortedResults.length}개</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {filteredAndSortedResults.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <FileText className="h-16 w-16 mx-auto mb-4 text-gray-300" />
              <p className="text-lg font-medium mb-2">분석 기록이 없습니다</p>
              <p className="text-sm">계약서를 업로드하고 분석을 시작해보세요.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredAndSortedResults.map((result) => (
                <div key={result.id} className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <div>
                        <p className="font-medium text-sm">{getContractName(result.contractId)}</p>
                        <p className="text-xs text-gray-500">
                          분석 #{result.id.slice(-6)} • {result.createdAt.toLocaleDateString('ko-KR')} {result.createdAt.toLocaleTimeString('ko-KR')}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {getStatusBadge(result.status)}
                      {result.status === AnalysisStatus.COMPLETED && (
                        <Badge className={getRiskLevelColor(result.riskLevel)}>
                          {getRiskLevelLabel(result.riskLevel)}
                        </Badge>
                      )}
                    </div>
                  </div>

                  {result.status === AnalysisStatus.COMPLETED && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3 text-sm">
                      <div>
                        <span className="text-gray-600">위험 조항:</span>
                        <span className="ml-1 font-medium">{result.riskClauses.length}개</span>
                      </div>
                      <div>
                        <span className="text-gray-600">신뢰도:</span>
                        <span className="ml-1 font-medium">{Math.round(result.confidence * 100)}%</span>
                      </div>
                      <div>
                        <span className="text-gray-600">AI 모델:</span>
                        <span className="ml-1 font-medium">{result.aiModel}</span>
                      </div>
                      <div>
                        <span className="text-gray-600">처리 시간:</span>
                        <span className="ml-1 font-medium">
                          {result.processingTimeMs ? `${Math.floor(result.processingTimeMs / 1000)}초` : '-'}
                        </span>
                      </div>
                    </div>
                  )}

                  {result.summary && (
                    <div className="mb-3">
                      <p className="text-sm text-gray-700 line-clamp-2">{result.summary}</p>
                    </div>
                  )}

                  <div className="flex items-center justify-between">
                    <div className="flex space-x-2">
                      {result.status === AnalysisStatus.COMPLETED && (
                        <>
                          <Button
                            variant="default"
                            size="sm"
                            onClick={() => onViewAnalysis(result.id)}
                          >
                            <Eye className="h-4 w-4 mr-1" />
                            상세 보기
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => onDownloadReport(result.id)}
                          >
                            <Download className="h-4 w-4 mr-1" />
                            리포트 다운로드
                          </Button>
                        </>
                      )}
                    </div>
                    <div className="flex space-x-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onArchiveAnalysis(result.id)}
                      >
                        <Archive className="h-4 w-4" />
                      </Button>
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button variant="ghost" size="sm" className="text-red-500 hover:text-red-700">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </DialogTrigger>
                        <DialogContent>
                          <DialogHeader>
                            <DialogTitle>분석 결과 삭제</DialogTitle>
                          </DialogHeader>
                          <div className="space-y-4">
                            <p className="text-sm text-gray-600">
                              이 분석 결과를 삭제하시겠습니까? 삭제된 데이터는 복구할 수 없습니다.
                            </p>
                            <div className="flex justify-end space-x-2">
                              <Button variant="outline" size="sm">
                                취소
                              </Button>
                              <Button 
                                variant="destructive" 
                                size="sm"
                                onClick={() => onDeleteAnalysis(result.id)}
                              >
                                삭제
                              </Button>
                            </div>
                          </div>
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

export default AnalysisHistory;