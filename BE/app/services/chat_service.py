import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import HTTPException

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.core.dependencies import get_rag_system, get_neo4j_driver

logger = logging.getLogger(__name__)

def load_risk_checklist():
    """Load risk checklist from a file."""
    try:
        # The file is located relative to the BE directory
        risk_file = Path(__file__).parent.parent.parent / "위험조항.txt"

        if risk_file.exists():
            with open(risk_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    risk_items = [item.strip() for item in content.split('\n') if item.strip()]
                    return '\n'.join([f"{i+1}. {item}" for i, item in enumerate(risk_items)])
        else:
            logger.warning(f"⚠️ Could not find 위험조항.txt at: {risk_file.absolute()}")
            return "Could not load risk checklist."
    except Exception as e:
        logger.error(f"❌ Failed to load risk checklist: {e}")
        return "Could not load risk checklist."


class ChatService:
    def __init__(self):
        pass

    async def process_chat_request(self, request: ChatRequest) -> ChatResponse:
        """
        Processes a chat request by routing it to the appropriate chat mode.
        """
        start_time = datetime.now()
        try:
            if request.chat_mode == "rag":
                return await self._chat_rag(request, start_time)
            elif request.chat_mode == "openai":
                return await self._chat_openai_basic(request, start_time)
            else:
                raise HTTPException(status_code=400, detail="Unsupported chat mode.")
        except Exception as e:
            logger.error(f"Chat processing failed: {e}", exc_info=True)
            processing_time = (datetime.now() - start_time).total_seconds()
            return ChatResponse(
                success=False,
                answer=f"An error occurred: {str(e)}",
                context_count=0,
                processing_time=processing_time,
            )

    async def _chat_rag(self, request: ChatRequest, start_time: datetime) -> ChatResponse:
        """Handles chat requests using the RAG system."""
        rag_system = get_rag_system()
        neo4j_driver = get_neo4j_driver()

        if not rag_system or not neo4j_driver:
            raise HTTPException(status_code=500, detail="RAG system is not available.")

        try:
            from experiment.run_questions_v3_with_concept import concept_enhanced_hybrid_retrieve

            search_result = concept_enhanced_hybrid_retrieve(
                request.question,
                rag_system["enhanced_lkg_retriever"],
                rag_system["hippo_retriever"],
                rag_system["llm_generator"],
                neo4j_driver,
            )

            sorted_context, context_ids = search_result if search_result and len(search_result) == 2 else (None, [])
            context_count = len(context_ids) if context_ids else 0

            if sorted_context:
                risk_checklist = load_risk_checklist()
                system_instruction = (
                    "당신은 대한민국의 고급 계약서 분석 전문가입니다. 추출된 정보와 질문을 꼼꼼히 분석하고 답변해야 합니다. "
                    "지식 그래프 정보가 충분하지 않다면 자신의 지식을 활용해서 답변할 수 있습니다. "
                    "답변은 'Thought: '로 시작하여 추론 과정을 단계별로 설명하고, "
                    "'Answer: '로 끝나며 간결하고 명확한 답변을 제공해야 합니다. "
                    "모든 답변은 한국어로 해주세요.\n\n"
                    f"=== 계약서 위험조항 체크리스트 ===\n{risk_checklist}\n"
                    "위 체크리스트를 참고하여 계약서의 잠재적 위험요소를 종합적으로 분석하세요."
                )

                messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": f"{sorted_context}\n\n{request.question}"},
                ]

                result = rag_system["llm_generator"].generate_response(
                    messages,
                    max_new_tokens=request.max_tokens,
                    temperature=request.temperature,
                )
            else:
                result = "No relevant context found to generate an answer."

            processing_time = (datetime.now() - start_time).total_seconds()
            return ChatResponse(
                success=True,
                answer=result or "Could not generate an answer.",
                context_count=context_count,
                processing_time=processing_time,
            )

        except Exception as e:
            logger.error(f"RAG chat failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"RAG chat processing error: {e}")

    async def _chat_openai_basic(self, request: ChatRequest, start_time: datetime) -> ChatResponse:
        """Handles chat requests using a simple OpenAI call."""
        try:
            from experiment.simple_openai_chat import SimpleOpenAIChat

            chat_instance = SimpleOpenAIChat()
            result = chat_instance.chat(request.question, request.file_id)

            processing_time = (datetime.now() - start_time).total_seconds()

            if result.get("success", False):
                return ChatResponse(
                    success=True,
                    answer=result["answer"],
                    context_count=0,
                    processing_time=processing_time,
                )
            else:
                error_message = result.get('error', 'Unknown OpenAI chat error')
                raise HTTPException(status_code=500, detail=f"OpenAI chat error: {error_message}")

        except Exception as e:
            logger.error(f"OpenAI basic chat failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"OpenAI basic chat processing error: {e}")

chat_service = ChatService()

def get_chat_service() -> ChatService:
    return chat_service