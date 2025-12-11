import React, { useCallback, useState, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import {
  Upload,
  File,
  X,
  CheckCircle,
  AlertCircle,
  Database,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Contract, ContractStatus } from "@/types";
import { api } from "@/services/api";
import { useToast } from "@/hooks/use-toast";

interface Neo4jDatabase {
  name: string;
  status: string;
  default: boolean;
}

interface FileUploadProps {
  onFileUpload: (files: File[]) => void;
  uploadedContracts: Contract[];
  isUploading: boolean;
  uploadProgress: number;
  onPipelineStart?: (
    pipelineId: string,
    fileInfo: Record<string, unknown>
  ) => void;
  onPipelineComplete?: (pipelineId: string, contractId: string) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({
  onFileUpload,
  uploadedContracts,
  isUploading,
  uploadProgress,
  onPipelineStart,
  onPipelineComplete,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [activePipelines, setActivePipelines] = useState<Map<string, string>>(
    new Map()
  ); // pipelineId -> contractId
  const [neo4jDatabase, setNeo4jDatabase] = useState<string>(
    import.meta.env.VITE_NEO4J_DATABASE || "neo4j"
  );
  const [neo4jDatabases, setNeo4jDatabases] = useState<Neo4jDatabase[]>([]);
  const [isLoadingDatabases, setIsLoadingDatabases] = useState(false);
  const { toast } = useToast();

  // Neo4j 데이터베이스 목록 로드
  const fetchNeo4jDatabases = useCallback(async () => {
    setIsLoadingDatabases(true);
    try {
      const response = await api.getNeo4jDatabases();
      if (response.success && response.databases) {
        setNeo4jDatabases(response.databases);
        // 기본 데이터베이스가 있고 현재 선택이 없으면 선택
        setNeo4jDatabase((currentDb) => {
          if (!currentDb || currentDb === "neo4j") {
            const defaultDb = response.databases.find((db) => db.default);
            return defaultDb?.name || currentDb;
          }
          return currentDb;
        });
      }
    } catch (error) {
      console.error("Neo4j 데이터베이스 목록 조회 실패:", error);
      // 실패 시 환경변수 값 사용
      setNeo4jDatabases([
        {
          name: import.meta.env.VITE_NEO4J_DATABASE || "neo4j",
          status: "online",
          default: true,
        },
      ]);
    } finally {
      setIsLoadingDatabases(false);
    }
  }, []);

  // 컴포넌트 마운트 시 데이터베이스 목록 로드
  useEffect(() => {
    fetchNeo4jDatabases();
  }, [fetchNeo4jDatabases]);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      try {
        // 첫 번째 파일만 처리 (현재는 단일 파일 업로드만 지원)
        const file = acceptedFiles[0];
        if (!file) return;

        // 파일 업로드 및 파이프라인 실행 (데이터베이스 이름 전달)
        const response = await api.uploadAndRunPipeline(file, 1, neo4jDatabase);

        if (response.success && response.data) {
          toast({
            title: "파일 업로드 성공",
            description: `파이프라인이 시작되었습니다. (DB: ${neo4jDatabase})`,
          });

          // 파이프라인 시작 콜백 호출
          if (onPipelineStart) {
            onPipelineStart(response.data.pipeline_id, response.data.file_info);
          }

          // 활성 파이프라인에 추가 (contractId는 file_id에서 추출)
          const contractId =
            response.data.file_info?.file_id || response.data.pipeline_id;
          setActivePipelines((prev) =>
            new Map(prev).set(response.data.pipeline_id, contractId)
          );

          // 기존 onFileUpload 콜백도 호출 (UI 업데이트용)
          onFileUpload(acceptedFiles);
        } else {
          throw new Error(response.message || "파일 업로드에 실패했습니다.");
        }
      } catch (error) {
        console.error("File upload error:", error);
        toast({
          title: "업로드 실패",
          description:
            error instanceof Error
              ? error.message
              : "파일 업로드 중 오류가 발생했습니다.",
          variant: "destructive",
        });
      }
    },
    [onFileUpload, onPipelineStart, toast, neo4jDatabase]
  );

  // 활성 파이프라인 상태 모니터링
  useEffect(() => {
    if (activePipelines.size === 0) return;

    const pollInterval = setInterval(async () => {
      for (const [pipelineId, contractId] of activePipelines) {
        try {
          const response = await api.getPipelineStatus(pipelineId);

          if (response.success) {
            if (response.status === "completed") {
              console.log(
                `✅ 파이프라인 완료 감지 - ID: ${pipelineId}, Contract: ${contractId}`
              );

              // 파이프라인 완료 콜백 호출
              if (onPipelineComplete) {
                onPipelineComplete(pipelineId, contractId);
              }

              // 활성 파이프라인에서 제거
              setActivePipelines((prev) => {
                const newMap = new Map(prev);
                newMap.delete(pipelineId);
                return newMap;
              });

              toast({
                title: "✅ 분석 완료",
                description: "계약서 분석이 완료되었습니다.",
              });
            } else if (response.status === "failed") {
              console.log(`❌ 파이프라인 실패 감지 - ID: ${pipelineId}`);

              // 활성 파이프라인에서 제거
              setActivePipelines((prev) => {
                const newMap = new Map(prev);
                newMap.delete(pipelineId);
                return newMap;
              });

              toast({
                title: "❌ 분석 실패",
                description: "파이프라인 실행이 실패했습니다.",
                variant: "destructive",
              });
            }
          }
        } catch (error) {
          console.error(
            `파이프라인 상태 확인 실패 - ID: ${pipelineId}:`,
            error
          );

          // 404 오류 시 파이프라인 제거 (서버 재시작 등)
          if (
            (error as { response?: { status?: number }; message?: string })
              ?.response?.status === 404 ||
            (
              error as { response?: { status?: number }; message?: string }
            )?.message?.includes("404")
          ) {
            setActivePipelines((prev) => {
              const newMap = new Map(prev);
              newMap.delete(pipelineId);
              return newMap;
            });
          }
        }
      }
    }, 2000); // 2초마다 폴링

    return () => clearInterval(pollInterval);
  }, [activePipelines, onPipelineComplete, toast]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/json": [".json"],
      "text/plain": [".txt"],
      "text/markdown": [".md"],
    },
    multiple: false, // 단일 파일만 업로드
    maxSize: 10 * 1024 * 1024, // 10MB
    onDragEnter: () => setDragActive(true),
    onDragLeave: () => setDragActive(false),
  });

  const getStatusIcon = (status: ContractStatus) => {
    switch (status) {
      case ContractStatus.COMPLETED:
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case ContractStatus.PROCESSING:
        return (
          <div className="h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        );
      case ContractStatus.FAILED:
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <File className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: ContractStatus) => {
    const variants = {
      [ContractStatus.COMPLETED]: "default",
      [ContractStatus.PROCESSING]: "secondary",
      [ContractStatus.UPLOADING]: "secondary",
      [ContractStatus.UPLOADED]: "outline",
      [ContractStatus.FAILED]: "destructive",
    } as const;

    const labels = {
      [ContractStatus.COMPLETED]: "✅ 완료",
      [ContractStatus.PROCESSING]: "🔄 분석중",
      [ContractStatus.UPLOADING]: "📤 업로드중",
      [ContractStatus.UPLOADED]: "📁 업로드됨",
      [ContractStatus.FAILED]: "❌ 실패",
    };

    return <Badge variant={variants[status]}>{labels[status]}</Badge>;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="space-y-6">
      {/* Neo4j Database Selection */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-gray-700">
              <Database className="h-5 w-5" />
              <Label htmlFor="neo4j-database" className="font-medium">
                Neo4j 데이터베이스
              </Label>
            </div>
            <div className="flex-1 max-w-xs">
              <Select
                value={neo4jDatabase}
                onValueChange={setNeo4jDatabase}
                disabled={isLoadingDatabases}
              >
                <SelectTrigger>
                  <SelectValue placeholder="데이터베이스 선택" />
                </SelectTrigger>
                <SelectContent>
                  {neo4jDatabases.map((db) => (
                    <SelectItem key={db.name} value={db.name}>
                      <div className="flex items-center space-x-2">
                        <span>{db.name}</span>
                        {db.status === "online" && (
                          <span className="text-xs text-green-500">●</span>
                        )}
                        {db.default && (
                          <Badge variant="outline" className="text-xs ml-1">
                            기본
                          </Badge>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={fetchNeo4jDatabases}
              disabled={isLoadingDatabases}
              title="데이터베이스 목록 새로고침"
            >
              <RefreshCw
                className={`h-4 w-4 ${
                  isLoadingDatabases ? "animate-spin" : ""
                }`}
              />
            </Button>
            <p className="text-xs text-gray-500">
              파이프라인 실행 시 사용할 데이터베이스
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Upload Zone */}
      <Card
        className={`transition-all duration-200 ${
          isDragActive || dragActive
            ? "border-blue-500 bg-blue-50"
            : "border-dashed border-gray-300"
        }`}
      >
        <CardContent className="p-8">
          <div
            {...getRootProps()}
            className={`text-center cursor-pointer transition-colors duration-200 ${
              isDragActive ? "text-blue-600" : "text-gray-600"
            }`}
          >
            <input {...getInputProps()} />
            <Upload
              className={`mx-auto h-12 w-12 mb-4 ${
                isDragActive ? "text-blue-500" : "text-gray-400"
              }`}
            />
            <h3 className="text-lg font-semibold mb-2">
              {isDragActive
                ? "파일을 여기에 놓아주세요"
                : "계약서 파일을 업로드하세요"}
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              JSON, TXT, MD 파일을 드래그하거나 클릭하여 선택하세요
            </p>
            <p className="text-xs text-gray-400">
              지원 형식: JSON, TXT, MD (최대 10MB)
            </p>
            <p className="text-xs text-blue-600 mt-2">
              데이터베이스: <span className="font-medium">{neo4jDatabase}</span>
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Upload Progress */}
      {isUploading && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-3">
              <div className="flex-1">
                <div className="flex justify-between text-sm mb-2">
                  <span>업로드 중...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <Progress value={uploadProgress} className="h-2" />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Uploaded Files List */}
      {uploadedContracts.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <h4 className="font-semibold mb-4">업로드된 계약서</h4>
            <div className="space-y-3">
              {uploadedContracts.map((contract) => (
                <div
                  key={contract.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(contract.status)}
                    <div>
                      <p className="font-medium text-sm">{contract.fileName}</p>
                      <p className="text-xs text-gray-500">
                        {formatFileSize(contract.fileSize)} •{" "}
                        {contract.uploadedAt.toLocaleDateString("ko-KR")}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {getStatusBadge(contract.status)}
                    {contract.status === ContractStatus.COMPLETED && (
                      <Button variant="outline" size="sm"></Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default FileUpload;
