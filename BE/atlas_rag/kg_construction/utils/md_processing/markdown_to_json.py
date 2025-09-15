import argparse
import json
import os
import sys
from pathlib import Path

# Set up argument parser
parser = argparse.ArgumentParser(description="Convert all Markdown files in a folder to separate JSON files.")
parser.add_argument(
    "--input", required=True, help="Path to the folder containing Markdown files"
)
parser.add_argument(
    "--output", default=None, help="Output folder for JSON files (defaults to input folder if not specified)"
)

# Parse arguments
args = parser.parse_args()

# Resolve input folder path
input_folder = Path(args.input)
if not input_folder.is_dir():
    print(f"Error: '{args.input}' is not a directory.", file=sys.stderr)
    sys.exit(1)

# Set output folder (use input folder if not specified)
output_folder = Path(args.output) if args.output else input_folder
output_folder.mkdir(parents=True, exist_ok=True)

# Find all .md files in the input folder
markdown_files = [f for f in input_folder.iterdir() if f.suffix.lower() == ".md"]

if not markdown_files:
    print(f"Error: No Markdown files found in '{args.input}'.", file=sys.stderr)
    sys.exit(1)

def parse_markdown_sections(content):
    """
    마크다운 내용을 조항별로 파싱하여 각 조항에 고유 ID 부여
    """
    clauses = []
    current_clause = None
    clause_id = 1
    
    # 줄별로 처리
    lines = content.split('\n')
    
    for line_num, line in enumerate(lines):
        line = line.strip()
        
        # 제목 레벨 확인 (H1, H2, H3 등)
        if line.startswith('#'):
            # 이전 조항이 있으면 저장
            if current_clause:
                clauses.append(current_clause)
            
            # 새 조항 시작
            current_clause = {
                "id": str(clause_id),
                "text": line + "\n",  # 제목 포함
                "metadata": {
                    "lang": "ko"
                }
            }
            clause_id += 1
            
        else:
            # 내용 추가
            if current_clause:
                current_clause["text"] += line + "\n"
    
    # 마지막 조항 추가
    if current_clause:
        clauses.append(current_clause)
    
    return clauses

# Process each Markdown file
for file in markdown_files:
    try:
        # Read the content of the file
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()

        # 마크다운을 조항별로 파싱하여 각 조항에 고유 ID 부여
        clauses = parse_markdown_sections(content)

        # Create output JSON filename (e.g., file1.md -> file1.json)
        output_file = output_folder / f"{file.stem}.json"

        # Write JSON to file (원래 형식 유지)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(clauses, f, indent=4, ensure_ascii=False)

        print(f"Successfully converted '{file}' to '{output_file}'")
        print(f"  - Total clauses: {len(clauses)}")
    except FileNotFoundError:
        print(f"Error: File '{file}' not found.", file=sys.stderr)
    except Exception as e:
        print(f"Error processing file '{file}': {e}", file=sys.stderr)