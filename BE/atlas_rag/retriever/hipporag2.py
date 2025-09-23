import networkx as nx
import json
from tqdm import tqdm
import json
from tqdm import tqdm
from typing import Dict, List, Tuple
import networkx as nx
import numpy as np
import json_repair
from atlas_rag.vectorstore.embedding_model import BaseEmbeddingModel
from atlas_rag.llm_generator.llm_generator import LLMGenerator
from logging import Logger
from dataclasses import dataclass
from typing import Optional
from atlas_rag.retriever.base import BasePassageRetriever
from atlas_rag.retriever.inference_config import InferenceConfig

def min_max_normalize(x):
    min_val = np.min(x)
    max_val = np.max(x)
    range_val = max_val - min_val
    
    # Handle the case where all values are the same (range is zero)
    if range_val == 0:
        return np.ones_like(x)  # Return an array of ones with the same shape as x
    
    return (x - min_val) / range_val


class HippoRAG2Retriever(BasePassageRetriever):
    def __init__(self, llm_generator:LLMGenerator, 
                 sentence_encoder:BaseEmbeddingModel, 
                 data : dict, 
                 inference_config: Optional[InferenceConfig] = None,
                 logger = None,
                 **kwargs):
        self.llm_generator = llm_generator
        self.sentence_encoder = sentence_encoder

        self.node_embeddings = data["node_embeddings"]
        self.node_list = data["node_list"]
        self.edge_list = data["edge_list"]
        self.edge_embeddings = data["edge_embeddings"]
        self.text_embeddings = data["text_embeddings"]
        self.edge_faiss_index = data["edge_faiss_index"]
        self.passage_dict = data["text_dict"]
        self.text_id_list = list(self.passage_dict.keys())
        self.KG = data["KG"]
        self.KG = self.KG.subgraph(self.node_list + self.text_id_list)
        
        
        self.logger = logger
        if self.logger is None:
            self.logging = False
        else:
            self.logging = True
        
        # 하이브리드 모드: query2edge + query2node 조합
        self.hybrid_mode = True
        self.edge_weight = 0.6  # query2edge 가중치
        self.node_weight = 0.4  # query2node 가중치

        self.inference_config = inference_config if inference_config is not None else InferenceConfig()
        node_id_to_file_id = {}
        for node_id in tqdm(list(self.KG.nodes), disable=True):
            if self.inference_config.keyword == "musique" and self.KG.nodes[node_id]['type']=="passage":
                node_id_to_file_id[node_id] = self.KG.nodes[node_id]["id"]
            else:
                node_id_to_file_id[node_id] = self.KG.nodes[node_id]["file_id"]
        self.node_id_to_file_id = node_id_to_file_id

    def ner(self, text):
        return self.llm_generator.ner(text)
    
    def ner2node(self, query, topN = 10):
        entities = self.ner(query)
        entities = entities.split(", ")

        if len(entities) == 0:
            entities = [query]
        # retrieve the top k nodes
        topk_nodes = []
        node_score_dict = {}
        for entity_index, entity in enumerate(entities):
            topk_for_this_entity = 1
            entity_embedding = self.sentence_encoder.encode([entity], query_type="search")
            scores = min_max_normalize(self.node_embeddings@entity_embedding[0].T)
            index_matrix = np.argsort(scores)[-topk_for_this_entity:][::-1]
            similarity_matrix = [scores[i] for i in index_matrix]
            for index, sim_score in zip(index_matrix, similarity_matrix):
                node = self.node_list[index]
                if node not in topk_nodes:
                    topk_nodes.append(node)
                    node_score_dict[node] = sim_score
                    
        topk_nodes = list(set(topk_nodes))
        result_node_score_dict = {}
        if len(topk_nodes) > 2*topN:
            topk_nodes = topk_nodes[:2*topN]
            for node in topk_nodes:
                if node in node_score_dict:
                    result_node_score_dict[node] = node_score_dict[node]
        return result_node_score_dict
    
    def query2node(self, query, topN = 10):
        query_emb = self.sentence_encoder.encode([query], query_type="entity")
        scores = min_max_normalize(self.node_embeddings@query_emb[0].T)
        index_matrix = np.argsort(scores)[-topN:][::-1]
        similarity_matrix = [scores[i] for i in index_matrix]
        result_node_score_dict = {}
        for index, sim_score in zip(index_matrix, similarity_matrix):
            node = self.node_list[index]
            result_node_score_dict[node] = sim_score

        return result_node_score_dict
    
    def query2edge(self, query, topN = 10):
        query_emb = self.sentence_encoder.encode([query], query_type="edge")
        scores = min_max_normalize(self.edge_embeddings@query_emb[0].T)
        index_matrix = np.argsort(scores)[-topN:][::-1]
        log_edge_list = []
        for index in index_matrix:
            edge = self.edge_list[index]
            edge_str = [self.KG.nodes[edge[0]]['id'], self.KG.edges[edge]['relation'], self.KG.nodes[edge[1]]['id']]
            log_edge_list.append(edge_str)

        similarity_matrix = [scores[i] for i in index_matrix]
        # construct the edge list
        before_filter_edge_json = {}
        before_filter_edge_json['fact'] = []
        for index, sim_score in zip(index_matrix, similarity_matrix):
            edge = self.edge_list[index]
            edge_str = [self.KG.nodes[edge[0]]['id'], self.KG.edges[edge]['relation'], self.KG.nodes[edge[1]]['id']]
            before_filter_edge_json['fact'].append(edge_str)
        if self.logging:
            self.logger.info(f"HippoRAG2 Before Filter Edge: {before_filter_edge_json['fact']}")
        filtered_facts = self.llm_generator.filter_triples_with_entity_event(query, json.dumps(before_filter_edge_json, ensure_ascii=False))
        parsed_result = json_repair.loads(filtered_facts)
        if isinstance(parsed_result, dict) and 'fact' in parsed_result:
            filtered_facts = parsed_result['fact']
        elif isinstance(parsed_result, list):
            filtered_facts = parsed_result
        else:
            print(f"⚠️ 예상치 못한 JSON 구조: {type(parsed_result)}")
            filtered_facts = []
        if len(filtered_facts) == 0:
            return {}
        # use filtered facts to get the edge id and check if it exists in the original candidate list.
        node_score_dict = {}
        log_edge_list = []
        for edge in filtered_facts:
            edge_str = f'{edge[0]} {edge[1]} {edge[2]}'
            search_emb = self.sentence_encoder.encode([edge_str], query_type="search")
            D, I = self.edge_faiss_index.search(search_emb, 1)
            filtered_index = I[0][0]
            # get the edge and the original score
            edge = self.edge_list[filtered_index]
            log_edge_list.append([self.KG.nodes[edge[0]]['id'], self.KG.edges[edge]['relation'], self.KG.nodes[edge[1]]['id']])
            head, tail = edge[0], edge[1]
            sim_score = scores[filtered_index]
            
            if head not in node_score_dict:
                node_score_dict[head] = [sim_score]
            else:
                node_score_dict[head].append(sim_score)
            if tail not in node_score_dict:
                node_score_dict[tail] = [sim_score]
            else:
                node_score_dict[tail].append(sim_score)
        # average the scores
        if self.logging:
            self.logger.info(f"HippoRAG2: Filtered edges: {log_edge_list}")
        
        # take average of the scores
        for node in node_score_dict:
            node_score_dict[node] = sum(node_score_dict[node]) / len(node_score_dict[node])
        
        return node_score_dict
    
    def query2passage(self, query, weight_adjust = 0.3):
        query_emb = self.sentence_encoder.encode([query], query_type="passage")
        sim_scores = self.text_embeddings @ query_emb[0].T
        sim_scores = min_max_normalize(sim_scores)*weight_adjust # converted to probability
        # create dict of passage id and score
        return dict(zip(self.text_id_list, sim_scores))
    
    def hybrid_retrieve_nodes(self, query, topN=30):
        """하이브리드 모드: query2edge + query2node 결과 병합"""
        # 1. query2edge로 관계 검색
        edge_node_dict = self.query2edge(query, topN=topN)
        
        # 2. query2node로 내용 검색
        content_node_dict = self.query2node(query, topN=topN)
        
        # 3. 두 결과를 가중치로 병합
        combined_node_dict = {}
        
        # edge 결과 추가 (가중치 적용)
        for node, score in edge_node_dict.items():
            combined_node_dict[node] = score * self.edge_weight
        
        # content 결과 추가/병합 (가중치 적용)
        for node, score in content_node_dict.items():
            if node in combined_node_dict:
                combined_node_dict[node] += score * self.node_weight
            else:
                combined_node_dict[node] = score * self.node_weight
        
        if self.logging:
            self.logger.info(f"하이브리드 검색 - Edge: {len(edge_node_dict)}개, Content: {len(content_node_dict)}개, 병합: {len(combined_node_dict)}개")
        
        return combined_node_dict

    def retrieve_personalization_dict(self, query, topN=30, weight_adjust=0.3):
        if self.hybrid_mode:
            node_dict = self.hybrid_retrieve_nodes(query, topN=topN)
        else:
            # 기존 단일 모드 (호환성 유지)
            if hasattr(self, 'retrieve_node_fn'):
                node_dict = self.retrieve_node_fn(query, topN=topN)
            else:
                node_dict = self.query2edge(query, topN=topN)
        
        text_dict = self.query2passage(query, weight_adjust=weight_adjust)
  
        return node_dict, text_dict

    def retrieve(self, query, topN=5, **kwargs):
        topN_edges = self.inference_config.topk_edges
        weight_adjust = self.inference_config.weight_adjust
        
        node_dict, text_dict = self.retrieve_personalization_dict(query, topN=topN_edges, weight_adjust=weight_adjust)
          
        personalization_dict = {}
        if len(node_dict) == 0:
            # return topN text passages
            sorted_passages = sorted(text_dict.items(), key=lambda x: x[1], reverse=True)
            sorted_passages = sorted_passages[:topN]
            sorted_passages_contents = []
            sorted_scores = []
            sorted_passage_ids = []
            for passage_id, score in sorted_passages:
                sorted_passages_contents.append(self.passage_dict[passage_id])
                sorted_scores.append(float(score))
                sorted_passage_ids.append(self.node_id_to_file_id[passage_id])
            return sorted_passages_contents, sorted_passage_ids
            
        personalization_dict.update(node_dict)
        personalization_dict.update(text_dict)
        # retrieve the top N passages
        pr = nx.pagerank(self.KG, personalization=personalization_dict, 
                         alpha = self.inference_config.ppr_alpha, 
                         max_iter=self.inference_config.ppr_max_iter, 
                         tol=self.inference_config.ppr_tol)

        # get the top N passages based on the text_id list and pagerank score
        text_dict_score = {}
        for node in self.text_id_list:
            # filter out nodes that have 0 score
            if pr[node] > 0.0:
                text_dict_score[node] = pr[node]
            
        # return topN passages
        sorted_passages_ids = sorted(text_dict_score.items(), key=lambda x: x[1], reverse=True)
        sorted_passages_ids = sorted_passages_ids[:topN]
        
        sorted_passages_contents = []
        sorted_scores = []
        sorted_passage_ids = []
        for passage_id, score in sorted_passages_ids:
            sorted_passages_contents.append(self.passage_dict[passage_id])
            sorted_scores.append(score)
            sorted_passage_ids.append(self.node_id_to_file_id[passage_id])
        return sorted_passages_contents, sorted_passage_ids