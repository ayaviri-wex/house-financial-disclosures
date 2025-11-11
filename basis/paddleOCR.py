import json
import sys
from pathlib import Path
import numpy as np
from paddleocr import PaddleOCR
import re
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline

def convert_float32(obj):
    if isinstance(obj, np.float32):
        return float(obj)
    elif isinstance(obj, list):
        return [convert_float32(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_float32(v) for k, v in obj.items()}
    return obj

def get_input_filepath(filename):
    input_path = Path(filename)

    # Check that the input exists
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    return input_path

def check_paddle_output_exists(input_path):
    output_dir = Path("paddle_output") / input_path.stem
    return output_dir.exists()

def get_paddle_output_from_file(input_path):
    output_dir = Path("paddle_output") / input_path.stem
    json_file = output_dir / (input_path.stem + "_0_res.json")
    with json_file.open("r", encoding="utf-8") as f:
        ocr_results = json.load(f)
    return ocr_results

def run_paddle_ocr(input_path):
    # Initialize PaddleOCR
    ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False
    )

    # Run OCR
    print(f"Running OCR on {input_path} ...")
    results = ocr.predict(str(input_path))

    # Save results
    output_dir = Path("paddle_output") / input_path.stem
    for res in results:
        res.print()
        res.save_to_img(str(output_dir))
        res.save_to_json(str(output_dir))
    
    return results[0]._to_json()['res'] # TODO: implement for multiple pages

def preprocess_for_ner(ocr_results):
    texts, scores = ocr_results["rec_texts"], ocr_results["rec_scores"]

    # convert caps to title case and filter by score
    regex_converter = lambda text: re.sub('[A-Z]+', lambda x: x.group(0).title(), text)
    threshold = 0.9
    texts = [regex_converter(texts[i]) for i in range(len(texts)) if scores[i] >= threshold]

    return ' '.join(texts)

def run_ner(texts):
    model = "dslim/bert-large-NER"

    tokenizer = AutoTokenizer.from_pretrained(model)
    model = AutoModelForTokenClassification.from_pretrained(model)

    nlp = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple")

    results = nlp(texts)
    return convert_float32(results)

def post_process_ner(ner_input, ner_results):
    # Filter out unwanted entity groups:
    prefixes = {"ORG": "org", "PER": "person" , "LOC": "addr"}
    ner_results = [item for item in ner_results if item["entity_group"] in prefixes]

    # Filter out low confidence results
    confidence_threshold = 0.75
    ner_results = [item for item in ner_results if item["score"] >= confidence_threshold]

    # reorganize into sets by entity group to get rid of duplicates
    results = {}
    for item in ner_results:
        group = item["entity_group"]
        if group not in results:
            results[group] = {}

        if item["word"] not in results[group]:
            results[group][item["word"]] = {
                "id": prefixes[group] + '_' + item["word"].replace(" ", "_").lower(),
                "label": item["word"],
                "score": item["score"],
                "source": "ner"
            }
        else:
            # keep the highest score
            results[group][item["word"]]["score"] = max(results[group][item["word"]]["score"], item["score"])

    # Rename keys
    results["organizations"] = results.pop("ORG", {})
    results["persons"] = results.pop("PER", {})
    results["addresses"] = results.pop("LOC", {})

    return results

def main():
    print("Starting ingestion process...")
    if len(sys.argv) != 2:
        print("Usage: python ingestion.py <image_filepath>")
        sys.exit(1)
    filename = sys.argv[1]

    input_path = get_input_filepath(filename)
    
    if check_paddle_output_exists(input_path):
        ocr_results = get_paddle_output_from_file(input_path)
    else:
        print("Paddle OCR output not found for this file. END LOOP")
        sys.exit(1) # don't bother
        ocr_results = run_paddle_ocr(input_path)

    ner_input = preprocess_for_ner(ocr_results)

    ner_results = run_ner(ner_input)

    results = post_process_ner(ner_input, ner_results)

    output_path = Path("ner_output") / (input_path.stem + ".json")
    with open(output_path, 'w') as f:
        json.dump(results, f)

    print("Successfully generated NER output for this file.")

if __name__ == "__main__":
    main()
