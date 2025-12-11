import os
import pickle
import networkx as nx
from tqdm import tqdm
from atlas_rag.vectorstore.embedding_model import BaseEmbeddingModel
import faiss
import numpy as np
import torch

def compute_graph_embeddings(node_list, edge_list_string, sentence_encoder: BaseEmbeddingModel, batch_size=40, normalize_embeddings: bool = False):
    # Encode in batches
    node_embeddings = []
    if len(node_list) > 0:
        for i in tqdm(range(0, len(node_list), batch_size), desc="Encoding nodes", disable=True):
            batch = node_list[i:i + batch_size]
            embeddings = sentence_encoder.encode(batch, normalize_embeddings = normalize_embeddings)
            if isinstance(embeddings, list):
                node_embeddings.extend(embeddings)
            elif isinstance(embeddings, np.ndarray):
                node_embeddings.extend(embeddings.tolist())
            elif isinstance(embeddings, torch.Tensor):
                node_embeddings.extend(embeddings.cpu().numpy().tolist())
            else:
                node_embeddings.extend(list(embeddings))
    else:
        print("⚠️ Warning: node_list is empty, returning empty embeddings")

    edge_embeddings = []
    if len(edge_list_string) > 0:
        for i in tqdm(range(0, len(edge_list_string), batch_size), desc="Encoding edges", disable=True):
            batch = edge_list_string[i:i + batch_size]
            embeddings = sentence_encoder.encode(batch, normalize_embeddings = normalize_embeddings)
            if isinstance(embeddings, list):
                edge_embeddings.extend(embeddings)
            elif isinstance(embeddings, np.ndarray):
                edge_embeddings.extend(embeddings.tolist())
            elif isinstance(embeddings, torch.Tensor):
                edge_embeddings.extend(embeddings.cpu().numpy().tolist())
            else:
                edge_embeddings.extend(list(embeddings))
    else:
        print("⚠️ Warning: edge_list_string is empty, returning empty embeddings")

    return node_embeddings, edge_embeddings

def build_faiss_index(embeddings):
    if len(embeddings) == 0:
        raise ValueError("Cannot build FAISS index from empty embeddings list")
    
    dimension = len(embeddings[0])
    
    faiss_index = faiss.IndexHNSWFlat(dimension, 64, faiss.METRIC_INNER_PRODUCT)
    X = np.array(embeddings).astype('float32')

    # normalize the vectors
    faiss.normalize_L2(X)

    # batched add
    for i in tqdm(range(0, X.shape[0], 32), disable=True):
        faiss_index.add(X[i:i+32])
    return faiss_index

def compute_text_embeddings(text_list, sentence_encoder: BaseEmbeddingModel, batch_size = 40, normalize_embeddings: bool = False):
    """Separated text embedding computation"""
    text_embeddings = []
    
    for i in tqdm(range(0, len(text_list), batch_size), desc="Encoding texts", disable=True):
        batch = text_list[i:i + batch_size]
        embeddings = sentence_encoder.encode(batch, normalize_embeddings=normalize_embeddings)
        if isinstance(embeddings, torch.Tensor):
            embeddings = embeddings.cpu().numpy()
        text_embeddings.extend(sentence_encoder.encode(batch, normalize_embeddings = normalize_embeddings))
    return text_embeddings

def create_embeddings_and_index(sentence_encoder, model_name: str, working_directory: str, keyword: str, include_events: bool, include_concept: bool,
                                 normalize_embeddings: bool = True, 
                                 text_batch_size = 40,
                                 node_and_edge_batch_size = 256,
                                 **kwargs):
    # Extract the last part of the encoder_model_name for simplified reference
    encoder_model_name = model_name.split('/')[-1]
    
    print(f"Using encoder model: {encoder_model_name}")
    graph_dir = f"{working_directory}/kg_graphml/{keyword}_graph_with_numeric_id.graphml"
    if not os.path.exists(graph_dir):
        raise FileNotFoundError(f"Graph file {graph_dir} does not exist. Please check the path or generate the graph first.")

    # 환경변수에서 precompute 디렉토리 경로 가져오기
    precompute_dir = os.getenv('PRECOMPUTE_DIRECTORY', 'precompute')
    precompute_path = f"{working_directory}/{precompute_dir}"
    
    node_index_path = f"{precompute_path}/{keyword}_event{include_events}_concept{include_concept}_{encoder_model_name}_node_faiss.index"
    node_list_path = f"{precompute_path}/{keyword}_event{include_events}_concept{include_concept}_node_list.pkl"
    edge_index_path = f"{precompute_path}/{keyword}_event{include_events}_concept{include_concept}_{encoder_model_name}_edge_faiss.index"
    edge_list_path = f"{precompute_path}/{keyword}_event{include_events}_concept{include_concept}_edge_list.pkl"
    node_embeddings_path = f"{precompute_path}/{keyword}_event{include_events}_concept{include_concept}_{encoder_model_name}_node_embeddings.pkl"
    edge_embeddings_path = f"{precompute_path}/{keyword}_event{include_events}_concept{include_concept}_{encoder_model_name}_edge_embeddings.pkl"
    text_embeddings_path = f"{precompute_path}/{keyword}_{encoder_model_name}_text_embeddings.pkl"
    text_index_path = f"{precompute_path}/{keyword}_text_faiss.index"
    original_text_list_path = f"{precompute_path}/{keyword}_text_list.pkl"
    original_text_dict_with_node_id_path = f"{precompute_path}/{keyword}_original_text_dict_with_node_id.pkl"

    if not os.path.exists(precompute_path):
        os.makedirs(precompute_path, exist_ok=True)

    print(f"Loading graph from {graph_dir}")
    with open(graph_dir, "rb") as f:
        KG: nx.DiGraph = nx.read_graphml(f)

    node_list = list(KG.nodes)
    print(f"📊 Total nodes in graph: {len(node_list)}")
    print(f"📊 Total edges in graph: {len(KG.edges)}")
    
    # 노드 타입 확인
    node_types = {}
    for node in node_list:
        node_type = KG.nodes[node].get("type", "unknown")
        node_types[node_type] = node_types.get(node_type, 0) + 1
    print(f"📊 Node types: {node_types}")
    
    text_list = [node for node in tqdm(node_list, disable=True) if KG.nodes[node].get("type") == "passage"]
    print(f"📊 Text nodes (passage): {len(text_list)}")
    
    if not include_events and not include_concept:
        node_list = [node for node in tqdm(node_list, disable=True) if KG.nodes[node].get("type") == "entity"]
    elif include_events and not include_concept:
        node_list = [node for node in tqdm(node_list, disable=True) if KG.nodes[node].get("type") in ["event", "entity"]]
    elif include_events and include_concept:
        node_list = [node for node in tqdm(node_list, disable=True) if KG.nodes[node].get("type") in ["event", "concept", "entity"]]
    else:
        raise ValueError("Invalid combination of include_events and include_concept")
    
    print(f"📊 Filtered node_list length: {len(node_list)}")
    
    if len(node_list) == 0:
        raise ValueError(f"No nodes found with the specified filters (include_events={include_events}, include_concept={include_concept}). Available node types: {list(node_types.keys())}")

    edge_list = list(KG.edges)
    node_set = set(node_list)
    
    # 노드 ID 추출 (안전하게)
    node_list_string = []
    for node in node_list:
        node_id = KG.nodes[node].get("id")
        if node_id is None:
            print(f"⚠️ Warning: Node {node} has no 'id' attribute. Attributes: {list(KG.nodes[node].keys())}")
            continue
        node_list_string.append(str(node_id))
    
    print(f"📊 node_list_string length: {len(node_list_string)}")
    
    if len(node_list_string) == 0:
        raise ValueError("No valid node IDs found. Check if nodes have 'id' attribute in GraphML.")

    # Filter edges based on node list
    # 디버깅: 엣지의 노드 타입 확인
    edge_type_stats = {}
    edges_not_in_set = []
    for i, edge in enumerate(edge_list[:10]):  # 처음 10개만 확인
        source_type = KG.nodes[edge[0]].get("type", "unknown")
        target_type = KG.nodes[edge[1]].get("type", "unknown")
        edge_type_key = f"{source_type}->{target_type}"
        edge_type_stats[edge_type_key] = edge_type_stats.get(edge_type_key, 0) + 1
        
        if edge[0] not in node_set or edge[1] not in node_set:
            edges_not_in_set.append((i, edge, source_type, target_type, edge[0] in node_set, edge[1] in node_set))
    
    print(f"📊 엣지 타입 샘플 (처음 10개): {edge_type_stats}")
    if edges_not_in_set:
        print(f"📊 필터링에서 제외된 엣지 샘플 (처음 5개):")
        for idx, edge, src_type, tgt_type, src_in_set, tgt_in_set in edges_not_in_set[:5]:
            print(f"  - 엣지 {idx}: {src_type}->{tgt_type} (source in set: {src_in_set}, target in set: {tgt_in_set})")
    
    edge_list_index = [i for i, edge in tqdm(enumerate(edge_list), disable=True) if edge[0] in node_set and edge[1] in node_set]
    print(f"📊 Filtered edge indices: {len(edge_list_index)}")
    
    if len(edge_list_index) == 0:
        print("⚠️ Warning: No edges found after filtering. Using empty edge list.")
        print(f"⚠️ 디버깅: node_set 크기: {len(node_set)}, 전체 엣지 수: {len(edge_list)}")
        # 전체 엣지의 노드 타입 통계
        all_edge_types = {}
        for edge in edge_list:
            source_type = KG.nodes[edge[0]].get("type", "unknown")
            target_type = KG.nodes[edge[1]].get("type", "unknown")
            edge_type_key = f"{source_type}->{target_type}"
            all_edge_types[edge_type_key] = all_edge_types.get(edge_type_key, 0) + 1
        print(f"⚠️ 전체 엣지 타입 분포: {all_edge_types}")
        edge_list = []
        edge_list_string = []
    else:
        edge_list = [edge_list[i] for i in edge_list_index]
        # 엣지 문자열 생성 (안전하게)
        edge_list_string = []
        for edge in edge_list:
            try:
                source_id = KG.nodes[edge[0]].get("id", "")
                target_id = KG.nodes[edge[1]].get("id", "")
                relation = KG.edges[edge].get("relation", "")
                edge_str = f"{source_id} {relation} {target_id}"
                edge_list_string.append(edge_str)
            except Exception as e:
                print(f"⚠️ Warning: Failed to create edge string for {edge}: {e}")
                continue
        
        print(f"📊 edge_list_string length: {len(edge_list_string)}")

    original_text_list = []
    original_text_dict_with_node_id = {}
    for text_node in text_list:
        text_id = KG.nodes[text_node].get("id")
        if text_id is None:
            print(f"⚠️ Warning: Text node {text_node} has no 'id' attribute")
            continue
        text = str(text_id).strip()
        original_text_list.append(text)
        original_text_dict_with_node_id[text_node] = text

    print(f"📊 original_text_list length: {len(original_text_list)}")
    
    assert len(original_text_list) == len(original_text_dict_with_node_id)

    with open(original_text_list_path, "wb") as f:
        pickle.dump(original_text_list, f)
    with open(original_text_dict_with_node_id_path, "wb") as f:
        pickle.dump(original_text_dict_with_node_id, f)

    if not os.path.exists(text_index_path) or not os.path.exists(text_embeddings_path):
        print("Computing text embeddings...")
        if len(original_text_list) > 0:
            text_embeddings = compute_text_embeddings(original_text_list, sentence_encoder, text_batch_size, normalize_embeddings)  
            text_faiss_index = build_faiss_index(text_embeddings)  
            faiss.write_index(text_faiss_index, text_index_path)
            with open(text_embeddings_path, "wb") as f:
                pickle.dump(text_embeddings, f)
        else:
            print("⚠️ Warning: original_text_list is empty, skipping text embeddings")
            text_embeddings = []
            text_faiss_index = None
    else:
        print("Text embeddings already computed.")
        if os.path.getsize(text_embeddings_path) > 0:
            with open(text_embeddings_path, "rb") as f:
                text_embeddings = pickle.load(f)
            if os.path.getsize(text_index_path) > 0:
                text_faiss_index = faiss.read_index(text_index_path)
            else:
                text_faiss_index = None
        else:
            print("⚠️ Warning: text_embeddings_path exists but is empty")
            text_embeddings = []
            text_faiss_index = None

    if not os.path.exists(node_embeddings_path) or not os.path.exists(edge_embeddings_path):
        print("Node and edge embeddings not found, computing...")
        node_embeddings, edge_embeddings = compute_graph_embeddings(node_list_string, edge_list_string, sentence_encoder, node_and_edge_batch_size, normalize_embeddings=normalize_embeddings)  # Assumes this function is defined
    else:
        with open(node_embeddings_path, "rb") as f:
            node_embeddings = pickle.load(f)
        with open(edge_embeddings_path, "rb") as f:
            edge_embeddings = pickle.load(f)
        print("Graph embeddings already computed")
    
    # 노드 인덱스 생성 (빈 리스트 처리)
    if not os.path.exists(node_index_path):
        if len(node_embeddings) > 0:
            node_faiss_index = build_faiss_index(node_embeddings)
            faiss.write_index(node_faiss_index, node_index_path)
        else:
            print("⚠️ Warning: node_embeddings is empty, skipping FAISS index creation")
            node_faiss_index = None
    else:
        if os.path.getsize(node_index_path) > 0:
            node_faiss_index = faiss.read_index(node_index_path)
        else:
            print("⚠️ Warning: node_index_path exists but is empty")
            node_faiss_index = None
    
    # 엣지 인덱스 생성 (빈 리스트 처리)
    if not os.path.exists(edge_index_path):
        if len(edge_embeddings) > 0:
            edge_faiss_index = build_faiss_index(edge_embeddings)
            faiss.write_index(edge_faiss_index, edge_index_path)
        else:
            print("⚠️ Warning: edge_embeddings is empty, skipping FAISS index creation")
            edge_faiss_index = None
    else:
        if os.path.getsize(edge_index_path) > 0:
            edge_faiss_index = faiss.read_index(edge_index_path)
        else:
            print("⚠️ Warning: edge_index_path exists but is empty")
            edge_faiss_index = None

    if not os.path.exists(node_embeddings_path):
        with open(node_embeddings_path, "wb") as f:
            pickle.dump(node_embeddings, f)

    if not os.path.exists(edge_embeddings_path):
        with open(edge_embeddings_path, "wb") as f:
            pickle.dump(edge_embeddings, f)

    with open(node_list_path, "wb") as f:
        pickle.dump(node_list, f)

    with open(edge_list_path, "wb") as f:
        pickle.dump(edge_list, f)

    print("Node and edge embeddings already computed.")
    
    # 빈 인덱스에 대한 경고
    if node_faiss_index is None:
        print("⚠️ Warning: node_faiss_index is None (no nodes to index)")
    if edge_faiss_index is None:
        print("⚠️ Warning: edge_faiss_index is None (no edges to index)")
    
    # Return all required indices, embeddings, and lists
    return {
        "KG": KG,
        "node_faiss_index": node_faiss_index,
        "edge_faiss_index": edge_faiss_index,
        "text_faiss_index": text_faiss_index,
        "node_embeddings": node_embeddings,
        "edge_embeddings": edge_embeddings,
        "text_embeddings": text_embeddings,
        "node_list": node_list,
        "edge_list": edge_list,
        "text_dict": original_text_dict_with_node_id,
    }

