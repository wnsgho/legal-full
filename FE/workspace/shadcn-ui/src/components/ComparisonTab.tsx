import React from 'react';
import ComparisonView from "@/components/ComparisonView";
import { AnalysisResult, ComparisonResult } from "@/types";

interface ComparisonTabProps {
  analysisResults: AnalysisResult[];
  handleCompare: (analysisId1: string, analysisId2: string) => ComparisonResult;
}

const ComparisonTab: React.FC<ComparisonTabProps> = ({
  analysisResults,
  handleCompare,
}) => {
  return (
    <ComparisonView
      analysisResults={analysisResults}
      onCompare={handleCompare}
    />
  );
};

export default ComparisonTab;
