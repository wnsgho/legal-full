import React, { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Bot, User, MessageCircle, Trash2 } from "lucide-react";
import { ChatMessage } from "@/types";
import { api } from "@/services/api";
import { useToast } from "@/hooks/use-toast";

interface ChatInterfaceProps {
  contractId: string;
  messages: ChatMessage[];
  onSendMessage: (message: string) => void;
  onClearHistory: () => void;
  isLoading?: boolean;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  contractId,
  messages,
  onSendMessage,
  onClearHistory,
  isLoading = false,
}) => {
  const [inputMessage, setInputMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (inputMessage.trim() && !isLoading && !isSending) {
      const message = inputMessage.trim();
      setInputMessage("");
      setIsSending(true);

      try {
        // 사용자 메시지 추가
        onSendMessage(message);

        // AI 응답 요청
        const response = await api.sendChatMessage(message);

        if (response.success && response.answer) {
          // AI 응답을 부모 컴포넌트에 전달
          onSendMessage(`AI: ${response.answer}`);
        } else {
          throw new Error(response.message || "AI 응답을 받을 수 없습니다.");
        }
      } catch (error) {
        console.error("Chat error:", error);
        toast({
          title: "채팅 오류",
          description:
            error instanceof Error
              ? error.message
              : "AI와의 대화 중 오류가 발생했습니다.",
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
    <Card className="h-[600px] flex flex-col">
      <CardHeader className="flex-shrink-0">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <MessageCircle className="h-5 w-5" />
            <span>계약서 AI 상담</span>
          </div>
          <div className="flex items-center space-x-2">
            <Badge variant="outline" className="text-xs">
              계약서 #{contractId.slice(-6)}
            </Badge>
            {messages.length > 0 && (
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
          {messages.length === 0 ? (
            <div className="space-y-4">
              <div className="text-center text-gray-500 mb-6">
                <Bot className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p className="text-lg font-medium mb-2">
                  AI 상담을 시작해보세요
                </p>
                <p className="text-sm">
                  계약서에 대한 궁금한 점을 언제든 물어보세요.
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
                      <span className="text-xs text-gray-600">{question}</span>
                    </Button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message) => (
                <div key={message.id} className="space-y-3">
                  {message.isUserMessage ? (
                    /* User Message */
                    <div className="flex justify-end">
                      <div className="flex items-start space-x-2 max-w-[80%]">
                        <div className="bg-blue-500 text-white rounded-lg px-4 py-2">
                          <p className="text-sm">{message.message}</p>
                          <p className="text-xs opacity-75 mt-1">
                            {formatTime(message.createdAt)}
                          </p>
                        </div>
                        <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                          <User className="h-4 w-4 text-blue-600" />
                        </div>
                      </div>
                    </div>
                  ) : (
                    /* AI Response */
                    <div className="flex justify-start">
                      <div className="flex items-start space-x-2 max-w-[80%]">
                        <div className="flex-shrink-0 w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
                          <Bot className="h-4 w-4 text-gray-600" />
                        </div>
                        <div className="bg-gray-100 rounded-lg px-4 py-2 w-full">
                          {(() => {
                            const response = message.response;
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
                                  {/* Answer 부분 - 위에 표시 */}
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

                                  {/* Thought 부분 - 아래에 표시 */}
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
                              // 기존 형식이 아닌 경우 그대로 표시
                              return (
                                <p className="text-sm text-gray-800 leading-relaxed">
                                  {response}
                                </p>
                              );
                            }
                          })()}
                          <p className="text-xs text-gray-500 mt-2">
                            {formatTime(message.createdAt)}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {/* Loading indicator */}
              {(isLoading || isSending) && (
                <div className="flex justify-start">
                  <div className="flex items-start space-x-2">
                    <div className="flex-shrink-0 w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
                      <Bot className="h-4 w-4 text-gray-600" />
                    </div>
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
            * AI 응답은 참고용이며, 정확한 법률 자문은 전문가와 상담하시기
            바랍니다.
          </p>
        </div>
      </CardContent>
    </Card>
  );
};

export default ChatInterface;
