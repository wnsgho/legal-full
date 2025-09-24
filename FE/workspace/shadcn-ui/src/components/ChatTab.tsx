import React from 'react';
import ChatInterface from "@/components/ChatInterface";
import { ChatMessage } from "@/types";

interface ChatTabProps {
  selectedContract: string;
  chatMessages: ChatMessage[];
  handleSendMessage: (message: string) => void;
  handleClearChatHistory: () => void;
}

const ChatTab: React.FC<ChatTabProps> = ({
  selectedContract,
  chatMessages,
  handleSendMessage,
  handleClearChatHistory,
}) => {
  return (
    <ChatInterface
      contractId={selectedContract}
      messages={chatMessages}
      onSendMessage={handleSendMessage}
      onClearHistory={handleClearChatHistory}
    />
  );
};

export default ChatTab;
