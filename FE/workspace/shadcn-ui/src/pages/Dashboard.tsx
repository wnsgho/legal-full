import React, { useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Upload,
  BarChart3,
  MessageSquare,
  History,
  GitCompare,
  TrendingUp,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import DashboardHeader from "@/components/DashboardHeader";
import UploadTab from "@/components/UploadTab";
import AnalysisTab from "@/components/AnalysisTab";
import ComparisonTab from "@/components/ComparisonTab";
import ChatTab from "@/components/ChatTab";
import HistoryTab from "@/components/HistoryTab";
import SummaryDashboardTab from "@/components/SummaryDashboardTab";
import { useDashboardStore } from "@/store/dashboardStore";

const Dashboard: React.FC = () => {
  const {
    contracts,
    analysisResults,
    chatMessages,
    isUploading,
    uploadProgress,
    currentAnalysis,
    selectedContract,
    viewMode,
    currentPipelineId,
    systemStatus,
    checkSystemStatus,
    checkPipelineExists,
    handlePipelineStart,
    handleAnalysisComplete,
    handleFileUpload,
    handleRetryAnalysis,
    handleViewResult,
    handleCompare,
    handleSendMessage,
    handleClearChatHistory,
    handleClauseClick,
    handleViewAnalysis,
    handleDeleteAnalysis,
    handleDownloadReport,
    handleArchiveAnalysis,
    setViewMode,
  } = useDashboardStore();
  const { toast } = useToast();

  useEffect(() => {
    checkSystemStatus();
  }, [checkSystemStatus]);

  useEffect(() => {
    checkPipelineExists();
  }, [currentPipelineId, checkPipelineExists, toast]);

  const currentAnalysisResult = analysisResults.find(
    (a) => a.contractId === selectedContract
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <DashboardHeader systemStatus={systemStatus} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs defaultValue="upload" className="space-y-6">
          <TabsList className="grid w-full grid-cols-6">
            <TabsTrigger value="upload" className="flex items-center space-x-2">
              <Upload className="h-4 w-4" />
              <span>업로드</span>
            </TabsTrigger>
            <TabsTrigger
              value="analysis"
              className="flex items-center space-x-2"
            >
              <BarChart3 className="h-4 w-4" />
              <span>분석 결과</span>
            </TabsTrigger>
            <TabsTrigger
              value="comparison"
              className="flex items-center space-x-2"
            >
              <GitCompare className="h-4 w-4" />
              <span>비교 분석</span>
            </TabsTrigger>
            <TabsTrigger value="chat" className="flex items-center space-x-2">
              <MessageSquare className="h-4 w-4" />
              <span>AI 상담</span>
            </TabsTrigger>
            <TabsTrigger
              value="history"
              className="flex items-center space-x-2"
            >
              <History className="h-4 w-4" />
              <span>분석 기록</span>
            </TabsTrigger>
            <TabsTrigger
              value="dashboard"
              className="flex items-center space-x-2"
            >
              <TrendingUp className="h-4 w-4" />
              <span>대시보드</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="upload" className="space-y-6">
            <UploadTab
              handleFileUpload={handleFileUpload}
              contracts={contracts}
              isUploading={isUploading}
              uploadProgress={uploadProgress}
              handlePipelineStart={handlePipelineStart}
              analysisResults={analysisResults}
              handleRetryAnalysis={handleRetryAnalysis}
              handleViewResult={handleViewResult}
              currentAnalysis={currentAnalysis}
              pipelineId={currentPipelineId}
              handleAnalysisComplete={handleAnalysisComplete}
            />
          </TabsContent>

          <TabsContent value="analysis" className="space-y-6">
            <AnalysisTab
              viewMode={viewMode}
              setViewMode={setViewMode}
              currentAnalysisResult={currentAnalysisResult}
              handleClauseClick={handleClauseClick}
            />
          </TabsContent>

          <TabsContent value="comparison">
            <ComparisonTab
              analysisResults={analysisResults}
              onCompare={handleCompare}
            />
          </TabsContent>

          <TabsContent value="chat">
            <ChatTab
              selectedContract={selectedContract}
              chatMessages={chatMessages}
              handleSendMessage={handleSendMessage}
              handleClearChatHistory={handleClearChatHistory}
            />
          </TabsContent>

          <TabsContent value="history">
            <HistoryTab
              analysisResults={analysisResults}
              contracts={contracts}
              onViewAnalysis={handleViewAnalysis}
              onDeleteAnalysis={handleDeleteAnalysis}
              onDownloadReport={handleDownloadReport}
              onArchiveAnalysis={handleArchiveAnalysis}
            />
          </TabsContent>

          <TabsContent value="dashboard" className="space-y-6">
            <SummaryDashboardTab
              contracts={contracts}
              analysisResults={analysisResults}
            />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

export default Dashboard;
