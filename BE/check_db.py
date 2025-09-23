from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()
uri = os.getenv('NEO4J_URI', 'neo4j://127.0.0.1:7687')
driver = GraphDatabase.driver(uri)

with driver.session() as session:
    # 노드 개수 확인
    result = session.run('MATCH (n) RETURN count(n) as count')
    count = result.single()['count']
    print(f'전체 노드 수: {count}')
    
    # Node 라벨이 있는 노드 확인
    result = session.run('MATCH (n:Node) RETURN count(n) as count')
    node_count = result.single()['count']
    print(f'Node 라벨 노드 수: {node_count}')
    
    # numeric_id가 있는 노드 확인
    result = session.run('MATCH (n:Node) WHERE n.numeric_id IS NOT NULL RETURN count(n) as count')
    numeric_count = result.single()['count']
    print(f'numeric_id가 있는 노드 수: {numeric_count}')
    
    # 샘플 노드 확인
    result = session.run('MATCH (n:Node) WHERE n.numeric_id IS NOT NULL RETURN n.numeric_id, n.name LIMIT 5')
    print('샘플 노드들:')
    for record in result:
        print(f'  numeric_id: {record["numeric_id"]}, name: {record["name"]}')
    
    # 특정 numeric_id 확인 (로그에서 본 것들)
    test_ids = ['491', '1876', '385', '176', '620']
    print(f'\n테스트 numeric_id들 확인:')
    for test_id in test_ids:
        result = session.run('MATCH (n:Node {numeric_id: $id}) RETURN n.numeric_id, n.name', id=int(test_id))
        record = result.single()
        if record:
            print(f'  {test_id}: {record["name"]}')
        else:
            print(f'  {test_id}: 찾을 수 없음')

driver.close()




