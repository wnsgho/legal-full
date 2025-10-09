import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
  useRef,
} from "react";
import Graph from "graphology";
import { circular } from "graphology-layout";
import forceAtlas2 from "graphology-layout-forceatlas2";
import FA2Layout from "graphology-layout-forceatlas2/worker";
import Sigma from "sigma";
import { PlainObject } from "sigma/types";
import { animateNodes } from "sigma/utils";
import { api } from "../services/api";

// 노드 타입별 색상 정의
const NODE_COLORS = {
  default: "#007f99", // 일반 노드 색상
  text: "#093446", // Text 라벨 노드 색상
};

const EDGE_COLORS: Record<string, string> = {
  Relation: "#666666", // 옅은 검은색
  Source: "#666666", // 옅은 검은색
  CONTAINS: "#666666",
  RELATED_TO: "#666666",
  HAS_PROPERTY: "#666666",
  IS_A: "#666666",
};

interface ApiNode {
  id: number;
  labels: string[];
  properties: Record<string, unknown>;
}

interface ApiRelationship {
  id: number;
  type: string;
  start_node: number;
  end_node: number;
  properties: Record<string, unknown>;
}

interface GraphFetchResult {
  success: boolean;
  nodes: ApiNode[];
  relationships: ApiRelationship[];
  database: string;
}

interface SigmaKnowledgeGraphProps {
  width?: string;
  height?: string;
  className?: string;
  serverUrl?: string;
  serverUser?: string;
  serverPassword?: string;
  serverDatabase?: string;
  limit?: number;
  autoLoad?: boolean;
  onNodeClick?: (node: any) => void;
  onEdgeClick?: (edge: any) => void;
}

interface NodeInfo {
  id: string;
  labels: string[];
  properties: Record<string, unknown>;
  raw?: unknown;
}

const SigmaKnowledgeGraph: React.FC<SigmaKnowledgeGraphProps> = ({
  width = "100%",
  height = "600px",
  className = "",
  serverUrl,
  serverUser,
  serverPassword,
  serverDatabase,
  limit = 1000,
  autoLoad = true,
  onNodeClick,
  onEdgeClick,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const fa2LayoutRef = useRef<FA2Layout | null>(null);
  const graphRef = useRef<Graph | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<GraphFetchResult | null>(null);
  const [selectedNode, setSelectedNode] = useState<NodeInfo | null>(null);
  const [showNodeInfo, setShowNodeInfo] = useState(false);
  const [isLayoutRunning, setIsLayoutRunning] = useState(false);
  const [cancelCurrentAnimation, setCancelCurrentAnimation] = useState<
    (() => void) | null
  >(null);

  // Neo4j에서 그래프 데이터를 가져오는 함수
  const fetchGraphData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // 1) 런타임 설정을 /config에서 우선 시도
      let runtimeConfig: any = null;
      try {
        const res = await fetch("/config", { cache: "no-store" });
        if (res.ok) {
          runtimeConfig = await res.json();
        }
      } catch (_) {
        // 무시하고 env/props로 폴백
      }

      // 2) props → env → runtime 순으로 병합 (props가 최우선)
      const envVars = (import.meta.env || {}) as unknown as {
        VITE_NEO4J_URI?: string;
        VITE_NEO4J_USER?: string;
        VITE_NEO4J_PASSWORD?: string;
        VITE_NEO4J_DATABASE?: string;
      };

      const mergedServerUrl =
        serverUrl ||
        runtimeConfig?.serverUrl ||
        envVars.VITE_NEO4J_URI ||
        "neo4j://127.0.0.1:7687";
      const mergedUser =
        serverUser ||
        runtimeConfig?.serverUser ||
        envVars.VITE_NEO4J_USER ||
        "neo4j";
      const mergedPassword =
        serverPassword ||
        runtimeConfig?.serverPassword ||
        envVars.VITE_NEO4J_PASSWORD ||
        "";
      const mergedDatabase =
        serverDatabase ||
        runtimeConfig?.serverDatabase ||
        envVars.VITE_NEO4J_DATABASE ||
        "contract3";

      if (!mergedPassword) {
        throw new Error(
          "Neo4j 비밀번호가 설정되지 않았습니다. 환경변수를 확인해주세요."
        );
      }

      const data = await api.getSigmaGraphData({
        serverUrl: mergedServerUrl,
        username: mergedUser,
        password: mergedPassword,
        database: mergedDatabase,
        limit,
      });

      if (data.success) {
        setGraphData(data);
        console.log("그래프 데이터 로드 성공:", data);
      } else {
        throw new Error("그래프 데이터 로드 실패");
      }
    } catch (err) {
      const errorMsg = `그래프 데이터 로드 중 오류: ${err}`;
      console.error(errorMsg);
      setError(errorMsg);
    } finally {
      setIsLoading(false);
    }
  }, [serverUrl, serverUser, serverPassword, serverDatabase, limit]);

  // 시그마 그래프를 초기화하고 렌더링하는 함수
  const initializeSigma = useCallback(() => {
    if (!containerRef.current || !graphData) return;

    // 컨테이너 크기 확인
    const container = containerRef.current;
    const rect = container.getBoundingClientRect();
    console.log("컨테이너 크기:", rect.width, rect.height);

    if (rect.width === 0 || rect.height === 0) {
      console.warn("컨테이너 크기가 0입니다. 잠시 후 다시 시도합니다.");
      setTimeout(() => initializeSigma(), 100);
      return;
    }

    // 기존 시그마 인스턴스 정리
    if (sigmaRef.current) {
      sigmaRef.current.kill();
      sigmaRef.current = null;
    }

    // 그래프 생성 (multi-graph로 설정하여 중복 엣지 허용)
    const graph = new Graph({ multi: true });
    graphRef.current = graph;

    // 노드 추가 (DATABASE_SCHEMA.md에 맞게)
    console.log("전체 노드 데이터:", graphData.nodes.slice(0, 5)); // 처음 5개 노드만 로그
    graphData.nodes.forEach((node) => {
      const nodeId = `node_${node.id}`;

      // 노드 라벨에 따라 다른 속성 사용
      const nodeLabel = node.labels && node.labels[0];

      let label = `Node ${node.id}`; // 기본값

      if (nodeLabel === "Node" && node.properties.name) {
        // "Node" 라벨이고 name 속성이 있으면 name 사용
        label = node.properties.name;
      } else if (nodeLabel === "Text" && node.properties.text) {
        // "Text" 라벨이고 text 속성이 있으면 text 사용
        label = node.properties.text;
      } else if (node.properties.numeric_id) {
        // 그 외의 경우 numeric_id 사용
        label = `ID: ${node.properties.numeric_id}`;
      }

      const nodeType = node.properties.type || node.labels[0] || "Unknown";
      const numericId = node.properties.numeric_id || node.id;

      // 디버깅: 라벨 정보 출력 (처음 5개만)
      if (node.id <= 5) {
        console.log("노드 라벨 정보:", {
          id: nodeId,
          nodeLabel: nodeLabel,
          properties: JSON.stringify(node.properties, null, 2),
          labels: node.labels,
          finalLabel: label,
          hasName: !!node.properties.name,
          hasText: !!node.properties.text,
        });
      }

      // 노드 타입에 따른 색상 결정 (Text 노드 식별)
      const isTextNode =
        nodeType.toLowerCase().includes("text") ||
        node.labels.some((label) => label.toLowerCase().includes("text")) ||
        String(label).toLowerCase().includes("text") ||
        (node.properties.text && node.properties.text.length > 0) ||
        (node.properties.content && node.properties.content.length > 0);

      // 디버깅: Text 노드 확인
      if (isTextNode) {
        console.log("Text 노드 발견:", {
          id: nodeId,
          nodeType,
          labels: node.labels,
          label: String(label),
        });
      }

      const nodeColor = isTextNode ? NODE_COLORS.text : NODE_COLORS.default;

      // numeric_id를 기반으로 크기 결정 (더 작은 크기로 겹침 방지)
      const nodeSize = Math.max(6, Math.min(15, 6 + (numericId % 9)));

      graph.addNode(nodeId, {
        label: String(label),
        x: Math.random() * 200 - 100, // 예제처럼 적당한 초기 배치 범위 (-100 to 100)
        y: Math.random() * 200 - 100, // 예제처럼 적당한 초기 배치 범위 (-100 to 100)
        size: nodeSize,
        color: nodeColor,
        // type 속성 제거 (Sigma가 인식하지 못하는 타입으로 인한 오류 방지)
        properties: node.properties,
        originalId: node.id,
        labels: node.labels,
        numeric_id: numericId,
        nodeType: nodeType, // type 대신 nodeType으로 저장
      });
    });

    // 엣지 추가 (DATABASE_SCHEMA.md에 맞게, multi-graph 지원)
    graphData.relationships.forEach((rel) => {
      const sourceId = `node_${rel.start_node}`;
      const targetId = `node_${rel.end_node}`;

      if (graph.hasNode(sourceId) && graph.hasNode(targetId)) {
        const edgeType = rel.type || "Relation";
        // 관계 타입과 ID를 포함한 고유한 엣지 ID 생성
        const edgeId = `edge_${rel.id}_${edgeType}`;
        const edgeColor = EDGE_COLORS[edgeType] || "#999999";

        // numeric_id를 기반으로 두께 결정 (스키마에 따라)
        const numericId = rel.properties.numeric_id || rel.id;
        const edgeSize = Math.max(1, Math.min(5, 1 + (numericId % 4)));

        // relation 속성을 라벨로 사용
        const relationLabel = rel.properties.relation || edgeType;

        try {
          graph.addEdge(sourceId, targetId, {
            id: edgeId,
            label: relationLabel,
            size: edgeSize,
            color: edgeColor,
            // type 속성 제거 (Sigma가 인식하지 못하는 타입으로 인한 오류 방지)
            properties: rel.properties,
            originalId: rel.id,
            numeric_id: numericId,
            edgeType: edgeType, // type 대신 edgeType으로 저장
          });
        } catch (error) {
          // 이미 존재하는 엣지인 경우 무시
          console.warn(`엣지 추가 실패 (이미 존재): ${edgeId}`, error);
        }
      }
    });

    // 시그마 인스턴스 생성 (컨테이너 크기 문제 해결)
    const sigma = new Sigma(graph, containerRef.current, {
      renderLabels: true,
      defaultNodeColor: "#666",
      defaultEdgeColor: "#666666",
      labelSize: 10,
      labelWeight: "normal",
      // 노드와 엣지 렌더링 최적화
      nodeHoverColor: "#ff0000",
      edgeHoverColor: "#ff0000",
      // 줌 및 팬 설정
      enableEdgeEvents: true,
      enableNodeEvents: true,
      // 컨테이너 크기 문제 해결
      allowInvalidContainer: true,
    });

    sigmaRef.current = sigma;

    // ForceAtlas2 레이아웃 설정 (sigmaexample.tsx 기본 설정 기반)
    const sensibleSettings = forceAtlas2.inferSettings(graph);
    // 예제처럼 기본 설정을 사용하되 약간 조정
    const fa2Settings = {
      ...sensibleSettings,
      // 기본 설정 유지하되 약간 조정
      gravity: sensibleSettings.gravity * 0.5, // 중력을 절반으로 줄임
      scalingRatio: sensibleSettings.scalingRatio * 2, // 스케일링을 2배로 증가
      // repulsionStrength는 기본값 사용 (너무 높게 설정하면 퍼짐)
      // attractionStrength는 기본값 사용 (너무 낮게 설정하면 연결이 끊김)
    };

    const fa2Layout = new FA2Layout(graph, {
      settings: fa2Settings,
    });
    fa2LayoutRef.current = fa2Layout;

    // 노드 클릭 이벤트
    sigma.on("clickNode", (event) => {
      const nodeId = event.node;
      const nodeData = graph.getNodeAttributes(nodeId);

      const nodeInfo: NodeInfo = {
        id: nodeId,
        labels: nodeData.labels || [],
        properties: {
          ...nodeData.properties,
          nodeType: nodeData.nodeType, // nodeType 정보 추가
        },
        raw: nodeData,
      };

      setSelectedNode(nodeInfo);
      setShowNodeInfo(true);
      onNodeClick?.(nodeData);
    });

    // 엣지 클릭 이벤트
    sigma.on("clickEdge", (event) => {
      const edgeId = event.edge;
      const edgeData = graph.getEdgeAttributes(edgeId);

      const edgeInfo: NodeInfo = {
        id: edgeId,
        labels: [edgeData.edgeType || "Edge"],
        properties: {
          ...edgeData.properties,
          edgeType: edgeData.edgeType, // edgeType 정보 추가
        },
        raw: edgeData,
      };

      setSelectedNode(edgeInfo);
      setShowNodeInfo(true);
      onEdgeClick?.(edgeData);
    });

    // 초기 레이아웃 적용 (예제처럼 적당한 크기로)
    const circularPositions = circular(graph, { scale: 100 }); // 예제와 같은 스케일 사용
    animateNodes(graph, circularPositions, { duration: 1000 }); // 애니메이션 시간 단축

    // ForceAtlas2 대신 원형 레이아웃을 기본으로 사용
    // FA2는 사용자가 명시적으로 요청할 때만 실행
  }, [graphData, onNodeClick, onEdgeClick]);

  // ForceAtlas2 레이아웃 시작/중지
  const toggleFA2Layout = useCallback(() => {
    if (!fa2LayoutRef.current) return;

    if (isLayoutRunning) {
      fa2LayoutRef.current.stop();
      setIsLayoutRunning(false);
    } else {
      fa2LayoutRef.current.start();
      setIsLayoutRunning(true);
    }
  }, [isLayoutRunning]);

  // 랜덤 레이아웃
  const randomLayout = useCallback(() => {
    if (!graphRef.current || !fa2LayoutRef.current) return;

    // FA2 중지
    if (fa2LayoutRef.current.isRunning()) {
      fa2LayoutRef.current.stop();
      setIsLayoutRunning(false);
    }

    if (cancelCurrentAnimation) {
      cancelCurrentAnimation();
    }

    // 현재 위치 범위 계산
    const xExtents = { min: 0, max: 0 };
    const yExtents = { min: 0, max: 0 };
    graphRef.current.forEachNode((_node, attributes) => {
      xExtents.min = Math.min(attributes.x, xExtents.min);
      xExtents.max = Math.max(attributes.x, xExtents.max);
      yExtents.min = Math.min(attributes.y, yExtents.min);
      yExtents.max = Math.max(attributes.y, yExtents.max);
    });

    const randomPositions: PlainObject<PlainObject<number>> = {};
    graphRef.current.forEachNode((node) => {
      // 적당한 범위로 랜덤 배치 (예제 방식과 유사하게)
      const range = Math.max(
        200, // 적당한 기본 범위
        Math.max(xExtents.max - xExtents.min, yExtents.max - yExtents.min) * 1.5 // 기존 범위의 1.5배
      );
      randomPositions[node] = {
        x: (Math.random() - 0.5) * range,
        y: (Math.random() - 0.5) * range,
      };
    });

    const cancelAnimation = animateNodes(graphRef.current, randomPositions, {
      duration: 800, // 애니메이션 시간을 더 단축
    });
    setCancelCurrentAnimation(() => cancelAnimation);
  }, [cancelCurrentAnimation]);

  // 원형 레이아웃
  const circularLayout = useCallback(() => {
    if (!graphRef.current || !fa2LayoutRef.current) return;

    // FA2 중지
    if (fa2LayoutRef.current.isRunning()) {
      fa2LayoutRef.current.stop();
      setIsLayoutRunning(false);
    }

    if (cancelCurrentAnimation) {
      cancelCurrentAnimation();
    }

    const circularPositions = circular(graphRef.current, { scale: 2000 });
    const cancelAnimation = animateNodes(graphRef.current, circularPositions, {
      duration: 800, // 애니메이션 시간을 단축
      easing: "linear",
    });
    setCancelCurrentAnimation(() => cancelAnimation);
  }, [cancelCurrentAnimation]);

  // 컴포넌트 마운트 시 데이터 로드
  useEffect(() => {
    if (autoLoad) {
      fetchGraphData();
    }
  }, [autoLoad, fetchGraphData]);

  // 그래프 데이터가 로드되면 시그마 초기화
  useEffect(() => {
    if (graphData) {
      initializeSigma();
    }
  }, [graphData, initializeSigma]);

  // 컴포넌트 언마운트 시 정리
  useEffect(() => {
    return () => {
      if (sigmaRef.current) {
        sigmaRef.current.kill();
      }
      if (fa2LayoutRef.current) {
        fa2LayoutRef.current.stop();
      }
    };
  }, []);

  return (
    <div
      className={`sigma-knowledge-graph ${className}`}
      style={{ width, height }}
    >
      {/* 컨트롤 패널 */}
      <div className="p-2 border-b bg-white/70 backdrop-blur sticky top-0 z-10">
        <div className="flex gap-2 items-center flex-wrap">
          <button
            onClick={fetchGraphData}
            disabled={isLoading}
            className="px-3 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? "로딩 중..." : "데이터 새로고침"}
          </button>

          <button
            onClick={toggleFA2Layout}
            className={`px-3 py-2 text-sm rounded ${
              isLayoutRunning
                ? "bg-red-600 text-white hover:bg-red-700"
                : "bg-green-600 text-white hover:bg-green-700"
            }`}
          >
            {isLayoutRunning ? "FA2 중지" : "FA2 시작"}
          </button>

          <button
            onClick={randomLayout}
            className="px-3 py-2 bg-gray-200 text-gray-800 text-sm rounded hover:bg-gray-300"
          >
            랜덤 레이아웃
          </button>

          <button
            onClick={circularLayout}
            className="px-3 py-2 bg-purple-200 text-purple-800 text-sm rounded hover:bg-purple-300"
          >
            원형 레이아웃
          </button>

          {graphData && (
            <div className="text-xs text-gray-600 ml-auto">
              노드: {graphData.nodes.length} | 관계:{" "}
              {graphData.relationships.length}
            </div>
          )}
        </div>
      </div>

      {/* 로딩 상태 */}
      {isLoading && (
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
            <p className="text-gray-600">그래프를 로딩 중입니다...</p>
          </div>
        </div>
      )}

      {/* 에러 상태 */}
      {error && (
        <div className="flex items-center justify-center h-full">
          <div className="text-center text-red-600">
            <p className="mb-2">⚠️ 오류가 발생했습니다</p>
            <p className="text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* 그래프 컨테이너 */}
      <div
        ref={containerRef}
        style={{
          width: "100%",
          height: "calc(100% - 60px)",
          minHeight: "400px", // 최소 높이 보장
          border: "1px solid lightgray",
          display: error || isLoading ? "none" : "block",
          position: "relative", // 위치 명시
        }}
      />

      {/* 노드/엣지 정보 모달 */}
      {showNodeInfo && selectedNode && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">
                {selectedNode.labels.includes("Edge") ||
                selectedNode.labels.includes("RELATED_TO")
                  ? "엣지 정보"
                  : "노드 정보"}
              </h3>
              <button
                onClick={() => setShowNodeInfo(false)}
                className="text-gray-500 hover:text-gray-700 text-xl"
              >
                ×
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <h4 className="font-medium text-gray-700 mb-2">기본 정보</h4>
                <div className="bg-gray-50 p-3 rounded">
                  <p>
                    <strong>ID:</strong> {selectedNode.id}
                  </p>
                  <p>
                    <strong>라벨:</strong>{" "}
                    {selectedNode.labels.join(", ") || "없음"}
                  </p>
                </div>
              </div>

              <div>
                <h4 className="font-medium text-gray-700 mb-2">속성</h4>
                <div className="bg-gray-50 p-3 rounded max-h-60 overflow-y-auto">
                  {Object.keys(selectedNode.properties).length > 0 ? (
                    <div className="space-y-2">
                      {Object.entries(selectedNode.properties).map(
                        ([key, value]) => (
                          <div key={key} className="flex">
                            <span className="font-medium text-blue-600 w-32 flex-shrink-0">
                              {key}:
                            </span>
                            <span className="text-gray-800 break-all">
                              {typeof value === "object"
                                ? JSON.stringify(value, null, 2)
                                : String(value)}
                            </span>
                          </div>
                        )
                      )}
                    </div>
                  ) : (
                    <p className="text-gray-500">속성이 없습니다</p>
                  )}
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setShowNodeInfo(false)}
                  className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
                >
                  닫기
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SigmaKnowledgeGraph;
