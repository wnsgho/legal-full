import React from 'react';
import { Badge } from "@/components/ui/badge";
import { Shield, Users } from "lucide-react";

interface DashboardHeaderProps {
  systemStatus: {
    rag_system_loaded: boolean;
    neo4j_connected: boolean;
  } | null;
}

const DashboardHeader: React.FC<DashboardHeaderProps> = ({ systemStatus }) => {
  return (
    <header className="bg-white border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-3">
            <Shield className="h-8 w-8 text-blue-600" />
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                계약서 분석 AI
              </h1>
              <p className="text-sm text-gray-500">
                스마트 계약서 리스크 분석 서비스
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            {systemStatus && (
              <div className="flex items-center space-x-2">
                <Badge
                  variant={
                    systemStatus.rag_system_loaded ? "default" : "destructive"
                  }
                  className="text-xs"
                >
                  RAG:{" "}
                  {systemStatus.rag_system_loaded ? "연결됨" : "연결 안됨"}
                </Badge>
                <Badge
                  variant={
                    systemStatus.neo4j_connected ? "default" : "destructive"
                  }
                  className="text-xs"
                >
                  Neo4j:{" "}
                  {systemStatus.neo4j_connected ? "연결됨" : "연결 안됨"}
                </Badge>
              </div>
            )}
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
  );
};

export default DashboardHeader;
