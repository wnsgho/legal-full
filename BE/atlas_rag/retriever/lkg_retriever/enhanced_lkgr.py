from difflib import get_close_matches
from logging import Logger
import faiss
from neo4j import GraphDatabase
import time
import nltk
from nltk.corpus import stopwords
import re
nltk.download('stopwords')
from graphdatascience import GraphDataScience
from atlas_rag.llm_generator.llm_generator import LLMGenerator
from atlas_rag.vectorstore.embedding_model import BaseEmbeddingModel
import string
from atlas_rag.retriever.lkg_retriever.base import BaseLargeKGRetriever
from atlas_rag.retriever.lkg_retriever.lkgr import LargeKGRetriever


class EnhancedLargeKGRetriever(LargeKGRetriever):
    """
    조항 검색 기능과 연결된 노드 검색 기능이 추가된 향상된 LKG 리트라이버
    """
    
    def __init__(self, keyword: str, neo4j_driver: GraphDatabase, 
                llm_generator: LLMGenerator, sentence_encoder: BaseEmbeddingModel, 
                node_index: faiss.Index, passage_index: faiss.Index, 
                topN: int = 5,
                number_of_source_nodes_per_ner: int = 10,
                sampling_area: int = 250, logger: Logger = None, **kwargs):
        
        # 부모 클래스 초기화
        super().__init__(keyword, neo4j_driver, llm_generator, sentence_encoder, 
                        node_index, passage_index, topN, number_of_source_nodes_per_ner, 
                        sampling_area, logger, **kwargs)
        
        # 데이터베이스 이름 설정
        self.database_name = kwargs.get('database', 'neo4j')
        
        # 조항 검색 관련 설정
        self.clause_patterns = [
            r'제\d+조',
            r'\d+조',
            r'조항\s*\d+',
            r'제\d+조\s*\d+항',
            r'\d+조\s*\d+항',
            r'비밀유지',
            r'계약해지',
            r'손해배상',
            r'지적재산권',
            r'유지보수',
            r'대가',
            r'책임',
            r'효력',
            r'분쟁',
            r'거래종결',
            r'배당',
            r'차입',
            r'매도인',
            r'매수인',
            r'계약',
            r'가격',
            r'조정',
            r'운전자본',
            r'부채'
        ]
        
        # 연결된 노드 검색 설정
        self.connected_nodes_limit = 8
        
    def is_clause_question(self, question):
        """
        질문이 조항 관련 질문인지 판단
        """
        if self.verbose:
            self.logger.info(f"조항 질문 판단 - 질문: '{question}'")
        
        for i, pattern in enumerate(self.clause_patterns):
            if re.search(pattern, question):
                if self.verbose:
                    self.logger.info(f"조항 패턴 매칭 성공: 패턴 {i+1} '{pattern}'")
                return True
        
        if self.verbose:
            self.logger.info("조항 패턴 매칭 실패 - 모든 패턴 확인 완료")
        return False
    
    def _extract_keywords_from_query(self, query):
        """
        질문에서 키워드 추출 (질문에서 직접 추출)
        """
        import re
        
        # 불용어 제거 (질문에서 의미있는 단어만 추출)
        stop_words = ['은', '는', '이', '가', '을', '를', '에', '에서', '로', '으로', '와', '과', '의', '도', '만', '까지', '부터', '한', '할', '한다면', '수', '있나요', '인가요', '어떻게', '무엇', '언제', '어디서', '왜', '어떤']
        
        # 질문을 단어로 분리 (한글, 영문, 숫자만)
        words = re.findall(r'[가-힣a-zA-Z0-9]+', query)
        
        # 불용어 제거하고 2글자 이상인 단어만 선택
        keywords = []
        for word in words:
            if len(word) >= 2 and word not in stop_words:
                keywords.append(word)
        
        return keywords
    
    def _search_by_keywords(self, keywords, topN=10):
        """
        키워드로 Neo4j에서 직접 검색
        """
        if not keywords:
            return []
            
        try:
            with self.neo4j_driver.session(database=self.database_name) as session:
                all_results = []
                
                for keyword in keywords:
                    # Text 노드에서 키워드 검색
                    query = """
                    MATCH (t:Text)
                    WHERE t.text CONTAINS $keyword
                    RETURN t.numeric_id as textId, t.text as text,
                           'keyword_match' as match_type,
                           size(t.text) as text_length
                    ORDER BY text_length DESC
                    LIMIT $topN
                    """
                    
                    result = session.run(query, keyword=keyword, topN=topN)
                    keyword_results = [dict(record) for record in result]
                    all_results.extend(keyword_results)
                
                # 중복 제거
                seen_ids = set()
                unique_results = []
                for result in all_results:
                    if result['textId'] not in seen_ids:
                        seen_ids.add(result['textId'])
                        unique_results.append(result)
                
                if self.verbose:
                    self.logger.info(f"키워드 검색: 총 {len(all_results)}개 결과, 중복 제거 후 {len(unique_results)}개")
                
                return unique_results[:topN]
                
        except Exception as e:
            if self.verbose:
                self.logger.error(f"키워드 검색 중 오류: {e}")
            return []
    
    def search_clause_directly(self, question, topN=30):
        """
        조항 질문에 대해 직접 Neo4j에서 검색 (더 많은 결과 가져오기)
        """
        try:
            with self.neo4j_driver.session(database=self.database_name) as session:
                all_results = []
                
                # 1. 조항 번호 추출하여 검색
                clause_matches = re.findall(r'제?(\d+)조', question)
                if clause_matches:
                    for clause_num in clause_matches:
                        clause_number = int(clause_num)
                        results = self._search_by_clause_number(session, clause_number, topN)
                        all_results.extend(results)
                        if self.verbose:
                            self.logger.info(f"제{clause_number}조 검색 결과: {len(results)}개")
                
                # 2. 조항 유형으로 검색
                clause_type_patterns = {
                    '비밀유지': ['비밀유지', '비밀보호'],
                    '계약해지': ['계약해지', '해지'],
                    '손해배상': ['손해배상', '배상'],
                    '지적재산권': ['지적재산권', '저작권'],
                    '유지보수': ['유지보수', '지원'],
                    '대가': ['대가', '요금', '비용'],
                    '책임': ['책임', '의무'],
                    '효력': ['효력', '발효'],
                    '분쟁': ['분쟁', '소송']
                }
                
                for clause_type, keywords in clause_type_patterns.items():
                    if any(keyword in question for keyword in keywords):
                        results = self._search_by_clause_type(session, clause_type, topN)
                        all_results.extend(results)
                        if self.verbose:
                            self.logger.info(f"{clause_type} 조항 검색 결과: {len(results)}개")
                
                # 3. 일반적인 조항 검색
                if not all_results:
                    results = self._search_by_general_clause(session, question, topN)
                    all_results.extend(results)
                    if self.verbose:
                        self.logger.info(f"일반 조항 검색 결과: {len(results)}개")
                
                # 4. 중복 제거 (textId 기준)
                seen_ids = set()
                unique_results = []
                for result in all_results:
                    if result['textId'] not in seen_ids:
                        seen_ids.add(result['textId'])
                        unique_results.append(result)
                
                if self.verbose:
                    self.logger.info(f"총 조항 검색 결과: {len(unique_results)}개 (중복 제거 후)")
                
                return unique_results[:topN]
                
        except Exception as e:
            if self.verbose:
                self.logger.error(f"조항 직접 검색 중 오류: {e}")
            return []
    
    def _search_by_clause_number(self, session, clause_number, topN):
        """조항 번호로 검색"""
        all_results = []
        
        # 1. 정확한 조항 번호 검색
        query1 = """
        MATCH (t:Text)
        WHERE t.text CONTAINS $clause_query
        RETURN t.numeric_id as textId, t.text as text, 
               'exact_clause_match' as match_type,
               size(t.text) as text_length
        ORDER BY text_length DESC
        LIMIT $topN
        """
        
        clause_query = f"제{clause_number}조"
        result1 = session.run(query1, clause_query=clause_query, topN=topN)
        all_results.extend([dict(record) for record in result1])
        
        # 2. 조항 번호만으로 검색 (제 없이)
        query2 = """
        MATCH (t:Text)
        WHERE t.text CONTAINS $clause_query2
        RETURN t.numeric_id as textId, t.text as text, 
               'number_clause_match' as match_type,
               size(t.text) as text_length
        ORDER BY text_length DESC
        LIMIT $topN
        """
        
        clause_query2 = f"{clause_number}조"
        result2 = session.run(query2, clause_query2=clause_query2, topN=topN)
        all_results.extend([dict(record) for record in result2])
        
        # 3. 조항 제목으로 검색
        query3 = """
        MATCH (t:Text)
        WHERE t.text CONTAINS $clause_title
        RETURN t.numeric_id as textId, t.text as text, 
               'title_clause_match' as match_type,
               size(t.text) as text_length
        ORDER BY text_length DESC
        LIMIT $topN
        """
        
        clause_title = f"제{clause_number}조 ("
        result3 = session.run(query3, clause_title=clause_title, topN=topN)
        all_results.extend([dict(record) for record in result3])
        
        # 4. 조항 번호가 포함된 모든 텍스트 검색 (더 넓은 범위)
        query4 = """
        MATCH (t:Text)
        WHERE t.text =~ $clause_regex
        RETURN t.numeric_id as textId, t.text as text, 
               'regex_clause_match' as match_type,
               size(t.text) as text_length
        ORDER BY text_length DESC
        LIMIT $topN
        """
        
        clause_regex = f".*제{clause_number}조.*"
        result4 = session.run(query4, clause_regex=clause_regex, topN=topN)
        all_results.extend([dict(record) for record in result4])
        
        # 5. 조항 번호가 문장 시작에 있는 경우 검색
        query5 = """
        MATCH (t:Text)
        WHERE t.text STARTS WITH $clause_start
        RETURN t.numeric_id as textId, t.text as text, 
               'start_clause_match' as match_type,
               size(t.text) as text_length
        ORDER BY text_length DESC
        LIMIT $topN
        """
        
        clause_start = f"제{clause_number}조"
        result5 = session.run(query5, clause_start=clause_start, topN=topN)
        all_results.extend([dict(record) for record in result5])
        
        # 중복 제거
        seen_ids = set()
        unique_results = []
        for result in all_results:
            if result['textId'] not in seen_ids:
                seen_ids.add(result['textId'])
                unique_results.append(result)
        
        if self.verbose:
            self.logger.info(f"제{clause_number}조 검색: 총 {len(all_results)}개 결과, 중복 제거 후 {len(unique_results)}개")
        
        return unique_results[:topN]
    
    def _search_by_clause_type(self, session, clause_type, topN):
        """조항 유형으로 검색"""
        query = """
        MATCH (t:Text)
        WHERE t.text CONTAINS $clause_type
        RETURN t.numeric_id as textId, t.text as text,
               'clause_type_match' as match_type,
               size(t.text) as text_length
        ORDER BY text_length DESC
        LIMIT $topN
        """
        
        result = session.run(query, clause_type=clause_type, topN=topN)
        return [dict(record) for record in result]
    
    def _search_by_general_clause(self, session, question, topN):
        """일반적인 조항 검색"""
        query = """
        MATCH (t:Text)
        WHERE t.text CONTAINS $question
        RETURN t.numeric_id as textId, t.text as text,
               'general_clause_match' as match_type,
               size(t.text) as text_length
        ORDER BY text_length DESC
        LIMIT $topN
        """
        
        result = session.run(query, question=question, topN=topN)
        return [dict(record) for record in result]
    
    def get_connected_nodes(self, node_ids, limit=8):
        """
        주어진 노드들에 연결된 다른 노드들을 가져옵니다.
        
        Args:
            node_ids: 연결된 노드를 찾을 기준 노드 ID들
            limit: 가져올 연결된 노드의 최대 개수
            
        Returns:
            list: 연결된 노드들의 정보
        """
        if not node_ids:
            return []
            
        try:
            with self.neo4j_driver.session(database=self.database_name) as session:
                # 연결된 노드들을 찾는 쿼리
                query = """
                UNWIND $node_ids AS node_id
                MATCH (n:Node {numeric_id: node_id})-[r:Relation]-(connected:Node)
                WITH connected, count(r) as connection_count
                ORDER BY connection_count DESC, connected.numeric_id
                LIMIT $limit
                RETURN connected.numeric_id as numeric_id, 
                       connected.name as name,
                       connected.type as type,
                       connection_count
                """
                
                result = session.run(query, node_ids=node_ids, limit=limit)
                connected_nodes = [dict(record) for record in result]
                
                if self.verbose:
                    self.logger.info(f"연결된 노드 {len(connected_nodes)}개 발견")
                
                return connected_nodes
                
        except Exception as e:
            if self.verbose:
                self.logger.error(f"연결된 노드 검색 중 오류: {e}")
            return []
    
    def get_connected_text_nodes(self, node_ids, limit=8):
        """
        주어진 노드들에 연결된 Text 노드들을 가져옵니다.
        Relation 관계를 통해 관련 개념 노드들을 찾고, 그 노드들이 가리키는 다른 Text 노드들을 가져옵니다.
        
        Args:
            node_ids: 연결된 Text 노드를 찾을 기준 노드 ID들
            limit: 가져올 연결된 Text 노드의 최대 개수
            
        Returns:
            list: 연결된 Text 노드들의 정보
        """
        if not node_ids:
            return []
            
        try:
            with self.neo4j_driver.session(database=self.database_name) as session:
                # Relation 관계를 통해 관련 개념 노드들을 찾고, 그 노드들이 가리키는 다른 Text 노드들을 가져오는 쿼리
                query = """
                UNWIND $node_ids AS node_id
                MATCH (n:Node {numeric_id: node_id})-[:Relation]-(related:Node)
                MATCH (related)-[:Source]->(t:Text)
                WHERE t.numeric_id <> node_id  // 원본 노드와 다른 Text 노드만
                WITH t, count(related) as relation_count
                ORDER BY relation_count DESC, size(t.text) DESC
                LIMIT $limit
                RETURN t.numeric_id as textId, 
                       t.text as text,
                       relation_count
                """
                
                result = session.run(query, node_ids=node_ids, limit=limit)
                connected_text_nodes = [dict(record) for record in result]
                
                if self.verbose:
                    self.logger.info(f"연결된 Text 노드 {len(connected_text_nodes)}개 발견 (Relation 관계 사용)")
                
                return connected_text_nodes
                
        except Exception as e:
            if self.verbose:
                self.logger.error(f"연결된 Text 노드 검색 중 오류: {e}")
            return []
    
    def check_gds_graph(self):
        """
        GDS 그래프가 제대로 로드되었는지 확인
        """
        try:
            graph = self.gds_driver.graph.get('largekgrag_graph')
            node_count = graph.node_count()
            if self.verbose:
                self.logger.info(f"GDS 그래프 확인: {node_count}개 노드")
            return True
        except Exception as e:
            if self.verbose:
                self.logger.error(f"GDS 그래프 확인 실패: {e}")
            return False
    
    def retrieve_with_clause_search(self, query, topN=5):
        """
        조항 검색이 통합된 retrieve 메서드
        """
        if self.verbose:
            self.logger.info(f"향상된 검색 시작: {query}")
        
        # 0. GDS 그래프 확인
        if not self.check_gds_graph():
            if self.verbose:
                self.logger.warning("GDS 그래프를 사용할 수 없습니다. 조항 검색만 사용합니다.")
            # GDS 그래프가 없으면 조항 검색만 사용
            if self.is_clause_question(query):
                clause_results = self.search_clause_directly(query, topN=topN)
                if clause_results:
                    content = [result['text'] for result in clause_results]
                    context_ids = [result['textId'] for result in clause_results]
                    return content, context_ids
            return [], []
        
        # 1. 조항 질문인지 확인
        if self.is_clause_question(query):
            if self.verbose:
                self.logger.info("조항 관련 질문 감지 - 직접 조항 검색 시도")
            
            # 조항 직접 검색 (더 많은 결과 가져오기)
            clause_results = self.search_clause_directly(query, topN=30)
            if clause_results:
                if self.verbose:
                    self.logger.info(f"조항 검색으로 {len(clause_results)}개 결과 발견")
                
                # 조항 검색 결과를 텍스트로 변환
                content = [result['text'] for result in clause_results]
                context_ids = [result['textId'] for result in clause_results]
                
                # 조항과 연결된 추가 노드들 찾기
                if context_ids:
                    if self.verbose:
                        self.logger.info(f"조항 검색으로 {len(context_ids)}개 Text 노드 발견, 연결된 노드 검색 시작")
                    
                    # Text 노드에서 연결된 Node들을 찾기
                    connected_nodes = self._get_nodes_from_text_ids(context_ids)
                    if connected_nodes:
                        if self.verbose:
                            self.logger.info(f"연결된 노드 {len(connected_nodes)}개 발견")
                        
                        # 연결된 노드들의 Text 노드들 가져오기
                        additional_texts = self.get_connected_text_nodes(
                            [node['numeric_id'] for node in connected_nodes], 
                            limit=self.connected_nodes_limit
                        )
                        
                        if self.verbose:
                            self.logger.info(f"연결된 노드에서 {len(additional_texts)}개 추가 Text 노드 발견")
                        
                        # 추가 텍스트들을 기존 결과에 추가
                        added_count = 0
                        skipped_count = 0
                        
                        if self.verbose:
                            self.logger.info(f"기존 context_ids: {context_ids}")
                            self.logger.info(f"추가할 텍스트들: {[t['textId'] for t in additional_texts]}")
                        
                        for additional in additional_texts:
                            if additional['textId'] not in context_ids:
                                content.append(additional['text'])
                                context_ids.append(additional['textId'])
                                added_count += 1
                                if self.verbose:
                                    self.logger.info(f"새로운 텍스트 추가: ID {additional['textId']} - {additional['text'][:50]}...")
                            else:
                                skipped_count += 1
                                if self.verbose:
                                    self.logger.info(f"중복으로 스킵: ID {additional['textId']} - {additional['text'][:50]}...")
                        
                        if self.verbose:
                            self.logger.info(f"연결된 노드에서 {added_count}개 텍스트 추가됨, {skipped_count}개 중복으로 스킵됨")
                    else:
                        if self.verbose:
                            self.logger.info("연결된 노드를 찾을 수 없음")
                
                if self.verbose:
                    self.logger.info(f"최종 조항 검색 결과: {len(content)}개 (연결된 노드 포함)")
                
                return content[:topN], context_ids[:topN]
            else:
                if self.verbose:
                    self.logger.info("조항 검색에서 결과 없음 - 일반 검색으로 전환")
        
        # 2. 일반 LKG 검색 실행 (GDS PageRank 사용)
        if self.verbose:
            self.logger.info("일반 LKG 검색 실행 (GDS PageRank 사용)")
        
        try:
            # 조항 검색 결과를 personalization_dict로 사용
            personalization_dict = {}
            
            # 디버깅: 조항 질문 판단 결과 확인
            is_clause = self.is_clause_question(query)
            if self.verbose:
                self.logger.info(f"조항 질문 판단 결과: {is_clause}")
            
            # 조항 검색 또는 키워드 기반 검색
            if is_clause:
                if self.verbose:
                    self.logger.info("조항 검색 실행 중...")
                clause_results = self.search_clause_directly(query, topN=10)
                if self.verbose:
                    self.logger.info(f"조항 검색 결과: {len(clause_results) if clause_results else 0}개")
                
                if clause_results:
                    # 조항 검색 결과의 노드들을 personalization_dict에 추가
                    for result in clause_results:
                        text_id = result['textId']
                        # text_id를 node_id로 변환하여 personalization_dict에 추가
                        if hasattr(self, 'node_list') and text_id.isdigit():
                            faiss_index = int(text_id)
                            if faiss_index < len(self.node_list):
                                node_id = self.node_list[faiss_index]
                                personalization_dict[node_id] = 1.0  # 가중치 1.0으로 설정
                                if self.verbose:
                                    self.logger.info(f"personalization_dict에 노드 추가: {node_id}")
            else:
                # 조항 패턴이 아닌 경우 키워드 기반 검색
                if self.verbose:
                    self.logger.info("조항 패턴 아님 - 키워드 기반 검색 실행 중...")
                
                # 키워드 추출 (간단한 방법)
                keywords = self._extract_keywords_from_query(query)
                if self.verbose:
                    self.logger.info(f"추출된 키워드: {keywords}")
                
                if keywords:
                    # 키워드로 Neo4j에서 직접 검색
                    keyword_results = self._search_by_keywords(keywords, topN=10)
                    if self.verbose:
                        self.logger.info(f"키워드 검색 결과: {len(keyword_results) if keyword_results else 0}개")
                    
                    if keyword_results:
                        # 키워드 검색 결과의 노드들을 personalization_dict에 추가
                        for result in keyword_results:
                            text_id = result['textId']
                            # text_id가 문자열이면 int로 변환, 이미 int면 그대로 사용
                            if isinstance(text_id, str) and text_id.isdigit():
                                faiss_index = int(text_id)
                            elif isinstance(text_id, int):
                                faiss_index = text_id
                            else:
                                continue  # 숫자가 아닌 경우 건너뛰기
                            
                            if hasattr(self, 'node_list') and faiss_index < len(self.node_list):
                                node_id = self.node_list[faiss_index]
                                personalization_dict[node_id] = 0.8  # 키워드 검색은 가중치 0.8
                                if self.verbose:
                                    self.logger.info(f"키워드 검색으로 personalization_dict에 노드 추가: {node_id}")
            
            # personalization_dict가 있으면 PageRank 사용, 없으면 일반 검색
            if personalization_dict:
                if self.verbose:
                    self.logger.info(f"PageRank personalization_dict 사용: {len(personalization_dict)}개 노드")
                
                # GDS 그래프는 숫자 ID를 사용해야 함
                # personalization_dict의 키(실제 노드 ID)를 GDS 내부 숫자 ID로 변환
                if self.verbose:
                    self.logger.info("GDS 그래프용 personalization_dict 사용 (GDS 내부 숫자 ID로 변환)")
                
                # node_list를 사용하여 해시 ID → 숫자 인덱스 → GDS ID로 변환
                numeric_personalization_dict = {}
                
                # node_list가 있는 경우 사용
                if self.verbose:
                    self.logger.info(f"node_list 확인 - hasattr: {hasattr(self, 'node_list')}, 값: {getattr(self, 'node_list', None)}")
                    if hasattr(self, 'node_list') and self.node_list:
                        self.logger.info(f"node_list 길이: {len(self.node_list)}")
                        self.logger.info(f"node_list 타입: {type(self.node_list)}")
                        self.logger.info(f"node_list 첫 번째 요소: {self.node_list[0] if self.node_list else 'None'}")
                
                if hasattr(self, 'node_list') and self.node_list:
                    if self.verbose:
                        self.logger.info(f"node_list 사용하여 변환 (길이: {len(self.node_list)})")
                        self.logger.info(f"personalization_dict 키 개수: {len(personalization_dict)}")
                        self.logger.info(f"첫 번째 키 예시: {list(personalization_dict.keys())[:3]}")
                    
                    for node_id, weight in personalization_dict.items():
                        try:
                            # node_list에서 해시 ID의 인덱스 찾기
                            if node_id in self.node_list:
                                numeric_index = self.node_list.index(node_id)
                                # GDS 그래프에서 해당 인덱스의 노드 ID 가져오기
                                with self.neo4j_driver.session(database=self.database_name) as session:
                                    result = session.run(
                                        "MATCH (n:Node) WHERE n.numeric_id = $numeric_id RETURN id(n) as gds_id", 
                                        numeric_id=numeric_index
                                    )
                                    record = result.single()
                                    if record:
                                        gds_id = record["gds_id"]
                                        numeric_personalization_dict[gds_id] = weight
                                        if self.verbose and len(numeric_personalization_dict) <= 3:
                                            self.logger.info(f"해시 ID {node_id[:20]}... -> 인덱스 {numeric_index} -> GDS ID {gds_id}")
                                    else:
                                        if self.verbose:
                                            self.logger.warning(f"인덱스 {numeric_index}에 대한 GDS ID를 찾을 수 없음")
                            else:
                                if self.verbose:
                                    self.logger.warning(f"해시 ID {node_id[:20]}...가 node_list에 없음")
                        except Exception as e:
                            if self.verbose:
                                self.logger.warning(f"해시 ID 변환 실패 {node_id}: {e}")
                            continue
                else:
                    # node_list가 없는 경우 기존 방식 사용
                    if self.verbose:
                        self.logger.info(f"node_list 없음 - hasattr: {hasattr(self, 'node_list')}, 값: {getattr(self, 'node_list', None)}")
                    
                    for node_id, weight in personalization_dict.items():
                        try:
                            # Neo4j에서 노드의 내부 ID 가져오기 (GDS에서 사용하는 ID)
                            with self.neo4j_driver.session(database=self.database_name) as session:
                                result = session.run(
                                    "MATCH (n:Node) WHERE n.id = $node_id RETURN id(n) as gds_id", 
                                    node_id=node_id
                                )
                                record = result.single()
                                if record:
                                    gds_id = record["gds_id"]
                                    numeric_personalization_dict[gds_id] = weight
                                    if self.verbose:
                                        self.logger.info(f"노드 ID {node_id[:20]}... -> GDS ID {gds_id}")
                                else:
                                    if self.verbose:
                                        self.logger.warning(f"노드 ID {node_id}에 대한 GDS ID를 찾을 수 없음")
                        except Exception as e:
                            if self.verbose:
                                self.logger.warning(f"노드 ID 변환 실패 {node_id}: {e}")
                            continue
                
                if numeric_personalization_dict:
                    if self.verbose:
                        self.logger.info(f"숫자 ID로 변환된 personalization_dict: {len(numeric_personalization_dict)}개 노드")
                    # personalization_dict를 직접 사용하여 PageRank 실행
                    content, scores = self.pagerank(numeric_personalization_dict, self.topN, self.sampling_area)
                else:
                    if self.verbose:
                        self.logger.warning("숫자 ID 변환 실패 - 일반 검색 사용")
                    content, scores = super().retrieve_passages(query)
            else:
                if self.verbose:
                    self.logger.info("personalization_dict 없음 - 일반 검색 사용")
                
                # 일반 검색을 실행하되, 결과에서 personalization_dict를 추출하여 node_list 변환 시도
                # super().retrieve_passages(query) 대신 직접 retrieve_topk_nodes 호출
                if self.verbose:
                    self.logger.info("retrieve_topk_nodes 직접 호출하여 personalization_dict 생성")
                
                # retrieve_topk_nodes를 직접 호출하여 personalization_dict 생성
                topk_nodes = self.retrieve_topk_nodes(query, self.topN)
                
                if topk_nodes:
                    if self.verbose:
                        self.logger.info(f"retrieve_topk_nodes 결과: {len(topk_nodes)}개 노드")
                        self.logger.info(f"topk_nodes 예시: {topk_nodes[:3]}")
                    
                    # topk_nodes에서 personalization_dict 생성
                    temp_personalization_dict = {}
                    for node_id in topk_nodes:
                        temp_personalization_dict[node_id] = 1.0
                    
                    if temp_personalization_dict:
                        if self.verbose:
                            self.logger.info(f"임시 personalization_dict 생성: {len(temp_personalization_dict)}개 노드")
                        
                        # node_list를 사용하여 변환
                        numeric_personalization_dict = {}
                        for node_id, weight in temp_personalization_dict.items():
                            try:
                                # node_id가 숫자 인덱스인지 확인
                                if node_id.isdigit() and int(node_id) < len(self.node_list):
                                    numeric_index = int(node_id)
                                    hash_id = self.node_list[numeric_index]
                                    with self.neo4j_driver.session(database=self.database_name) as session:
                                        result = session.run(
                                            "MATCH (n:Node) WHERE n.id = $hash_id RETURN id(n) as gds_id", 
                                            hash_id=hash_id
                                        )
                                        record = result.single()
                                        if record:
                                            gds_id = record["gds_id"]
                                            numeric_personalization_dict[gds_id] = weight
                                            if self.verbose and len(numeric_personalization_dict) <= 3:
                                                self.logger.info(f"숫자 인덱스 {node_id} -> 해시 ID {hash_id[:20]}... -> GDS ID {gds_id}")
                                        else:
                                            if self.verbose:
                                                self.logger.warning(f"인덱스 {numeric_index}에 대한 GDS ID를 찾을 수 없음")
                                elif node_id in self.node_list:
                                    # 기존 로직 (해시 ID인 경우)
                                    numeric_index = self.node_list.index(node_id)
                                    with self.neo4j_driver.session(database=self.database_name) as session:
                                        result = session.run(
                                            "MATCH (n:Node) WHERE n.numeric_id = $numeric_id RETURN id(n) as gds_id", 
                                            numeric_id=numeric_index
                                        )
                                        record = result.single()
                                        if record:
                                            gds_id = record["gds_id"]
                                            numeric_personalization_dict[gds_id] = weight
                                            if self.verbose:
                                                self.logger.info(f"해시 ID {node_id[:20]}... -> 인덱스 {numeric_index} -> GDS ID {gds_id}")
                                        else:
                                            if self.verbose:
                                                self.logger.warning(f"인덱스 {numeric_index}에 대한 GDS ID를 찾을 수 없음")
                                else:
                                    if self.verbose:
                                        self.logger.warning(f"node_id {node_id}가 숫자 인덱스도 해시 ID도 아님")
                            except Exception as e:
                                if self.verbose:
                                    self.logger.warning(f"node_id 변환 실패 {node_id}: {e}")
                                continue
                        
                        if numeric_personalization_dict:
                            if self.verbose:
                                self.logger.info(f"✅ node_list 변환 성공: {len(numeric_personalization_dict)}개 노드")
                            # 변환된 personalization_dict로 PageRank 실행
                            content, scores = self.pagerank(numeric_personalization_dict, self.topN, self.sampling_area)
                        else:
                            if self.verbose:
                                self.logger.warning("node_list 변환 실패 - 일반 검색 사용")
                            content, scores = super().retrieve_passages(query)
                    else:
                        if self.verbose:
                            self.logger.warning("personalization_dict 생성 실패 - 일반 검색 사용")
                        content, scores = super().retrieve_passages(query)
                else:
                    if self.verbose:
                        self.logger.warning("retrieve_topk_nodes 결과 없음 - 일반 검색 사용")
                    content, scores = super().retrieve_passages(query)
            
            # scores를 context_ids로 변환 (임시 ID 생성)
            context_ids = [f"lkg_{i}" for i in range(len(content))]
            
            # 연결된 노드들 추가 검색
            if content and len(content) > 0:
                try:
                    # 1. 조항 검색으로 연결된 노드들 찾기
                    clause_results = self.search_clause_directly(query, topN=10)
                    if clause_results:
                        clause_text_ids = [result['textId'] for result in clause_results]
                        connected_nodes = self._get_nodes_from_text_ids(clause_text_ids)
                        if connected_nodes:
                            # 연결된 노드들의 추가 Text 노드들 가져오기
                            additional_texts = self.get_connected_text_nodes(
                                [node['numeric_id'] for node in connected_nodes], 
                                limit=self.connected_nodes_limit
                            )
                            
                            # 추가 텍스트들을 기존 결과에 추가 (중복 제거)
                            existing_content = set(content)
                            for additional in additional_texts:
                                if additional['text'] not in existing_content:
                                    content.append(additional['text'])
                                    context_ids.append(f"clause_connected_{additional['textId']}")
                                    existing_content.add(additional['text'])
                            
                            if self.verbose:
                                self.logger.info(f"조항 기반 연결 노드에서 {len(additional_texts)}개 추가 텍스트 발견")
                    
                    # 2. 키워드 기반 연결 노드 검색 (조항 검색 결과가 없거나 부족한 경우)
                    if len(content) < topN and hasattr(self, 'node_list') and self.node_list:
                        # 질문에서 키워드 추출
                        keywords = [word.strip() for word in query.split() if len(word.strip()) > 2]
                        
                        if keywords:
                            # 키워드와 관련된 노드들 찾기
                            keyword_nodes = []
                            for node in self.node_list:
                                # node_list가 문자열 리스트인 경우 처리
                                if isinstance(node, str):
                                    node_name = node.lower()
                                else:
                                    node_name = node.get('name', '').lower()
                                
                                if any(keyword.lower() in node_name for keyword in keywords):
                                    if isinstance(node, str):
                                        # 문자열인 경우 node_list에서 인덱스 찾기
                                        try:
                                            node_index = self.node_list.index(node)
                                            keyword_nodes.append(node_index)
                                        except ValueError:
                                            continue
                                    else:
                                        keyword_nodes.append(node.get('numeric_id'))
                            
                            if keyword_nodes:
                                # 키워드 노드들에서 연결된 Text 노드들 가져오기
                                additional_texts = self.get_connected_text_nodes(
                                    keyword_nodes, 
                                    limit=self.connected_nodes_limit
                                )
                                
                                # 추가 텍스트들을 기존 결과에 추가 (중복 제거)
                                existing_content = set(content)
                                for additional in additional_texts:
                                    if additional['text'] not in existing_content:
                                        content.append(additional['text'])
                                        context_ids.append(f"keyword_connected_{additional['textId']}")
                                        existing_content.add(additional['text'])
                                
                                if self.verbose:
                                    self.logger.info(f"키워드 기반 연결 노드에서 {len(additional_texts)}개 추가 텍스트 발견")
                
                except Exception as e:
                    if self.verbose:
                        self.logger.warning(f"연결된 노드 검색 중 오류: {e}")
            
            if self.verbose:
                self.logger.info(f"최종 LKG 검색 결과: {len(content)}개 (연결된 노드 포함)")
            
            return content, context_ids
            
        except Exception as e:
            if self.verbose:
                self.logger.error(f"일반 LKG 검색 중 오류: {e}")
            return [], []
    
    def _get_nodes_from_text_ids(self, text_ids):
        """
        Text 노드 ID들로부터 연결된 Node들을 찾습니다.
        """
        if not text_ids:
            return []
            
        try:
            with self.neo4j_driver.session(database=self.database_name) as session:
                query = """
                UNWIND $text_ids AS text_id
                MATCH (n:Node)-[:Source]->(t:Text {numeric_id: text_id})
                RETURN DISTINCT n.numeric_id as numeric_id, 
                               n.name as name,
                               n.type as type
                """
                
                result = session.run(query, text_ids=text_ids)
                return [dict(record) for record in result]
                
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Text ID에서 Node 검색 중 오류: {e}")
            return []
    
    def convert_numeric_id_to_name(self, numeric_id):
        """
        Enhanced version of convert_numeric_id_to_name using node_list like original
        """
        try:
            if numeric_id.isdigit():
                # FAISS 인덱스 번호를 node_list 인덱스로 사용
                faiss_index = int(numeric_id)
                
                # node_list에서 해당 인덱스의 노드 ID 가져오기
                if hasattr(self, 'node_list') and faiss_index < len(self.node_list):
                    node_id = self.node_list[faiss_index]
                    
                    # GraphML에서 노드 타입 확인 (entity 타입만 Neo4j에서 검색)
                    if hasattr(self, 'kg_graph') and node_id in self.kg_graph.nodes:
                        node_type = self.kg_graph.nodes[node_id].get('type', '')
                        if 'entity' not in node_type:
                            # entity가 아닌 경우 (event, concept 등)는 노드 ID 그대로 반환
                            return node_id
                    
                    # Neo4j에서 해당 노드 ID로 검색 (entity 타입만)
                    try:
                        with self.neo4j_driver.session(database=self.database_name) as session:
                            result = session.run(
                                "MATCH (n:Node) WHERE n.id = $node_id RETURN n.name as name", 
                                node_id=node_id
                            )
                            record = result.single()
                            if record and record['name']:
                                return record['name']
                            else:
                                # Neo4j에서 찾을 수 없으면 노드 ID 그대로 반환
                                return node_id
                    except Exception as neo4j_error:
                        if self.verbose:
                            self.logger.debug(f"Neo4j query failed for node_id {node_id}: {neo4j_error}")
                        return node_id
                else:
                    if self.verbose:
                        self.logger.warning(f"FAISS 인덱스 {faiss_index}가 node_list 범위를 벗어났습니다.")
                    return f"OutOfRange_Node_{numeric_id}"
            else:
                return numeric_id
        except Exception as e:
            if self.verbose:
                self.logger.warning(f"Error converting numeric_id {numeric_id}: {e}")
            return f"Error_Node_{numeric_id}"
    
    def retrieve_topk_nodes(self, query, top_k_nodes=2):
        """
        Enhanced version of retrieve_topk_nodes with better error handling
        """
        try:
            # extract entities from the query
            entities = self.ner(query)
            if self.verbose:
                self.logger.info(f"largekgRAG : LLM Extracted entities: {entities}")
            if len(entities) == 0:
                entities = [query]
            num_entities = len(entities)
            initial_nodes = []
            
            for entity in entities:
                try:
                    entity_embedding = self.sentence_encoder.encode([entity])
                    D, I = self.node_faiss_index.search(entity_embedding, top_k_nodes)
                    if self.verbose:
                        self.logger.info(f"largekgRAG : Search results - Distances: {D}, Indices: {I}")
                    initial_nodes += [str(i) for i in I[0]]
                except Exception as e:
                    if self.verbose:
                        self.logger.warning(f"Error searching for entity '{entity}': {e}")
                    continue
                    
            if self.verbose:
                self.logger.info(f"largekgRAG : Initial nodes: {initial_nodes}")
            
            if not initial_nodes:
                if self.verbose:
                    self.logger.warning("No initial nodes found")
                return []
            
            name_id_map = {}
            for node_id in initial_nodes:
                try:
                    name = self.convert_numeric_id_to_name(node_id)
                    if name and not name.startswith("Error_") and not name.startswith("Unknown_"):
                        name_id_map[name] = node_id
                except Exception as e:
                    if self.verbose:
                        self.logger.warning(f"Error converting node_id {node_id}: {e}")
                    continue
                    
            if not name_id_map:
                if self.verbose:
                    self.logger.warning("No valid nodes found after conversion")
                return []
                
        except Exception as e:
            if self.verbose:
                self.logger.error(f"largekgRAG : Error in retrieve_topk_nodes: {e}")
                import traceback
                self.logger.error(f"largekgRAG : Traceback: {traceback.format_exc()}")
            return []  
            
        topk_nodes = list(set(initial_nodes))
        
        # convert the numeric id to string and filter again then return numeric id
        keywords_before_filter = [self.convert_numeric_id_to_name(n) for n in initial_nodes if n in name_id_map.values()]
        
        if not keywords_before_filter:
            if self.verbose:
                self.logger.warning("No keywords for filtering")
            return []
            
        filtered_keywords = self.llm_generator.large_kg_filter_keywords_with_entity(query, keywords_before_filter)
    
        # Second pass: Add filtered keywords
        filtered_top_k_nodes = []
        filter_log_dict = {}
        match_threshold = 0.8
        if self.verbose:
            self.logger.info(f"largekgRAG : Filtered Before Match Keywords Candidate: {filtered_keywords}")
            
        for keyword in filtered_keywords:
            # Check for an exact match first
            if keyword in name_id_map:
                filtered_top_k_nodes.append(name_id_map[keyword])
                filter_log_dict[keyword] = name_id_map[keyword]
            else:
                # Look for close matches using difflib's get_close_matches
                close_matches = get_close_matches(keyword, name_id_map.keys(), n=1, cutoff=match_threshold)
                
                if close_matches:
                    # If a close match is found, add the corresponding node
                    filtered_top_k_nodes.append(name_id_map[close_matches[0]])
                
                filter_log_dict[keyword] = name_id_map[close_matches[0]] if close_matches else None
                
        if self.verbose:
            self.logger.info(f"largekgRAG : Filtered After Match Keywords Candidate: {filter_log_dict}")
        
        topk_nodes = list(set(filtered_top_k_nodes))
        if len(topk_nodes) > 2 * num_entities:
            topk_nodes = topk_nodes[:2 * num_entities]
            
        if self.verbose:
            self.logger.info(f"largekgRAG : Final topk_nodes: {topk_nodes}")
            
        return topk_nodes
    
    def retrieve(self, query, topN=5):
        """
        기본 retrieve 메서드를 향상된 버전으로 오버라이드
        """
        return self.retrieve_with_clause_search(query, topN)
