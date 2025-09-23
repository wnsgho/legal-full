export enum UserRole {
  USER = 'user',
  ADMIN = 'admin',
  ENTERPRISE = 'enterprise'
}

export enum ContractStatus {
  UPLOADING = 'uploading',
  UPLOADED = 'uploaded',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

export enum AnalysisStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

export enum RiskLevel {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

export enum ClauseCategory {
  TERMINATION = 'termination',
  LIABILITY = 'liability',
  PAYMENT = 'payment',
  INTELLECTUAL_PROPERTY = 'intellectual_property',
  CONFIDENTIALITY = 'confidentiality',
  COMPLIANCE = 'compliance',
  DISPUTE_RESOLUTION = 'dispute_resolution'
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  subscription: string;
  createdAt: Date;
}

export interface Contract {
  id: string;
  userId: string;
  fileName: string;
  fileSize: number;
  fileType: string;
  uploadedAt: Date;
  status: ContractStatus;
  s3Key: string;
  ocrText?: string;
}

export interface TextPosition {
  start: number;
  end: number;
  line?: number;
}

export interface RiskClause {
  id: string;
  text: string;
  riskLevel: RiskLevel;
  category: ClauseCategory;
  position: TextPosition;
  explanation: string;
  recommendation: string;
}

export interface AnalysisResult {
  id: string;
  contractId: string;
  status: AnalysisStatus;
  riskLevel: RiskLevel;
  riskClauses: RiskClause[];
  summary: string;
  recommendations: string[];
  aiModel: string;
  confidence: number;
  createdAt: Date;
  processingTimeMs?: number;
}

export interface ChatMessage {
  id: string;
  contractId: string;
  message: string;
  response?: string;
  isUserMessage: boolean;
  createdAt: Date;
}

export interface ComparisonResult {
  id: string;
  analysisId1: string;
  analysisId2: string;
  differences: {
    added: RiskClause[];
    removed: RiskClause[];
    modified: RiskClause[];
  };
  riskLevelChange: {
    from: RiskLevel;
    to: RiskLevel;
  };
  summary: string;
  createdAt: Date;
}

export interface AnalysisParams {
  focusAreas?: ClauseCategory[];
  analysisDepth: 'basic' | 'detailed' | 'comprehensive';
  includeRecommendations: boolean;
}