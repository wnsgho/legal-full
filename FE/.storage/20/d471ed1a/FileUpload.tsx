import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, X, CheckCircle, AlertCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Contract, ContractStatus } from '@/types';

interface FileUploadProps {
  onFileUpload: (files: File[]) => void;
  uploadedContracts: Contract[];
  isUploading: boolean;
  uploadProgress: number;
}

const FileUpload: React.FC<FileUploadProps> = ({
  onFileUpload,
  uploadedContracts,
  isUploading,
  uploadProgress
}) => {
  const [dragActive, setDragActive] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    onFileUpload(acceptedFiles);
  }, [onFileUpload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']
    },
    multiple: true,
    maxSize: 10 * 1024 * 1024, // 10MB
    onDragEnter: () => setDragActive(true),
    onDragLeave: () => setDragActive(false)
  });

  const getStatusIcon = (status: ContractStatus) => {
    switch (status) {
      case ContractStatus.COMPLETED:
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case ContractStatus.PROCESSING:
        return <div className="h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />;
      case ContractStatus.FAILED:
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <File className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: ContractStatus) => {
    const variants = {
      [ContractStatus.COMPLETED]: 'default',
      [ContractStatus.PROCESSING]: 'secondary',
      [ContractStatus.UPLOADING]: 'secondary',
      [ContractStatus.UPLOADED]: 'outline',
      [ContractStatus.FAILED]: 'destructive'
    } as const;

    const labels = {
      [ContractStatus.COMPLETED]: '완료',
      [ContractStatus.PROCESSING]: '분석중',
      [ContractStatus.UPLOADING]: '업로드중',
      [ContractStatus.UPLOADED]: '업로드됨',
      [ContractStatus.FAILED]: '실패'
    };

    return (
      <Badge variant={variants[status]}>
        {labels[status]}
      </Badge>
    );
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6">
      {/* Upload Zone */}
      <Card className={`transition-all duration-200 ${isDragActive || dragActive ? 'border-blue-500 bg-blue-50' : 'border-dashed border-gray-300'}`}>
        <CardContent className="p-8">
          <div
            {...getRootProps()}
            className={`text-center cursor-pointer transition-colors duration-200 ${
              isDragActive ? 'text-blue-600' : 'text-gray-600'
            }`}
          >
            <input {...getInputProps()} />
            <Upload className={`mx-auto h-12 w-12 mb-4 ${isDragActive ? 'text-blue-500' : 'text-gray-400'}`} />
            <h3 className="text-lg font-semibold mb-2">
              {isDragActive ? '파일을 여기에 놓아주세요' : '계약서 파일을 업로드하세요'}
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              PDF, Word, 이미지 파일을 드래그하거나 클릭하여 선택하세요
            </p>
            <p className="text-xs text-gray-400">
              지원 형식: PDF, DOC, DOCX, PNG, JPG, JPEG (최대 10MB)
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
                <div key={contract.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(contract.status)}
                    <div>
                      <p className="font-medium text-sm">{contract.fileName}</p>
                      <p className="text-xs text-gray-500">
                        {formatFileSize(contract.fileSize)} • {contract.uploadedAt.toLocaleDateString('ko-KR')}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {getStatusBadge(contract.status)}
                    {contract.status === ContractStatus.COMPLETED && (
                      <Button variant="outline" size="sm">
                        분석 보기
                      </Button>
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