from tqdm import tqdm
import argparse
import os
import csv 
import json
import re
import hashlib

# Increase the field size limit
csv.field_size_limit(10 * 1024 * 1024)  # 10 MB limit

def read_json_safely(filepath):
    """안전한 JSON 읽기 (인코딩 문제 해결) - Windows cp949 오류 해결"""
    # 1차: UTF-8 우선 시도 (가장 일반적)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return content
    except Exception as e:
        print(f"  - UTF-8 인코딩 실패: {e}")
    
    # 2차: UTF-8 BOM 포함 시도
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()
            return content
    except Exception as e:
        print(f"  - UTF-8-sig 인코딩 실패: {e}")
    
    # 3차: 바이너리 모드로 읽고 디코딩 시도 (Windows cp949 오류 해결)
    try:
        with open(filepath, 'rb') as f:
            content_bytes = f.read()
            
        # UTF-8 BOM 제거 시도
        if content_bytes.startswith(b'\xef\xbb\xbf'):
            content_bytes = content_bytes[3:]
            try:
                return content_bytes.decode('utf-8')
            except:
                pass
        
        # 다양한 인코딩으로 디코딩 시도 (UTF-8 우선)
        for encoding in ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1']:
            try:
                return content_bytes.decode(encoding, errors='ignore')
            except:
                continue
        
        # 마지막 수단: errors='ignore'로 강제 디코딩
        try:
            return content_bytes.decode('utf-8', errors='ignore')
        except:
            pass
            
    except Exception as e:
        print(f"  - 바이너리 모드 읽기 실패: {e}")
    
    print(f"❌ 모든 인코딩 시도 실패: {filepath}")
    return None

# Function to compute a hash ID from text
def compute_hash_id(text):
    # Use SHA-256 to generate a hash
    hash_object = hashlib.sha256(text.encode('utf-8'))
    return hash_object.hexdigest()  # Return hash as a hex string

def clean_text(text):
    # remove NUL as well
    
    new_text = text.replace("\n", " ") \
        .replace("\r", " ") \
        .replace("\t", " ") \
        .replace("\v", " ") \
        .replace("\f", " ") \
        .replace("\b", " ") \
        .replace("\a", " ") \
        .replace("\x1b", " ") \
        .replace(";", ",")
    new_text = new_text.replace("\x00", "")
    new_text = re.sub(r'\s+', ' ', new_text).strip()

    return new_text

def remove_NUL(text):
    return text.replace("\x00", "")

def json2csv(dataset, data_dir, output_dir, test=False):
    """
    Convert JSON files to CSV files for nodes, edges, and missing concepts.

    Args:
        dataset (str): Name of the dataset.
        data_dir (str): Directory containing the JSON files.
        output_dir (str): Directory to save the output CSV files.
        test (bool): If True, run in test mode (process only 3 files).
    """
    visited_nodes = set()
    visited_hashes = set()

    all_entities = set()
    all_events = set()
    all_relations = set()

    file_dir_list = [f for f in os.listdir(data_dir) if dataset in f]
    file_dir_list = sorted(file_dir_list)
    if test:
        file_dir_list = file_dir_list[:3]
    print("Loading data from the json files")
    print("Number of files: ", len(file_dir_list))

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # Define output file paths
    node_csv_without_emb = os.path.join(output_dir, f"triple_nodes_{dataset}_from_json_without_emb.csv")
    edge_csv_without_emb = os.path.join(output_dir, f"triple_edges_{dataset}_from_json_without_emb.csv")
    node_text_file = os.path.join(output_dir, f"text_nodes_{dataset}_from_json.csv")
    edge_text_file = os.path.join(output_dir, f"text_edges_{dataset}_from_json.csv")
    missing_concepts_file = os.path.join(output_dir, f"missing_concepts_{dataset}_from_json.csv")

    if test:
        node_text_file = os.path.join(output_dir, f"text_nodes_{dataset}_from_json_test.csv")
        edge_text_file = os.path.join(output_dir, f"text_edges_{dataset}_from_json_test.csv")
        node_csv_without_emb = os.path.join(output_dir, f"triple_nodes_{dataset}_from_json_without_emb_test.csv")
        edge_csv_without_emb = os.path.join(output_dir, f"triple_edges_{dataset}_from_json_without_emb_test.csv")
        missing_concepts_file = os.path.join(output_dir, f"missing_concepts_{dataset}_from_json_test.csv")

    # Open CSV files for writing
    with open(node_text_file, "w", newline='', encoding='utf-8', errors='ignore') as csvfile_node_text, \
         open(edge_text_file, "w", newline='', encoding='utf-8', errors='ignore') as csvfile_edge_text, \
         open(node_csv_without_emb, "w", newline='', encoding='utf-8', errors='ignore') as csvfile_node, \
         open(edge_csv_without_emb, "w", newline='', encoding='utf-8', errors='ignore') as csvfile_edge:

        csv_writer_node_text = csv.writer(csvfile_node_text)
        csv_writer_edge_text = csv.writer(csvfile_edge_text)
        writer_node = csv.writer(csvfile_node)
        writer_edge = csv.writer(csvfile_edge)

        # Write headers
        csv_writer_node_text.writerow(["text_id:ID", "original_text", ":LABEL"])
        csv_writer_edge_text.writerow([":START_ID", ":END_ID", ":TYPE"])
        writer_node.writerow(["name:ID", "type", "concepts", "synsets", ":LABEL"])
        writer_edge.writerow([":START_ID", ":END_ID", "relation", "concepts", "synsets", ":TYPE"])

        # Process each file
        for file_dir in tqdm(file_dir_list):
            print("Processing file for file ids: ", file_dir)
            
            # 안전한 JSON 읽기
            json_content = read_json_safely(os.path.join(data_dir, file_dir))
            if json_content is None:
                print(f"  ❌ 파일 읽기 실패: {file_dir}")
                continue
            
            # 각 줄을 처리
            for line in json_content.split('\n'):
                if not line.strip():
                    continue
                try:
                    # JSON 파싱 시도 (인코딩 문제 해결)
                    try:
                        data = json.loads(line.strip())
                    except json.JSONDecodeError as json_error:
                        print(f"  - JSON 파싱 오류: {json_error}")
                        print(f"  - 문제가 된 라인: {line[:100]}...")
                        continue
                    except Exception as e:
                        print(f"  - 예상치 못한 오류: {e}")
                        continue
                    
                    # 데이터 구조 검증
                    if not isinstance(data, dict):
                        print(f"  - 데이터가 딕셔너리가 아님: {type(data)}")
                        continue
                    
                    if "original_text" not in data:
                        print(f"  - original_text 필드 없음: {data.keys()}")
                        continue
                    
                    original_text = data["original_text"]
                    original_text = remove_NUL(original_text)
                    if "Here is the passage." in original_text:
                        original_text = original_text.split("Here is the passage.")[-1]
                    eot_token = "<|eot_id|>"
                    original_text = original_text.split(eot_token)[0]

                    text_hash_id = compute_hash_id(original_text)

                    # Write the original text as nodes
                    if text_hash_id not in visited_hashes:
                        visited_hashes.add(text_hash_id)
                        csv_writer_node_text.writerow([text_hash_id, original_text, "Text"])

                    file_id = str(data["id"])
                    
                    # 필수 필드 검증
                    required_fields = ["entity_relation_dict", "event_entity_relation_dict", "event_relation_dict"]
                    for field in required_fields:
                        if field not in data:
                            print(f"  - 필수 필드 없음: {field}")
                            data[field] = []  # 빈 리스트로 초기화
                    
                    entity_relation_dict = data["entity_relation_dict"]
                    event_entity_relation_dict = data["event_entity_relation_dict"]
                    event_relation_dict = data["event_relation_dict"]

                    # Process entity triples
                    entity_triples = []
                    for entity_triple in entity_relation_dict:
                        try:
                            assert isinstance(entity_triple["Head"], str)
                            assert isinstance(entity_triple["Relation"], str)
                            assert isinstance(entity_triple["Tail"], str)

                            head_entity = entity_triple["Head"]
                            relation = entity_triple["Relation"]
                            tail_entity = entity_triple["Tail"]

                            # Clean the text
                            head_entity = clean_text(head_entity)
                            relation = clean_text(relation)
                            tail_entity = clean_text(tail_entity)

                            if head_entity.isspace() or len(head_entity) == 0 or tail_entity.isspace() or len(tail_entity) == 0:
                                continue

                            entity_triples.append((head_entity, relation, tail_entity))
                        except:
                            print(f"Error processing entity triple: {entity_triple}")
                            continue

                    # Process event triples
                    event_triples = []
                    for event_triple in event_relation_dict:
                        try:
                            assert isinstance(event_triple["Head"], str)
                            assert isinstance(event_triple["Relation"], str)
                            assert isinstance(event_triple["Tail"], str)
                            head_event = event_triple["Head"]
                            relation = event_triple["Relation"]
                            tail_event = event_triple["Tail"]
                            
                            # Clean the text
                            head_event = clean_text(head_event)
                            relation = clean_text(relation)
                            tail_event = clean_text(tail_event)

                            if head_event.isspace() or len(head_event) == 0 or tail_event.isspace() or len(tail_event) == 0:
                                continue

                            event_triples.append((head_event, relation, tail_event))
                        except:
                            print(f"Error processing event triple: {event_triple}")

                    # Process event-entity triples
                    event_entity_triples = []
                    for event_entity_participations in event_entity_relation_dict:
                        if "Event" not in event_entity_participations or "Entity" not in event_entity_participations:
                            continue
                        if not isinstance(event_entity_participations["Event"], str) or not isinstance(event_entity_participations["Entity"], list):
                            continue

                        for entity in event_entity_participations["Entity"]:
                            if not isinstance(entity, str):
                                continue

                            entity = clean_text(entity)
                            event = clean_text(event_entity_participations["Event"])

                            if event.isspace() or len(event) == 0 or entity.isspace() or len(entity) == 0:
                                continue

                            event_entity_triples.append((event, "is participated by", entity))

                    # Write nodes and edges to CSV files
                    for entity_triple in entity_triples:
                        head_entity, relation, tail_entity = entity_triple
                        if head_entity is None or tail_entity is None or relation is None:
                            continue
                        if head_entity.isspace() or tail_entity.isspace() or relation.isspace():
                            continue
                        if len(head_entity) == 0 or len(tail_entity) == 0 or len(relation) == 0:
                            continue

                        # Add nodes to files
                        if head_entity not in visited_nodes:
                            visited_nodes.add(head_entity)
                            all_entities.add(head_entity)
                            writer_node.writerow([head_entity, "entity", [], [], "Node"])
                            csv_writer_edge_text.writerow([head_entity, text_hash_id, "Source"])

                        if tail_entity not in visited_nodes:
                            visited_nodes.add(tail_entity)
                            all_entities.add(tail_entity)
                            writer_node.writerow([tail_entity, "entity", [], [], "Node"])
                            csv_writer_edge_text.writerow([tail_entity, text_hash_id, "Source"])

                        all_relations.add(relation)
                        writer_edge.writerow([head_entity, tail_entity, relation, [], [], "Relation"])

                    for event_triple in event_triples:
                        head_event, relation, tail_event = event_triple
                        if head_event is None or tail_event is None or relation is None:
                            continue
                        if head_event.isspace() or tail_event.isspace() or relation.isspace():
                            continue
                        if len(head_event) == 0 or len(tail_event) == 0 or len(relation) == 0:
                            continue

                        # Add nodes to files
                        if head_event not in visited_nodes:
                            visited_nodes.add(head_event)
                            all_events.add(head_event)
                            writer_node.writerow([head_event, "event", [], [], "Node"])
                            csv_writer_edge_text.writerow([head_event, text_hash_id, "Source"])

                        if tail_event not in visited_nodes:
                            visited_nodes.add(tail_event)
                            all_events.add(tail_event)
                            writer_node.writerow([tail_event, "event", [], [], "Node"])
                            csv_writer_edge_text.writerow([tail_event, text_hash_id, "Source"])

                        all_relations.add(relation)
                        writer_edge.writerow([head_event, tail_event, relation, [], [], "Relation"])

                    for event_entity_triple in event_entity_triples:
                        head_event, relation, tail_entity = event_entity_triple
                        if head_event is None or tail_entity is None or relation is None:
                            continue
                        if head_event.isspace() or tail_entity.isspace() or relation.isspace():
                            continue
                        if len(head_event) == 0 or len(tail_entity) == 0 or len(relation) == 0:
                            continue

                        # Add nodes to files
                        if head_event not in visited_nodes:
                            visited_nodes.add(head_event)
                            all_events.add(head_event)
                            writer_node.writerow([head_event, "event", [], [], "Node"])
                            csv_writer_edge_text.writerow([head_event, text_hash_id, "Source"])

                        if tail_entity not in visited_nodes:
                            visited_nodes.add(tail_entity)
                            all_entities.add(tail_entity)
                            writer_node.writerow([tail_entity, "entity", [], [], "Node"])
                            csv_writer_edge_text.writerow([tail_entity, text_hash_id, "Source"])

                        all_relations.add(relation)
                        writer_edge.writerow([head_event, tail_entity, relation, [], [], "Relation"])

                except Exception as e:
                    # 레코드 파싱/처리 중 문제가 생기면 해당 라인을 건너뜁니다
                    print(f"Error processing line: {e}")
                    continue

    # Write missing concepts to CSV
    with open(missing_concepts_file, "w", newline='', encoding='utf-8', errors='ignore') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Name", "Type"])
        for entity in all_entities:
            writer.writerow([entity, "Entity"])
        for event in all_events:
            writer.writerow([event, "Event"])
        for relation in all_relations:
            writer.writerow([relation, "Relation"])

    print("Data to CSV completed successfully.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str, required=True, help="[pes2o_abstract, en_simple_wiki_v0, cc_en]")
    parser.add_argument("--data_dir", type=str, required=True, help="Directory containing the graph raw JSON files")
    parser.add_argument("--output_dir", type=str, required=True, help="Directory to save the output CSV files")
    parser.add_argument("--test", action="store_true", help="Test the script")
    args = parser.parse_args()
    json2csv(dataset=args.dataset, data_dir=args.data_dir, output_dir=args.output_dir, test=args.test)