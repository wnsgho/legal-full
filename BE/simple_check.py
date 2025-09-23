from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

try:
    load_dotenv()
    uri = os.getenv('NEO4J_URI', 'neo4j://127.0.0.1:7687')
    print(f"Neo4j URI: {uri}")
    
    driver = GraphDatabase.driver(uri)
    print("Neo4j 드라이버 생성 성공")
    
    with driver.session() as session:
        print("세션 생성 성공")
        
        # 간단한 쿼리 테스트
        result = session.run('RETURN 1 as test')
        test_value = result.single()['test']
        print(f"기본 쿼리 테스트: {test_value}")
        
        # 노드 개수 확인
        result = session.run('MATCH (n) RETURN count(n) as count')
        count = result.single()['count']
        print(f'전체 노드 수: {count}')
        
        # Node 라벨 확인
        result = session.run('MATCH (n:Node) RETURN count(n) as count')
        node_count = result.single()['count']
        print(f'Node 라벨 노드 수: {node_count}')
        
        if node_count > 0:
            # 샘플 노드 확인
            result = session.run('MATCH (n:Node) RETURN n.numeric_id, n.name LIMIT 3')
            print('샘플 노드들:')
            for record in result:
                print(f'  numeric_id: {record["numeric_id"]}, name: {record["name"]}')
        
    driver.close()
    print("연결 종료 성공")
    
except Exception as e:
    print(f"오류 발생: {e}")
    import traceback
    traceback.print_exc()




