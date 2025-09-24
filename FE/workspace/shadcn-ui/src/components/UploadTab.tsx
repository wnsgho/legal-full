import React from 'react';
import FileUpload from "@/components/FileUpload";
import AnalysisProgress from "@/components/AnalysisProgress";
import { Contract, AnalysisResult } from "@/types";

interface UploadTabProps {
  handleFileUpload: (files: File[]) => void;
  contracts: Contract[];
  isUploading: boolean;
  uploadProgress: number;
  handlePipelineStart: (pipelineId: string, fileInfo: any) => void;
  analysisResults: AnalysisResult[];
  handleRetryAnalysis: (analysisId: string) => void;
  handleViewResult: (analysisId: string) => void;
  currentAnalysis: {
    id: string;
    progress: number;
    stage: string;
  } | undefined;
  pipelineId: string | undefined;
  handleAnalysisComplete: (result: AnalysisResult) => void;
}

const UploadTab: React.FC<UploadTabProps> = ({
  handleFileUpload,
  contracts,
  isUploading,
  uploadProgress,
  handlePipelineStart,
  analysisResults,
  handleRetryAnalysis,
  handleViewResult,
  currentAnalysis,
  pipelineId,
  handleAnalysisComplete,
}) => {
  return (
    <div className="space-y-6">
      <FileUpload
        onFileUpload={handleFileUpload}
        uploadedContracts={contracts}
        isUploading={isUploading}
        uploadProgress={uploadProgress}
        onPipelineStart={handlePipelineStart}
      />
      <AnalysisProgress
        analysisResults={analysisResults}
        onRetryAnalysis={handleRetryAnalysis}
        onViewResult={handleViewResult}
        currentAnalysis={currentAnalysis}
        pipelineId={pipelineId}
        onAnalysisComplete={handleAnalysisComplete}
      />
    </div>
  );
};

export default UploadTab;
