

import openai
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any
import logging
import glob

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleGPTRiskAnalyzer:
    """간단한 GPT 위험분석기"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        초기화
        
        Args:
            api_key: OpenAI API 키 (없으면 환경변수에서 로드)
            model: 사용할 GPT 모델 (없으면 환경변수 OPENAI_GPT_MODEL 또는 기본값 gpt-4.1-2025-04-14 사용)
        """
        if model is None:
            model = os.getenv("OPENAI_GPT_MODEL", "gpt-4.1-2025-04-14")
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API 키가 필요합니다. 환경변수 OPENAI_API_KEY를 설정하거나 직접 전달하세요.")
        
        self.model = model
        self.client = openai.OpenAI(api_key=self.api_key)
        
        logger.info(f"SimpleGPTRiskAnalyzer 초기화 완료 - 모델: {self.model}")
    
    def analyze_contract(self, contract_text: str, contract_name: str = "계약서") -> Dict[str, Any]:
        """
        계약서 위험분석 수행
        
        Args:
            contract_text: 계약서 원문
            contract_name: 계약서명
            
        Returns:
            분석 결과 딕셔너리
        """
        try:
            logger.info(f"계약서 위험분석 시작: {contract_name}")
            start_time = datetime.now()
            
            # GPT에게 위험분석 요청
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "주어진 계약서를 분석하여 위험요소를 식별하고 분석해주세요."
                    },
                    {
                        "role": "user", 
                        "content": f"다음 계약서를 위험분석해줘:\n\n{contract_text}"
                    }
                ],
                max_tokens=4000,
                temperature=0.1
            )
            
            analysis_result = response.choices[0].message.content
            end_time = datetime.now()
            analysis_time = (end_time - start_time).total_seconds()
            
            # 결과 구성
            result = {
                "contract_name": contract_name,
                "analysis_date": start_time.isoformat(),
                "analysis_time": analysis_time,
                "model_used": self.model,
                "analysis_result": analysis_result,
                "status": "SUCCESS"
            }
            
            logger.info(f"위험분석 완료 - 소요시간: {analysis_time:.2f}초")
            return result
            
        except Exception as e:
            logger.error(f"위험분석 실패: {str(e)}")
            return {
                "contract_name": contract_name,
                "analysis_date": datetime.now().isoformat(),
                "analysis_time": 0,
                "model_used": self.model,
                "analysis_result": f"분석 실패: {str(e)}",
                "status": "FAILED",
                "error": str(e)
            }
    
    
    def save_result(self, result: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        분석 결과를 JSON 파일로 저장
        
        Args:
            result: 분석 결과
            filename: 저장할 파일명 (없으면 자동 생성)
            
        Returns:
            저장된 파일 경로
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gpt_risk_analysis_{timestamp}.json"
        
        filepath = os.path.join("data", filename)
        os.makedirs("data", exist_ok=True)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"분석 결과 저장: {filepath}")
        return filepath

def get_latest_uploaded_file():
    """uploads 폴더에서 가장 최근 파일을 찾아서 로드"""
    # 현재 스크립트 위치에서 uploads 폴더 찾기
    current_dir = os.path.dirname(os.path.abspath(__file__))
    uploads_dir = os.path.join(current_dir, "..", "uploads")
    
    # uploads 폴더가 없으면 상위 디렉토리에서 찾기
    if not os.path.exists(uploads_dir):
        uploads_dir = os.path.join(current_dir, "..", "..", "uploads")
    
    if not os.path.exists(uploads_dir):
        return None, "uploads 폴더를 찾을 수 없습니다."
    
    # 모든 파일 찾기
    all_files = []
    for root, dirs, files in os.walk(uploads_dir):
        for file in files:
            if file.endswith(('.md', '.txt', '.json')):
                file_path = os.path.join(root, file)
                file_time = os.path.getmtime(file_path)
                all_files.append((file_path, file_time, file))
    
    if not all_files:
        return None, "uploads 폴더에 분석 가능한 파일이 없습니다."
    
    # 최근 파일 선택
    latest_file = max(all_files, key=lambda x: x[1])
    file_path, _, file_name = latest_file
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, file_name
    except Exception as e:
        return None, f"파일 읽기 실패: {str(e)}"

def main():
    """메인 실행 함수"""
    print("=== 간단한 GPT 위험분석 스크립트 ===")
    
    # OpenAI API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OpenAI API 키가 설정되지 않았습니다.")
        print("환경변수 OPENAI_API_KEY를 설정하거나 .env 파일에 추가하세요.")
        return
    
    # 분석기 초기화
    try:
        analyzer = SimpleGPTRiskAnalyzer(api_key=api_key)
        print("✅ GPT 위험분석기 초기화 완료")
    except Exception as e:
        print(f"❌ 분석기 초기화 실패: {e}")
        return
    
    # 최근 업로드된 파일 자동 로드
    print("\n📁 최근 업로드된 파일을 찾는 중...")
    contract_text, file_name = get_latest_uploaded_file()
    
    if contract_text is None:
        print(f"❌ {file_name}")
        print("수동으로 계약서를 입력하시겠습니까? (y/n): ", end="")
        choice = input().strip().lower()
        
        if choice in ['y', 'yes', '예']:
            print("\n계약서 원문을 입력하세요 (여러 줄 입력 후 빈 줄로 종료):")
            contract_lines = []
            while True:
                line = input()
                if line.strip() == "":
                    break
                contract_lines.append(line)
            
            if not contract_lines:
                print("❌ 계약서 내용이 입력되지 않았습니다.")
                return
            
            contract_text = "\n".join(contract_lines)
            file_name = "수동입력계약서"
        else:
            return
    
    print(f"✅ 파일 로드 완료: {file_name}")
    contract_name = input(f"계약서명을 입력하세요 (기본값: {file_name}): ").strip() or file_name
    
    # 기본 위험분석 수행
    print("\n🔍 위험분석을 시작합니다...")
    result = analyzer.analyze_contract(contract_text, contract_name)
    
    # 결과 출력
    print("\n" + "="*50)
    print("📊 분석 결과")
    print("="*50)
    print(f"계약서명: {result['contract_name']}")
    print(f"분석일시: {result['analysis_date']}")
    print(f"소요시간: {result['analysis_time']:.2f}초")
    print(f"사용모델: {result['model_used']}")
    print(f"상태: {result['status']}")
    
    if result['status'] == 'SUCCESS':
        print("\n📝 분석 내용:")
        print("-" * 30)
        print(result['analysis_result'])
    else:
        print(f"\n❌ 분석 실패: {result.get('error', '알 수 없는 오류')}")
    
    # 결과 저장 여부 확인
    save_choice = input("\n결과를 파일로 저장하시겠습니까? (y/n): ").strip().lower()
    if save_choice in ['y', 'yes', '예']:
        filepath = analyzer.save_result(result)
        print(f"✅ 결과가 저장되었습니다: {filepath}")

if __name__ == "__main__":
    main()
