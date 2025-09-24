import React from 'react';
import AnalysisHistory from "@/components/AnalysisHistory";
import { AnalysisResult, Contract } from "@/types";

interface HistoryTabProps {
  analysisResults: AnalysisResult[];
  contracts: Contract[];
  handleViewAnalysis: (analysisId: string) => void;
  handleDeleteAnalysis: (analysisId: string) => void;
  handleDownloadReport: (analysisId: string) => void;
  handleArchiveAnalysis: (analysisId: string) => void;
}

const HistoryTab: React.FC<HistoryTabProps> = ({
  analysisResults,
  contracts,
  handleViewAnalysis,
  handleDeleteAnalysis,
  handleDownloadReport,
  handleArchiveAnalysis,
}) => {
  return (
    <AnalysisHistory
      analysisResults={analysisResults}
      contracts={contracts}
      onViewAnalysis={handleViewAnalysis}
      onDeleteAnalysis={handleDeleteAnalysis}
      onDownloadReport={handleDownloadReport}
      onArchiveAnalysis={handleArchiveAnalysis}
    />
  );
};

export default HistoryTab;
