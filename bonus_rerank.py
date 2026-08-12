import json
import re
from template import RAGASEvaluator

def _tokenize(text: str) -> set[str]:
    return set(re.findall(r'\b\w+\b', text.lower()))

def rerank_by_overlap(query: str, chunks: list[dict]) -> list[dict]:
    query_tokens = _tokenize(query)
    def overlap_score(chunk):
        chunk_tokens = _tokenize(chunk.get("text", ""))
        return len(query_tokens & chunk_tokens)
    
    # Sort chunks by overlap score descending
    return sorted(chunks, key=overlap_score, reverse=True)

def main():
    with open('golden_dataset.json', 'r', encoding='utf-8') as f:
        gold_data = json.load(f)
    
    # Map question ID to its expected answer
    gold_map = {item['id']: item['expected_answer'] for item in gold_data['qa_pairs']}

    with open('artifacts/actual_answers.json', 'r', encoding='utf-8') as f:
        actual_data = json.load(f)
    
    evaluator = RAGASEvaluator()
    print(f"| {'ID':<3} | {'Recall before':<13} | {'Recall after':<12} | {'Precision before':<16} | {'Precision after':<15} | {'Delta Precision':<15} |")
    print(f"|-----|---------------|--------------|------------------|-----------------|-----------------|")
    
    # Pick 5 difficult cases to observe precision changes
    target_ids = ['H01', 'H02', 'H04', 'H05', 'M01']
    
    avg_rec_before = 0
    avg_rec_after = 0
    avg_prec_before = 0
    avg_prec_after = 0
    count = 0

    for item in actual_data['answers']:
        if item['id'] not in target_ids:
            continue
            
        q_id = item['id']
        question = item['question']
        contexts = [c['text'] for c in item['retrieved_contexts']]
        gold_contexts = gold_map[q_id]
        
        # Before reranking
        rec_before = evaluator.evaluate_context_recall(contexts, gold_contexts)
        prec_before = evaluator.evaluate_context_precision(contexts, gold_contexts)
        
        # Rerank
        reranked_chunks = rerank_by_overlap(question, item['retrieved_contexts'])
        reranked_contexts = [c['text'] for c in reranked_chunks]
        
        # After reranking
        rec_after = evaluator.evaluate_context_recall(reranked_contexts, gold_contexts)
        prec_after = evaluator.evaluate_context_precision(reranked_contexts, gold_contexts)
        
        delta = prec_after - prec_before
        
        print(f"| {q_id:<3} | {rec_before:>13.3f} | {rec_after:>12.3f} | {prec_before:>16.3f} | {prec_after:>15.3f} | {delta:>15.3f} |")
        
        avg_rec_before += rec_before
        avg_rec_after += rec_after
        avg_prec_before += prec_before
        avg_prec_after += prec_after
        count += 1
        
    print(f"| **Avg** | {avg_rec_before/count:>13.3f} | {avg_rec_after/count:>12.3f} | {avg_prec_before/count:>16.3f} | {avg_prec_after/count:>15.3f} | {(avg_prec_after - avg_prec_before)/count:>15.3f} |")

if __name__ == '__main__':
    main()
