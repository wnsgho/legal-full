import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Copy, Download, Eye, EyeOff } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface MarkdownViewerProps {
  content: string;
  title?: string;
  showRaw?: boolean;
  onToggleRaw?: (showRaw: boolean) => void;
  className?: string;
}

const MarkdownViewer: React.FC<MarkdownViewerProps> = ({
  content,
  title = "문서 뷰어",
  showRaw = false,
  onToggleRaw,
  className = "",
}) => {
  const { toast } = useToast();

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      toast({
        title: "복사 완료",
        description: "문서 내용이 클립보드에 복사되었습니다.",
      });
    } catch (error) {
      toast({
        title: "복사 실패",
        description: "클립보드 복사에 실패했습니다.",
        variant: "destructive",
      });
    }
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${title}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    toast({
      title: "다운로드 완료",
      description: "문서가 다운로드되었습니다.",
    });
  };

  const formatMarkdown = (text: string) => {
    // 기본 마크다운 포맷팅
    return text
      .replace(
        /^# (.*$)/gim,
        '<h1 class="text-2xl font-bold mb-4 text-gray-900">$1</h1>'
      )
      .replace(
        /^## (.*$)/gim,
        '<h2 class="text-xl font-semibold mb-3 text-gray-800">$1</h2>'
      )
      .replace(
        /^### (.*$)/gim,
        '<h3 class="text-lg font-medium mb-2 text-gray-700">$1</h3>'
      )
      .replace(
        /^#### (.*$)/gim,
        '<h4 class="text-base font-medium mb-2 text-gray-700">$1</h4>'
      )
      .replace(/\*\*(.*?)\*\*/gim, '<strong class="font-semibold">$1</strong>')
      .replace(/\*(.*?)\*/gim, '<em class="italic">$1</em>')
      .replace(
        /`(.*?)`/gim,
        '<code class="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono">$1</code>'
      )
      .replace(/^\* (.*$)/gim, '<li class="ml-4">• $1</li>')
      .replace(/^- (.*$)/gim, '<li class="ml-4">- $1</li>')
      .replace(/^\d+\. (.*$)/gim, '<li class="ml-4">$&</li>')
      .replace(/\n\n/gim, '</p><p class="mb-4">')
      .replace(/^(?!<[h|l])/gim, '<p class="mb-4">')
      .replace(/(<li.*<\/li>)/gim, '<ul class="mb-4">$1</ul>')
      .replace(/<\/ul><ul class="mb-4">/gim, "");
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{title}</CardTitle>
          <div className="flex items-center space-x-2">
            {onToggleRaw && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onToggleRaw(!showRaw)}
                className="flex items-center space-x-1"
              >
                {showRaw ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
                <span>{showRaw ? "포맷 보기" : "원문 보기"}</span>
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              className="flex items-center space-x-1"
            >
              <Copy className="h-4 w-4" />
              <span>복사</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              className="flex items-center space-x-1"
            >
              <Download className="h-4 w-4" />
              <span>다운로드</span>
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto text-sm leading-relaxed">
          {showRaw ? (
            <pre className="whitespace-pre-wrap font-mono text-xs">
              {content}
            </pre>
          ) : (
            <div
              className="prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{
                __html: formatMarkdown(content),
              }}
            />
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default MarkdownViewer;

