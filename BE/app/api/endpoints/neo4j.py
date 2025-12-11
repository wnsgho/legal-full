from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import asyncio
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

from app.schemas.neo4j import (
    Neo4jConnectionInfo,
    Neo4jGraphDataResponse,
    Neo4jStatsResponse,
    Neo4jNode,
    Neo4jRelationship
)

router = APIRouter()


def get_neo4j_driver(connection_info: Neo4jConnectionInfo):
    """Neo4j 드라이버 생성"""
    try:
        driver = GraphDatabase.driver(
            connection_info.serverUrl,
            auth=(connection_info.username, connection_info.password)
        )
        return driver
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Neo4j 연결 실패: {str(e)}")


@router.post("/neo4j/databases")
async def get_neo4j_databases(connection_info: Neo4jConnectionInfo):
    """Neo4j 데이터베이스 목록 조회"""
    driver = None
    try:
        driver = get_neo4j_driver(connection_info)
        
        # system 데이터베이스에서 데이터베이스 목록 조회
        with driver.session(database="system") as session:
            result = session.run("SHOW DATABASES")
            databases = []
            for record in result:
                db_name = record["name"]
                db_status = record.get("currentStatus", "unknown")
                # system 데이터베이스는 제외 (선택 사항)
                if db_name != "system":
                    databases.append({
                        "name": db_name,
                        "status": db_status,
                        "default": record.get("default", False)
                    })
            
            return {
                "success": True,
                "databases": databases
            }
            
    except ServiceUnavailable:
        raise HTTPException(status_code=503, detail="Neo4j 서버에 연결할 수 없습니다")
    except AuthError:
        raise HTTPException(status_code=401, detail="Neo4j 인증 실패")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터베이스 목록 조회 실패: {str(e)}")
    finally:
        if driver:
            driver.close()


@router.post("/neo4j/stats", response_model=Neo4jStatsResponse)
async def get_neo4j_stats(connection_info: Neo4jConnectionInfo):
    """Neo4j 데이터베이스 통계 조회"""
    driver = None
    try:
        driver = get_neo4j_driver(connection_info)
        
        with driver.session(database=connection_info.database) as session:
            # 노드 수 조회
            node_result = session.run("MATCH (n) RETURN COUNT(n) as node_count")
            node_count = node_result.single()["node_count"]
            
            # 관계 수 조회
            rel_result = session.run("MATCH ()-[r]->() RETURN COUNT(r) as rel_count")
            rel_count = rel_result.single()["rel_count"]
            
            return Neo4jStatsResponse(
                success=True,
                nodeCount=node_count,
                relationshipCount=rel_count,
                database=connection_info.database
            )
            
    except ServiceUnavailable:
        raise HTTPException(status_code=503, detail="Neo4j 서버에 연결할 수 없습니다")
    except AuthError:
        raise HTTPException(status_code=401, detail="Neo4j 인증 실패")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")
    finally:
        if driver:
            driver.close()


@router.post("/neo4j/graph-data", response_model=Neo4jGraphDataResponse)
async def get_neo4j_graph_data(connection_info: Neo4jConnectionInfo):
    """Neo4j 그래프 데이터 조회"""
    driver = None
    try:
        driver = get_neo4j_driver(connection_info)
        
        with driver.session(database=connection_info.database) as session:
            # 노드 조회
            node_query = f"""
            MATCH (n)
            RETURN id(n) as id, labels(n) as labels, properties(n) as properties
            LIMIT {connection_info.limit}
            """
            node_result = session.run(node_query)
            nodes = [
                Neo4jNode(
                    id=record["id"],
                    labels=record["labels"],
                    properties=dict(record["properties"])
                )
                for record in node_result
            ]
            
            # 관계 조회
            rel_query = f"""
            MATCH (a)-[r]->(b)
            RETURN id(r) as id, type(r) as type, id(a) as start_node, id(b) as end_node, properties(r) as properties
            LIMIT {connection_info.limit}
            """
            rel_result = session.run(rel_query)
            relationships = [
                Neo4jRelationship(
                    id=record["id"],
                    type=record["type"],
                    start_node=record["start_node"],
                    end_node=record["end_node"],
                    properties=dict(record["properties"])
                )
                for record in rel_result
            ]
            
            return Neo4jGraphDataResponse(
                success=True,
                nodes=nodes,
                relationships=relationships,
                database=connection_info.database
            )
            
    except ServiceUnavailable:
        raise HTTPException(status_code=503, detail="Neo4j 서버에 연결할 수 없습니다")
    except AuthError:
        raise HTTPException(status_code=401, detail="Neo4j 인증 실패")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"그래프 데이터 조회 실패: {str(e)}")
    finally:
        if driver:
            driver.close()
