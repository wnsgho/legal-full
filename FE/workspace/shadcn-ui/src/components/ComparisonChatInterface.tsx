import React, { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Send,
  Bot,
  User,
  MessageCircle,
  Trash2,
  Database,
  Zap,
} from "lucide-react";
import { ChatMessage } from "@/types";
import { api } from "@/services/api";
import { useToast } from "@/hooks/use-toast";

interface ComparisonChatInterfaceProps {
  contractId: string;
  messages: ChatMessage[];
  onSendMessage: (message: string) => void;
  onClearHistory: () => void;
  isLoading?: boolean;
}

interface ComparisonMessage {
  id: string;
  userMessage: string;
  ragResponse?: string;
  openaiResponse?: string;
  timestamp: Date;
}

const ComparisonChatInterface: React.FC<ComparisonChatInterfaceProps> = ({
  contractId,
  messages,
  onSendMessage,
  onClearHistory,
  isLoading = false,
}) => {
  const [inputMessage, setInputMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [comparisonMessages, setComparisonMessages] = useState<
    ComparisonMessage[]
  >([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [comparisonMessages]);

  const handleSendMessage = async () => {
    if (inputMessage.trim() && !isLoading && !isSending) {
      const message = inputMessage.trim();
      setInputMessage("");
      setIsSending(true);

      try {
        // 사용자 메시지 추가
        onSendMessage(message);

        // 새로운 비교 메시지 생성
        const comparisonId = `comp_${Date.now()}`;
        const newComparisonMessage: ComparisonMessage = {
          id: comparisonId,
          userMessage: message,
          timestamp: new Date(),
        };

        setComparisonMessages((prev) => [...prev, newComparisonMessage]);

        // 먼저 RAG 시스템으로 요청 (기존 방식)
        let ragAnswer = "";
        let openaiAnswer = "";

        try {
          console.log("RAG 채팅 요청 시작:", { message, contractId });
          const ragResponse = await api.sendRAGChatMessage(message, contractId);
          if (ragResponse.success) {
            ragAnswer = ragResponse.answer;
            console.log("RAG 응답 성공:", ragAnswer.substring(0, 100) + "...");
          } else {
            ragAnswer = "RAG 시스템에서 오류가 발생했습니다.";
            console.error("RAG 응답 실패:", ragResponse);
          }
        } catch (error) {
          console.error("RAG 요청 오류:", error);
          ragAnswer = "RAG 시스템에서 오류가 발생했습니다.";
        }

        // 그 다음 OpenAI 기본 채팅으로 요청
        try {
          console.log("OpenAI 기본 채팅 요청 시작:", { message, contractId });
          const openaiResponse = await api.sendOpenAIChatMessage(
            message,
            contractId
          );
          if (openaiResponse.success) {
            openaiAnswer = openaiResponse.answer;
            console.log(
              "OpenAI 응답 성공:",
              openaiAnswer.substring(0, 100) + "..."
            );
          } else {
            openaiAnswer = "OpenAI 기본 채팅에서 오류가 발생했습니다.";
            console.error("OpenAI 응답 실패:", openaiResponse);
          }
        } catch (error) {
          console.error("OpenAI 요청 오류:", error);
          openaiAnswer = "OpenAI 기본 채팅에서 오류가 발생했습니다.";
        }

        // 비교 메시지 업데이트
        setComparisonMessages((prev) =>
          prev.map((msg) =>
            msg.id === comparisonId
              ? { ...msg, ragResponse: ragAnswer, openaiResponse: openaiAnswer }
              : msg
          )
        );

        // 기존 채팅에도 RAG 응답 추가 (호환성 유지)
        onSendMessage(`AI: ${ragAnswer}`);
      } catch (error) {
        console.error("Comparison chat error:", error);
        toast({
          title: "채팅 오류",
          description: "AI와의 대화 중 오류가 발생했습니다.",
          variant: "destructive",
        });
      } finally {
        setIsSending(false);
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClearHistory = async () => {
    try {
      await api.clearChatHistory();
      onClearHistory();
      setComparisonMessages([]);
      toast({
        title: "대화 기록 삭제",
        description: "채팅 기록이 삭제되었습니다.",
      });
    } catch (error) {
      console.error("Clear history error:", error);
      toast({
        title: "삭제 실패",
        description: "대화 기록 삭제 중 오류가 발생했습니다.",
        variant: "destructive",
      });
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString("ko-KR", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const suggestedQuestions = [
    "이 계약서에서 가장 위험한 조항이 무엇인가요?",
    "비밀유지 조항은 어떤 내용인가요?",
    "계약 해지 조건을 설명해주세요.",
    "손해배상 관련 조항이 있나요?",
    "지급 조건은 어떻게 되나요?",
  ];

  return (
    <div className="h-[600px] flex flex-col">
      <Card className="flex-1 flex flex-col">
        <CardHeader className="flex-shrink-0">
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <MessageCircle className="h-5 w-5" />
              <span>AI 채팅 비교</span>
            </div>
            <div className="flex items-center space-x-2">
              <Badge variant="outline" className="text-xs">
                계약서 #{contractId.slice(-6)}
              </Badge>
              {comparisonMessages.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleClearHistory}
                  className="text-gray-500 hover:text-red-500"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
          </CardTitle>
        </CardHeader>

        <CardContent className="flex-1 flex flex-col p-0">
          <ScrollArea className="flex-1 p-4">
            {comparisonMessages.length === 0 ? (
              <div className="space-y-4">
                <div className="text-center text-gray-500 mb-6">
                  <Bot className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <p className="text-lg font-medium mb-2">
                    AI 채팅 비교를 시작해보세요
                  </p>
                  <p className="text-sm">
                    RAG 시스템과 OpenAI 기본 채팅의 답변을 비교해보세요.
                  </p>
                </div>

                <div>
                  <p className="text-sm font-medium text-gray-700 mb-3">
                    추천 질문:
                  </p>
                  <div className="space-y-2">
                    {suggestedQuestions.map((question, index) => (
                      <Button
                        key={index}
                        variant="outline"
                        size="sm"
                        className="w-full justify-start text-left h-auto py-2 px-3"
                        onClick={() => setInputMessage(question)}
                      >
                        <span className="text-xs text-gray-600">
                          {question}
                        </span>
                      </Button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                {comparisonMessages.map((message) => (
                  <div key={message.id} className="space-y-4">
                    {/* 사용자 메시지 */}
                    <div className="flex justify-end">
                      <div className="flex items-start space-x-2 max-w-[80%]">
                        <div className="bg-blue-500 text-white rounded-lg px-4 py-2">
                          <p className="text-sm">{message.userMessage}</p>
                          <p className="text-xs opacity-75 mt-1">
                            {formatTime(message.timestamp)}
                          </p>
                        </div>
                        <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                          <User className="h-4 w-4 text-blue-600" />
                        </div>
                      </div>
                    </div>

                    {/* AI 응답 비교 */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      {/* RAG 응답 */}
                      <div className="space-y-2">
                        <div className="flex items-center space-x-2 mb-2">
                          <Database className="h-4 w-4 text-blue-600" />
                          <span className="text-sm font-semibold text-blue-800">
                            RAG 시스템
                          </span>
                          <Badge variant="outline" className="text-xs">
                            지식그래프 + LLM
                          </Badge>
                        </div>
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                          {message.ragResponse ? (
                            <div className="space-y-3">
                              {(() => {
                                const response = message.ragResponse;
                                const thoughtMatch = response.match(
                                  /Thought:\s*(.*?)(?=Answer:|$)/s
                                );
                                const answerMatch = response.match(
                                  /Answer:\s*(.*?)(?=Thought:|$)/s
                                );

                                if (thoughtMatch && answerMatch) {
                                  const thought = thoughtMatch[1].trim();
                                  const answer = answerMatch[1].trim();

                                  return (
                                    <div className="space-y-3">
                                      {/* Answer 부분 */}
                                      <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                                        <div className="flex items-center gap-2 mb-2">
                                          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                                          <span className="text-sm font-semibold text-green-800">
                                            답변
                                          </span>
                                        </div>
                                        <p className="text-sm text-green-800 leading-relaxed">
                                          {answer}
                                        </p>
                                      </div>

                                      {/* Thought 부분 */}
                                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                                        <div className="flex items-center gap-2 mb-2">
                                          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                                          <span className="text-sm font-semibold text-blue-800">
                                            사고 과정
                                          </span>
                                        </div>
                                        <p className="text-sm text-blue-800 leading-relaxed">
                                          {thought}
                                        </p>
                                      </div>
                                    </div>
                                  );
                                } else {
                                  return (
                                    <p className="text-sm text-gray-800 leading-relaxed">
                                      {response}
                                    </p>
                                  );
                                }
                              })()}
                            </div>
                          ) : (
                            <div className="flex items-center justify-center py-4">
                              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* OpenAI 기본 응답 */}
                      <div className="space-y-2">
                        <div className="flex items-center space-x-2 mb-2">
                          <Zap className="h-4 w-4 text-green-600" />
                          <span className="text-sm font-semibold text-green-800">
                            OpenAI 기본
                          </span>
                          <Badge variant="outline" className="text-xs">
                            GPT-4 Only
                          </Badge>
                        </div>
                        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                          {message.openaiResponse ? (
                            <p className="text-sm text-gray-800 leading-relaxed">
                              {message.openaiResponse}
                            </p>
                          ) : (
                            <div className="flex items-center justify-center py-4">
                              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-600"></div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}

                {/* Loading indicator */}
                {(isLoading || isSending) && (
                  <div className="flex justify-center">
                    <div className="bg-gray-100 rounded-lg px-4 py-2">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div
                          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                          style={{ animationDelay: "0.1s" }}
                        ></div>
                        <div
                          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                          style={{ animationDelay: "0.2s" }}
                        ></div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
            <div ref={messagesEndRef} />
          </ScrollArea>

          {/* Input Area */}
          <div className="border-t p-4">
            <div className="flex space-x-2">
              <Input
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="계약서에 대해 궁금한 점을 물어보세요..."
                disabled={isLoading}
                className="flex-1"
              />
              <Button
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || isLoading || isSending}
                size="icon"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              * RAG 시스템과 OpenAI 기본 채팅의 답변을 비교할 수 있습니다.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ComparisonChatInterface;
