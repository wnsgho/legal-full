import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Upload, 
  BarChart3, 
  MessageSquare, 
  History, 
  GitCompare,
  FileText,
  Shield,
  TrendingUp,
  Users,
  Clock
} from 'lucide-react';
import FileUpload from '@/components/FileUpload';
import AnalysisProgress from '@/components/AnalysisProgress';
import RiskClauses from '@/components/RiskClauses';
import ComparisonView from '@/components/ComparisonView';
import ChatInterface from '@/components/ChatInterface';
import AnalysisHistory from '@/components/AnalysisHistory';
import { 
  mockContracts, 
  mockAnalysisResults, 
  mockChatMessages, 
  contractSampleText 
} from '@/lib/mockData';
import { 
  Contract, 
  AnalysisResult, 
  ChatMessage, 
  ComparisonResult, 
  RiskClause,
  ContractStatus,
  AnalysisStatus,
  RiskLevel
} from '@/types';

const Dashboard: React.FC = () => {
  const [contracts, setContracts] = useState<Contract[]>(mockContracts);
  const [analysisResults, setAnalysisResults] = useState<AnalysisResult[]>(mockAnalysisResults);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(mockChatMessages);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [currentAnalysis, setCurrentAnalysis] = useState<{
    id: string;
    progress: number;
    stage: string;
  } | undefined>();
  const [selectedContract, setSelectedContract] = useState<string>('1');
  const [viewMode, setViewMode] = useState<'original' | 'summary'>('original');

  // Mock handlers
  const handleFileUpload = (files: File[]) => {
    setIsUploading(true);
    setUploadProgress(0);

    // Simulate upload progress
    const interval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsUploading(false);
          
          // Add new contracts
          const newContracts = files.map((file, index) => ({
            id: `new_${Date.now()}_${index}`,
            userId: 'user1',
            fileName: file.name,
            fileSize: file.size,
            fileType: file.type,
            uploadedAt: new Date(),
            status: ContractStatus.UPLOADED,
            s3Key: `contracts/user1/${file.name}`
          }));
          
          setContracts(prev => [...prev, ...newContracts]);
          
          // Start analysis simulation
          setTimeout(() => {
            startAnalysisSimulation(newContracts[0].id);
          }, 1000);
          
          return 100;
        }
        return prev + 10;
      });
    }, 200);
  };

  const startAnalysisSimulation = (contractId: string) => {
    const analysisId = `analysis_${Date.now()}`;
    setCurrentAnalysis({
      id: analysisId,
      progress: 0,
      stage: 'AI 모델 초기화 중...'
    });

    const stages = [
      '계약서 텍스트 추출 중...',
      '자연어 처리 중...',
      '위험 조항 식별 중...',
      '법률 조항 분석 중...',
      '권장사항 생성 중...',
      '분석 완료'
    ];

    let currentStage = 0;
    const interval = setInterval(() => {
      setCurrentAnalysis(prev => {
        if (!prev) return undefined;
        
        const newProgress = prev.progress + 16;
        if (newProgress >= 100) {
          clearInterval(interval);
          
          // Add completed analysis
          const newAnalysis: AnalysisResult = {
            id: analysisId,
            contractId,
            status: AnalysisStatus.COMPLETED,
            riskLevel: RiskLevel.HIGH,
            riskClauses: mockAnalysisResults[0].riskClauses,
            summary: '새로 업로드된 계약서에 대한 AI 분석이 완료되었습니다. 총 4개의 위험 조항이 발견되었으며, 특히 손해배상 조항에 주의가 필요합니다.',
            recommendations: [
              '손해배상액 조항 재검토 필요',
              '계약 기간 명확화 권장',
              '분쟁 해결 방법 개선 검토'
            ],
            aiModel: 'GPT-4',
            confidence: 0.94,
            createdAt: new Date(),
            processingTimeMs: 18000
          };
          
          setAnalysisResults(prev => [newAnalysis, ...prev]);
          setCurrentAnalysis(undefined);
          return undefined;
        }
        
        return {
          ...prev,
          progress: newProgress,
          stage: stages[Math.min(currentStage, stages.length - 1)]
        };
      });
      currentStage++;
    }, 1000);
  };

  const handleRetryAnalysis = (analysisId: string) => {
    console.log('Retrying analysis:', analysisId);
  };

  const handleViewResult = (analysisId: string) => {
    console.log('Viewing result:', analysisId);
  };

  const handleCompare = (analysisId1: string, analysisId2: string): ComparisonResult => {
    return {
      id: `comparison_${Date.now()}`,
      analysisId1,
      analysisId2,
      differences: {
        added: mockAnalysisResults[0].riskClauses.slice(0, 1),
        removed: mockAnalysisResults[0].riskClauses.slice(1, 2),
        modified: mockAnalysisResults[0].riskClauses.slice(2, 3)
      },
      riskLevelChange: {
        from: RiskLevel.MEDIUM,
        to: RiskLevel.HIGH
      },
      summary: '두 분석 결과를 비교한 결과, 1개의 새로운 위험 조항이 추가되었고, 1개가 제거되었으며, 1개가 수정되었습니다. 전반적인 위험도가 보통에서 높음으로 상승했습니다.',
      createdAt: new Date()
    };
  };

  const handleSendMessage = (message: string) => {
    const newMessage: ChatMessage = {
      id: `msg_${Date.now()}`,
      contractId: selectedContract,
      message,
      isUserMessage: true,
      createdAt: new Date()
    };

    setChatMessages(prev => [...prev, newMessage]);

    setTimeout(() => {
      const responses = [
        '분석 결과를 바탕으로 답변드리겠습니다. 해당 조항은 일반적인 계약 조건과 비교했을 때 다소 까다로운 편입니다.',
        '이 부분은 법적 검토가 필요한 영역입니다. 전문가와 상담하시는 것을 권장합니다.',
        '계약서에서 해당 내용을 찾아보니, 다음과 같은 조항이 관련되어 있습니다.',
        '위험도 분석 결과, 이 조항은 중간 수준의 주의가 필요합니다.'
      ];
      
      const response = responses[Math.floor(Math.random() * responses.length)];
      
      setChatMessages(prev => prev.map(msg => 
        msg.id === newMessage.id 
          ? { ...msg, response }
          : msg
      ));
    }, 1500);
  };

  const handleClearChatHistory = () => {
    setChatMessages([]);
  };

  const handleClauseClick = (clause: RiskClause) => {
    console.log('Clause clicked:', clause);
  };

  const handleViewAnalysis = (analysisId: string) => {
    console.log('View analysis:', analysisId);
  };

  const handleDeleteAnalysis = (analysisId: string) => {
    setAnalysisResults(prev => prev.filter(a => a.id !== analysisId));
  };

  const handleDownloadReport = (analysisId: string) => {
    console.log('Download report:', analysisId);
  };

  const handleArchiveAnalysis = (analysisId: string) => {
    console.log('Archive analysis:', analysisId);
  };

  const currentAnalysisResult = analysisResults.find(a => a.contractId === selectedContract);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <Shield className="h-8 w-8 text-blue-600" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">계약서 분석 AI</h1>
                <p className="text-sm text-gray-500">스마트 계약서 리스크 분석 서비스</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Badge variant="outline" className="text-xs">
                <Users className="h-3 w-3 mr-1" />
                Pro 플랜
              </Badge>
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <span className="text-sm font-medium text-blue-600">김</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs defaultValue="upload" className="space-y-6">
          <TabsList className="grid w-full grid-cols-6">
            <TabsTrigger value="upload" className="flex items-center space-x-2">
              <Upload className="h-4 w-4" />
              <span>업로드</span>
            </TabsTrigger>
            <TabsTrigger value="analysis" className="flex items-center space-x-2">
              <BarChart3 className="h-4 w-4" />
              <span>분석 결과</span>
            </TabsTrigger>
            <TabsTrigger value="comparison" className="flex items-center space-x-2">
              <GitCompare className="h-4 w-4" />
              <span>비교 분석</span>
            </TabsTrigger>
            <TabsTrigger value="chat" className="flex items-center space-x-2">
              <MessageSquare className="h-4 w-4" />
              <span>AI 상담</span>
            </TabsTrigger>
            <TabsTrigger value="history" className="flex items-center space-x-2">
              <History className="h-4 w-4" />
              <span>분석 기록</span>
            </TabsTrigger>
            <TabsTrigger value="dashboard" className="flex items-center space-x-2">
              <TrendingUp className="h-4 w-4" />
              <span>대시보드</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="upload" className="space-y-6">
            <FileUpload
              onFileUpload={handleFileUpload}
              uploadedContracts={contracts}
              isUploading={isUploading}
              uploadProgress={uploadProgress}
            />
            <AnalysisProgress
              analysisResults={analysisResults}
              onRetryAnalysis={handleRetryAnalysis}
              onViewResult={handleViewResult}
              currentAnalysis={currentAnalysis}
            />
          </TabsContent>

          <TabsContent value="analysis" className="space-y-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900">분석 결과</h2>
              <div className="flex items-center space-x-2">
                <Button
                  variant={viewMode === 'original' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('original')}
                >
                  원문 보기
                </Button>
                <Button
                  variant={viewMode === 'summary' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('summary')}
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
                      <CardTitle>계약서 {viewMode === 'original' ? '원문' : '요약'}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto text-sm leading-relaxed">
                        {viewMode === 'original' ? (
                          <pre className="whitespace-pre-wrap font-sans">{contractSampleText}</pre>
                        ) : (
                          <div>
                            <h4 className="font-semibold mb-2">분석 요약</h4>
                            <p className="mb-4">{currentAnalysisResult.summary}</p>
                            <h4 className="font-semibold mb-2">주요 권장사항</h4>
                            <ul className="list-disc list-inside space-y-1">
                              {currentAnalysisResult.recommendations.map((rec, index) => (
                                <li key={index} className="text-sm">{rec}</li>
                              ))}
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
                  />
                </div>
              </div>
            ) : (
              <Card>
                <CardContent className="p-8 text-center">
                  <FileText className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                  <p className="text-lg font-medium mb-2">분석 결과가 없습니다</p>
                  <p className="text-sm text-gray-500">계약서를 업로드하고 분석을 시작해보세요.</p>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="comparison">
            <ComparisonView
              analysisResults={analysisResults}
              onCompare={handleCompare}
            />
          </TabsContent>

          <TabsContent value="chat">
            <ChatInterface
              contractId={selectedContract}
              messages={chatMessages}
              onSendMessage={handleSendMessage}
              onClearHistory={handleClearChatHistory}
            />
          </TabsContent>

          <TabsContent value="history">
            <AnalysisHistory
              analysisResults={analysisResults}
              contracts={contracts}
              onViewAnalysis={handleViewAnalysis}
              onDeleteAnalysis={handleDeleteAnalysis}
              onDownloadReport={handleDownloadReport}
              onArchiveAnalysis={handleArchiveAnalysis}
            />
          </TabsContent>

          <TabsContent value="dashboard" className="space-y-6">
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
                      <p className="text-2xl font-bold">{analysisResults.length}</p>
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
                        {analysisResults.reduce((sum, a) => sum + a.riskClauses.length, 0)}
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
                        {Math.round(analysisResults.reduce((sum, a) => sum + (a.processingTimeMs || 0), 0) / 1000)}s
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
                      <div key={result.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div>
                          <p className="font-medium text-sm">분석 #{result.id.slice(-6)}</p>
                          <p className="text-xs text-gray-500">
                            {result.createdAt.toLocaleDateString('ko-KR')}
                          </p>
                        </div>
                        <Badge className={
                          result.riskLevel === RiskLevel.CRITICAL ? 'bg-red-100 text-red-800' :
                          result.riskLevel === RiskLevel.HIGH ? 'bg-orange-100 text-orange-800' :
                          result.riskLevel === RiskLevel.MEDIUM ? 'bg-yellow-100 text-yellow-800' :
                          'bg-green-100 text-green-800'
                        }>
                          {result.riskLevel === RiskLevel.CRITICAL ? '매우 높음' :
                           result.riskLevel === RiskLevel.HIGH ? '높음' :
                           result.riskLevel === RiskLevel.MEDIUM ? '보통' : '낮음'}
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
                    {[RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW].map(level => {
                      const count = analysisResults.filter(a => a.riskLevel === level).length;
                      const percentage = analysisResults.length > 0 ? (count / analysisResults.length) * 100 : 0;
                      const label = level === RiskLevel.CRITICAL ? '매우 높음' :
                                   level === RiskLevel.HIGH ? '높음' :
                                   level === RiskLevel.MEDIUM ? '보통' : '낮음';
                      const color = level === RiskLevel.CRITICAL ? 'bg-red-500' :
                                   level === RiskLevel.HIGH ? 'bg-orange-500' :
                                   level === RiskLevel.MEDIUM ? 'bg-yellow-500' : 'bg-green-500';
                      
                      return (
                        <div key={level} className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <div className={`w-3 h-3 rounded-full ${color}`}></div>
                            <span className="text-sm">{label}</span>
                          </div>
                          <div className="flex items-center space-x-2">
                            <div className="w-20 bg-gray-200 rounded-full h-2">
                              <div
                                className={`h-2 rounded-full ${color}`}
                                style={{ width: `${percentage}%` }}
                              ></div>
                            </div>
                            <span className="text-sm font-medium w-8">{count}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

export default Dashboard;