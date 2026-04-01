"""
eClerx KYC Chatbot — RAGAS Evaluation Pipeline
================================================
Evaluates the RAG chatbot against a golden dataset using RAGAS metrics.

Metrics:
  - Faithfulness         : Answer grounded in retrieved context (anti-hallucination)
  - Answer Relevancy     : How well the answer addresses the question
  - Context Precision    : Retrieved context relevance precision
  - Context Recall       : How well context covers the ground truth
  - Answer Correctness   : Semantic similarity to ground truth

Usage:
  pip install -r requirements-eval.txt
  python evaluate.py --api-key YOUR_OPENAI_KEY --url http://localhost:8000
  python evaluate.py --api-key YOUR_OPENAI_KEY --url https://kyc-chatbot-api.onrender.com
  python evaluate.py --subset simple            # Run only simple queries
  python evaluate.py --subset tricky            # Run only tricky queries
  python evaluate.py --subset all               # Run all 30 queries (default)
"""

import argparse
import json
import os
import sys
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# ── Optional: load from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / "backend" / ".env")
except ImportError:
    pass


# ═══════════════════════════════════════════════════════
# 1. ARGUMENT PARSING
# ═══════════════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser(description="RAGAS evaluation for eClerx KYC Chatbot")
    parser.add_argument("--api-key",  default=os.getenv("OPENAI_API_KEY", ""),
                        help="OpenAI API key")
    parser.add_argument("--url",      default="http://localhost:8000",
                        help="Backend base URL (no trailing slash)")
    parser.add_argument("--subset",   default="all",
                        choices=["all", "simple", "complex", "tricky", "adversarial", "multi_hop"],
                        help="Which category of questions to evaluate")
    parser.add_argument("--max",      type=int, default=None,
                        help="Max number of questions to evaluate (for quick testing)")
    parser.add_argument("--output",   default="eval_results.json",
                        help="Output file for detailed results")
    parser.add_argument("--session",  default="eval_session",
                        help="Session ID to use for all evaluation queries")
    return parser.parse_args()


# ═══════════════════════════════════════════════════════
# 2. QUERY THE CHATBOT
# ═══════════════════════════════════════════════════════

def query_chatbot(base_url: str, question: str, session_id: str) -> Dict[str, Any]:
    """Send a question to the chatbot and return the full response."""
    url = f"{base_url.rstrip('/')}/api/v1/chat"
    payload = {"query": question, "session_id": session_id}
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return {
            "answer": data.get("answer", ""),
            "sources": data.get("sources", []),
            "contexts": [s.get("content", "") for s in data.get("sources", [])],
            "error": None,
        }
    except requests.exceptions.Timeout:
        return {"answer": "", "sources": [], "contexts": [], "error": "timeout"}
    except Exception as e:
        return {"answer": "", "sources": [], "contexts": [], "error": str(e)}


# ═══════════════════════════════════════════════════════
# 3. RAGAS METRICS
# ═══════════════════════════════════════════════════════

def compute_ragas_metrics(
    questions: List[str],
    answers: List[str],
    contexts: List[List[str]],
    ground_truths: List[str],
    api_key: str,
) -> Dict[str, float]:
    """
    Run RAGAS evaluation on a batch of Q&A pairs.
    Returns a dict of metric_name -> score (0.0 to 1.0).
    """
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
            answer_correctness,
        )
        import openai

        os.environ["OPENAI_API_KEY"] = api_key

        data = {
            "question":    questions,
            "answer":      answers,
            "contexts":    contexts,
            "ground_truth": ground_truths,
        }
        dataset = Dataset.from_dict(data)

        metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
            answer_correctness,
        ]

        print("\n⏳ Running RAGAS evaluation (this may take a few minutes)...")
        result = evaluate(dataset, metrics=metrics)
        return dict(result)

    except ImportError as e:
        print(f"\n⚠️  RAGAS not installed: {e}")
        print("   Run: pip install ragas datasets")
        print("   Falling back to manual scoring...\n")
        return {}
    except Exception as e:
        print(f"\n❌ RAGAS evaluation failed: {e}")
        return {}


# ═══════════════════════════════════════════════════════
# 4. MANUAL SCORING (fallback when RAGAS unavailable)
# ═══════════════════════════════════════════════════════

def score_answer_manually(answer: str, ground_truth: str, context_keywords: List[str]) -> Dict[str, float]:
    """
    Simple heuristic scoring when RAGAS is not available.
    Uses keyword overlap and answer length heuristics.
    """
    if not answer:
        return {
            "keyword_coverage":   0.0,
            "answer_length_ok":   0.0,
            "not_empty":          0.0,
            "no_hallucination_flag": 1.0,
        }

    answer_lower = answer.lower()
    gt_lower = ground_truth.lower()

    # Keyword coverage
    if context_keywords:
        hits = sum(1 for kw in context_keywords if kw.lower() in answer_lower)
        keyword_score = hits / len(context_keywords)
    else:
        keyword_score = 0.5  # neutral if no keywords defined

    # Ground truth word overlap (simple Jaccard)
    gt_words = set(gt_lower.split())
    ans_words = set(answer_lower.split())
    if gt_words:
        overlap = len(gt_words & ans_words) / len(gt_words | ans_words)
    else:
        overlap = 0.0

    # Basic checks
    not_empty = 1.0 if len(answer) > 20 else 0.0
    reasonable_length = 1.0 if 30 < len(answer) < 3000 else 0.5

    # Hallucination flag: check if "I don't know" / "not in the document" is used
    # appropriately for adversarial questions
    hallucination_phrases = [
        "i cannot", "i can't", "not in the document", "not covered", "not found",
        "i don't have", "no information", "cannot provide"
    ]
    uses_fallback = any(p in answer_lower for p in hallucination_phrases)

    return {
        "keyword_coverage":   round(keyword_score, 3),
        "word_overlap":       round(overlap, 3),
        "answer_not_empty":   not_empty,
        "length_reasonable":  reasonable_length,
        "uses_fallback":      1.0 if uses_fallback else 0.0,
    }


# ═══════════════════════════════════════════════════════
# 5. MAIN EVALUATION LOOP
# ═══════════════════════════════════════════════════════

def run_evaluation(args):
    print("=" * 65)
    print("   eClerx KYC Chatbot — RAGAS Evaluation Pipeline")
    print("=" * 65)
    print(f"  Backend URL : {args.url}")
    print(f"  Subset      : {args.subset}")
    print(f"  Session     : {args.session}")
    print(f"  Output file : {args.output}")
    print("=" * 65)

    # Load golden dataset
    dataset_path = Path(__file__).parent / "golden_dataset.json"
    if not dataset_path.exists():
        print(f"❌ Golden dataset not found: {dataset_path}")
        sys.exit(1)

    with open(dataset_path) as f:
        golden = json.load(f)

    # Filter by subset
    if args.subset != "all":
        golden = [q for q in golden if q.get("category") == args.subset]

    if args.max:
        golden = golden[:args.max]

    if not golden:
        print("❌ No questions matched the filter. Check --subset value.")
        sys.exit(1)

    print(f"\n📋 Evaluating {len(golden)} questions...\n")

    # ── Step 1: Collect answers from chatbot
    results = []
    questions_list   = []
    answers_list     = []
    contexts_list    = []
    ground_truth_list = []

    for i, item in enumerate(golden):
        qid       = item["id"]
        question  = item["question"]
        gt        = item["ground_truth"]
        keywords  = item.get("context_keywords", [])
        category  = item.get("category", "unknown")
        difficulty= item.get("difficulty", "unknown")

        print(f"  [{i+1:02d}/{len(golden)}] {qid} ({category}/{difficulty})")
        print(f"         Q: {question[:75]}{'...' if len(question) > 75 else ''}")

        # Query chatbot
        start = time.time()
        response = query_chatbot(args.url, question, args.session)
        elapsed = round(time.time() - start, 2)

        if response["error"]:
            print(f"         ⚠️  Error: {response['error']}")
            answer   = ""
            contexts = []
        else:
            answer   = response["answer"]
            contexts = response["contexts"]
            print(f"         A: {answer[:75]}{'...' if len(answer) > 75 else ''}")

        print(f"         ⏱  {elapsed}s | {len(contexts)} source(s) retrieved\n")

        # Manual scoring
        manual_scores = score_answer_manually(answer, gt, keywords)

        results.append({
            "id":           qid,
            "category":     category,
            "difficulty":   difficulty,
            "question":     question,
            "ground_truth": gt,
            "answer":       answer,
            "contexts":     contexts,
            "latency_s":    elapsed,
            "error":        response["error"],
            "manual_scores": manual_scores,
        })

        questions_list.append(question)
        answers_list.append(answer if answer else "No answer generated.")
        contexts_list.append(contexts if contexts else ["No context retrieved."])
        ground_truth_list.append(gt)

        # Small delay to avoid rate limits
        time.sleep(0.5)

    # ── Step 2: Run RAGAS if API key provided
    ragas_scores = {}
    if args.api_key:
        ragas_scores = compute_ragas_metrics(
            questions_list,
            answers_list,
            contexts_list,
            ground_truth_list,
            args.api_key,
        )
    else:
        print("⚠️  No API key provided — skipping RAGAS metrics. Use --api-key.")

    # ── Step 3: Compute summary statistics
    error_count   = sum(1 for r in results if r["error"])
    empty_count   = sum(1 for r in results if not r["answer"])
    avg_latency   = round(sum(r["latency_s"] for r in results) / len(results), 2)
    avg_kw_cov    = round(sum(r["manual_scores"].get("keyword_coverage", 0) for r in results) / len(results), 3)
    avg_overlap   = round(sum(r["manual_scores"].get("word_overlap", 0) for r in results) / len(results), 3)

    # Per-category breakdown
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"count": 0, "kw_sum": 0.0, "overlap_sum": 0.0, "errors": 0}
        categories[cat]["count"]      += 1
        categories[cat]["kw_sum"]     += r["manual_scores"].get("keyword_coverage", 0)
        categories[cat]["overlap_sum"]+= r["manual_scores"].get("word_overlap", 0)
        if r["error"]:
            categories[cat]["errors"] += 1

    cat_summary = {}
    for cat, stats in categories.items():
        n = stats["count"]
        cat_summary[cat] = {
            "count":            n,
            "avg_kw_coverage":  round(stats["kw_sum"] / n, 3),
            "avg_word_overlap": round(stats["overlap_sum"] / n, 3),
            "error_rate":       round(stats["errors"] / n, 3),
        }

    # ── Step 4: Print results
    print("\n" + "=" * 65)
    print("   EVALUATION SUMMARY")
    print("=" * 65)
    print(f"  Total questions evaluated : {len(results)}")
    print(f"  Errors (API/timeout)      : {error_count}")
    print(f"  Empty answers             : {empty_count}")
    print(f"  Average latency           : {avg_latency}s")
    print(f"  Avg keyword coverage      : {avg_kw_cov:.1%}")
    print(f"  Avg word overlap w/ GT    : {avg_overlap:.1%}")

    if ragas_scores:
        print("\n  ── RAGAS Scores ──")
        ragas_map = {
            "faithfulness":       "Faithfulness      (anti-hallucination)",
            "answer_relevancy":   "Answer Relevancy  (on-topic answers)",
            "context_precision":  "Context Precision (retrieved context quality)",
            "context_recall":     "Context Recall    (coverage of ground truth)",
            "answer_correctness": "Answer Correctness (semantic similarity to GT)",
        }
        for key, label in ragas_map.items():
            score = ragas_scores.get(key, "N/A")
            bar = ""
            if isinstance(score, float):
                filled = int(score * 20)
                bar = " [" + "█" * filled + "░" * (20 - filled) + f"] {score:.3f}"
            print(f"  {label}: {bar}")

    print("\n  ── Per-Category Breakdown ──")
    for cat, stats in cat_summary.items():
        print(f"  {cat:15s}: {stats['count']} questions | "
              f"KW coverage: {stats['avg_kw_coverage']:.1%} | "
              f"Overlap: {stats['avg_word_overlap']:.1%} | "
              f"Errors: {stats['error_rate']:.0%}")

    print("=" * 65)

    # ── Step 5: Save to JSON
    output_path = Path(__file__).parent / args.output
    final_output = {
        "metadata": {
            "eval_date":    datetime.utcnow().isoformat() + "Z",
            "backend_url":  args.url,
            "subset":       args.subset,
            "total_questions": len(results),
        },
        "summary": {
            "total":        len(results),
            "errors":       error_count,
            "empty_answers": empty_count,
            "avg_latency_s": avg_latency,
            "avg_keyword_coverage": avg_kw_cov,
            "avg_word_overlap": avg_overlap,
            "ragas_scores": ragas_scores,
            "by_category":  cat_summary,
        },
        "detailed_results": results,
    }

    with open(output_path, "w", indent=2) as f:
        json.dump(final_output, f, indent=2, default=str)

    print(f"\n✅ Detailed results saved to: {output_path}")
    print(f"\n💡 Tip: Open eval_report.py to generate an HTML report from these results.\n")


# ═══════════════════════════════════════════════════════
# 6. ENTRY POINT
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    args = parse_args()
    run_evaluation(args)
