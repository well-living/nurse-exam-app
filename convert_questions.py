import json

def transform_json(input_filename, output_filename):
    # 元のファイルを読み込む
    with open(input_filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    transformed_data = []
    
    for item in data:
        # 新しい構造に変換
        new_item = {
            "id": f"q{item['id']:03}", # idをq001形式にする
            "year": 2026,              # 年を2026に固定
            "number": item['id'],      # 元のidを問題番号とする
            "category": "必修",        # カテゴリを必修に固定
            "question_text": item['question'],
            "choices": item['options'],
            "correct_answer": item['answer'],
            "explanation": item['explanation']
        }
        transformed_data.append(new_item)
    
    # 変換後のデータを保存する
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(transformed_data, f, ensure_ascii=False, indent=2)

# 実行
transform_json('questions.json', 'questions_transformed.json')