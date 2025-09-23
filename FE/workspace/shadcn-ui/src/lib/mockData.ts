import { Contract, AnalysisResult, RiskClause, ChatMessage, RiskLevel, ClauseCategory, ContractStatus, AnalysisStatus } from '@/types';

export const mockContracts: Contract[] = [
  {
    id: '1',
    userId: 'user1',
    fileName: 'service_agreement_2024.pdf',
    fileSize: 2048576,
    fileType: 'application/pdf',
    uploadedAt: new Date('2024-01-15'),
    status: ContractStatus.COMPLETED,
    s3Key: 'contracts/user1/service_agreement_2024.pdf',
    ocrText: 'Service Agreement between Company A and Company B...'
  },
  {
    id: '2',
    userId: 'user1',
    fileName: 'employment_contract.docx',
    fileSize: 1024768,
    fileType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    uploadedAt: new Date('2024-01-10'),
    status: ContractStatus.COMPLETED,
    s3Key: 'contracts/user1/employment_contract.docx'
  },
  {
    id: '3',
    userId: 'user1',
    fileName: 'vendor_agreement_draft.pdf',
    fileSize: 3072384,
    fileType: 'application/pdf',
    uploadedAt: new Date('2024-01-20'),
    status: ContractStatus.PROCESSING,
    s3Key: 'contracts/user1/vendor_agreement_draft.pdf'
  }
];

export const mockRiskClauses: RiskClause[] = [
  {
    id: 'clause1',
    text: '계약 해지 시 30일 이내에 모든 자료를 반납하여야 하며, 위반 시 손해배상액은 계약금액의 200%로 한다.',
    riskLevel: RiskLevel.CRITICAL,
    category: ClauseCategory.TERMINATION,
    position: { start: 1250, end: 1320 },
    explanation: '계약 위반 시 과도한 손해배상 조항이 포함되어 있습니다. 일반적으로 손해배상액은 실제 손해액 또는 계약금액의 10-30% 수준이 적정합니다.',
    recommendation: '손해배상액을 계약금액의 30% 이하로 협상하거나, 실제 손해액 기준으로 변경할 것을 권장합니다.'
  },
  {
    id: 'clause2',
    text: '본 계약에 따른 모든 분쟁은 서울중앙지방법원을 전속관할로 한다.',
    riskLevel: RiskLevel.MEDIUM,
    category: ClauseCategory.DISPUTE_RESOLUTION,
    position: { start: 2100, end: 2150 },
    explanation: '분쟁 해결을 위한 전속관할 조항입니다. 회사 소재지와 다른 경우 소송 비용이 증가할 수 있습니다.',
    recommendation: '중재 조항 추가 또는 양 당사자 소재지 중 선택 가능하도록 수정을 고려해보세요.'
  },
  {
    id: 'clause3',
    text: '을은 계약 이행 중 알게 된 모든 정보에 대해 영구적인 비밀유지 의무를 진다.',
    riskLevel: RiskLevel.HIGH,
    category: ClauseCategory.CONFIDENTIALITY,
    position: { start: 1800, end: 1860 },
    explanation: '영구적인 비밀유지 의무는 과도할 수 있습니다. 일반적으로 3-5년 또는 정보의 성격에 따라 기간을 제한합니다.',
    recommendation: '비밀유지 기간을 계약 종료 후 3-5년으로 제한하거나, 정보 유형별로 차등 적용할 것을 권장합니다.'
  },
  {
    id: 'clause4',
    text: '대금 지급은 용역 완료 후 90일 이내에 이루어진다.',
    riskLevel: RiskLevel.LOW,
    category: ClauseCategory.PAYMENT,
    position: { start: 950, end: 990 },
    explanation: '90일 지급 조건은 일반적인 수준입니다만, 현금 흐름에 영향을 줄 수 있습니다.',
    recommendation: '가능하다면 30-60일로 단축 협상을 고려해보세요.'
  }
];

export const mockAnalysisResults: AnalysisResult[] = [
  {
    id: 'analysis1',
    contractId: '1',
    status: AnalysisStatus.COMPLETED,
    riskLevel: RiskLevel.HIGH,
    riskClauses: mockRiskClauses,
    summary: '본 계약서에는 4개의 주요 위험 요소가 발견되었습니다. 특히 과도한 손해배상 조항(200%)과 영구적 비밀유지 의무가 가장 큰 리스크로 평가됩니다. 전반적으로 상대방에게 유리한 조건들이 많아 재협상이 필요합니다.',
    recommendations: [
      '손해배상액을 계약금액의 30% 이하로 제한',
      '비밀유지 기간을 계약 종료 후 5년으로 제한',
      '분쟁 해결 방법에 중재 조항 추가 검토',
      '지급 조건을 60일 이내로 단축 협상'
    ],
    aiModel: 'GPT-4',
    confidence: 0.92,
    createdAt: new Date('2024-01-15T10:30:00'),
    processingTimeMs: 15000
  },
  {
    id: 'analysis2',
    contractId: '2',
    status: AnalysisStatus.COMPLETED,
    riskLevel: RiskLevel.MEDIUM,
    riskClauses: mockRiskClauses.slice(0, 2),
    summary: '고용 계약서로서 전반적으로 표준적인 조건들이 포함되어 있습니다. 일부 개선 가능한 조항들이 있으나 큰 위험 요소는 없습니다.',
    recommendations: [
      '경업금지 조항의 지역적 범위 명확화',
      '퇴직금 산정 기준 구체화'
    ],
    aiModel: 'GPT-4',
    confidence: 0.88,
    createdAt: new Date('2024-01-10T14:20:00'),
    processingTimeMs: 12000
  }
];

export const mockChatMessages: ChatMessage[] = [
  {
    id: 'msg1',
    contractId: '1',
    message: '이 계약서에서 가장 위험한 조항이 무엇인가요?',
    response: '분석 결과, 가장 위험한 조항은 "계약 위반 시 손해배상액이 계약금액의 200%"라는 부분입니다. 이는 일반적인 손해배상 기준(10-30%)을 크게 초과하는 과도한 조건으로, 실제 분쟁 발생 시 상당한 재정적 부담이 될 수 있습니다. 이 조항에 대한 재협상을 강력히 권장합니다.',
    isUserMessage: true,
    createdAt: new Date('2024-01-15T11:00:00')
  },
  {
    id: 'msg2',
    contractId: '1',
    message: '비밀유지 조항은 어떤가요?',
    response: '비밀유지 조항에서 "영구적인 비밀유지 의무"라는 표현이 문제가 될 수 있습니다. 일반적으로 비밀유지 의무는 계약 종료 후 3-5년으로 제한하는 것이 합리적입니다. 영구적 의무는 과도하며, 향후 사업 활동에 제약이 될 수 있으므로 기간 제한을 두는 것을 권장합니다.',
    isUserMessage: true,
    createdAt: new Date('2024-01-15T11:05:00')
  }
];

export const contractSampleText = `
서비스 제공 계약서

제1조 (목적)
본 계약은 갑과 을 간의 서비스 제공에 관한 제반 사항을 규정함을 목적으로 한다.

제2조 (계약 기간)
본 계약의 유효기간은 2024년 1월 1일부터 2024년 12월 31일까지로 한다.

제3조 (대금 지급)
갑은 을이 제공한 서비스에 대한 대금을 용역 완료 후 90일 이내에 지급한다.

제4조 (비밀유지)
을은 계약 이행 중 알게 된 모든 정보에 대해 영구적인 비밀유지 의무를 진다.

제5조 (계약 해지)
계약 해지 시 30일 이내에 모든 자료를 반납하여야 하며, 위반 시 손해배상액은 계약금액의 200%로 한다.

제6조 (분쟁 해결)
본 계약에 따른 모든 분쟁은 서울중앙지방법원을 전속관할로 한다.

제7조 (기타)
본 계약에 명시되지 않은 사항은 관련 법령에 따른다.

갑: (주)에이컴퍼니
을: (주)비컴퍼니

2024년 1월 15일
`;