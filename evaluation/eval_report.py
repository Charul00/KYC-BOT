"""
eClerx KYC Chatbot — HTML Evaluation Report Generator
========================================================
Reads eval_results.json and generates a beautiful HTML report.

Usage:
  python eval_report.py
  python eval_report.py --input eval_results.json --output report.html
"""

import json
import argparse
from pathlib import Path
from datetime import datetime


def generate_report(input_path: str, output_path: str):
    with open(input_path) as f:
        data = json.load(f)

    meta    = data.get("metadata", {})
    summary = data.get("summary", {})
    results = data.get("detailed_results", [])
    ragas   = summary.get("ragas_scores", {})
    by_cat  = summary.get("by_category", {})

    def pct(v):
        try: return f"{float(v):.1%}"
        except: return "N/A"

    def score_bar(v, max_val=1.0):
        try:
            ratio = float(v) / max_val
            color = "#22c55e" if ratio >= 0.8 else "#f59e0b" if ratio >= 0.5 else "#ef4444"
            return f'<div style="background:#e2e8f0;border-radius:4px;height:8px;width:100%;"><div style="background:{color};width:{ratio*100:.1f}%;height:8px;border-radius:4px;"></div></div>'
        except:
            return ""

    cat_colors = {
        "simple": "#3b82f6", "complex": "#8b5cf6", "tricky": "#f59e0b",
        "adversarial": "#ef4444", "multi_hop": "#06b6d4"
    }

    rows = ""
    for r in results:
        cat = r.get("category", "")
        color = cat_colors.get(cat, "#64748b")
        diff = r.get("difficulty", "")
        err = r.get("error", "")
        ms = r.get("manual_scores", {})
        kw = ms.get("keyword_coverage", 0)
        ov = ms.get("word_overlap", 0)
        rows += f"""
        <tr>
          <td><code style="color:#2563eb">{r['id']}</code></td>
          <td><span style="background:{color}22;color:{color};padding:2px 8px;border-radius:99px;font-size:11px;font-weight:600;">{cat}</span></td>
          <td><span style="color:#64748b;font-size:12px;">{diff}</span></td>
          <td style="max-width:220px;font-size:12px;color:#374151;">{r['question'][:100]}{'…' if len(r['question'])>100 else ''}</td>
          <td style="max-width:220px;font-size:12px;color:#374151;">{'<span style="color:#ef4444">⚠ ' + err + '</span>' if err else r['answer'][:120] + ('…' if len(r.get('answer',''))>120 else '')}</td>
          <td style="font-size:12px;">{score_bar(kw)}<span style="color:#64748b;font-size:10px;">{pct(kw)}</span></td>
          <td style="font-size:12px;">{score_bar(ov)}<span style="color:#64748b;font-size:10px;">{pct(ov)}</span></td>
          <td style="font-size:12px;color:#64748b;">{r.get('latency_s','?')}s</td>
        </tr>"""

    ragas_html = ""
    if ragas:
        ragas_items = {
            "faithfulness":       "Faithfulness",
            "answer_relevancy":   "Answer Relevancy",
            "context_precision":  "Context Precision",
            "context_recall":     "Context Recall",
            "answer_correctness": "Answer Correctness",
        }
        for key, label in ragas_items.items():
            v = ragas.get(key, None)
            if v is not None:
                ragas_html += f"""
                <div style="margin-bottom:14px;">
                  <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                    <span style="font-size:13px;font-weight:600;color:#374151;">{label}</span>
                    <span style="font-size:13px;font-weight:700;color:#1e293b;">{float(v):.3f}</span>
                  </div>
                  {score_bar(v)}
                </div>"""
    else:
        ragas_html = '<p style="color:#94a3b8;font-size:13px;">RAGAS scores not available. Run with --api-key to enable.</p>'

    cat_cards = ""
    for cat, stats in by_cat.items():
        color = cat_colors.get(cat, "#64748b")
        cat_cards += f"""
        <div style="background:white;border:1px solid #e2e8f0;border-radius:12px;padding:16px;flex:1;min-width:140px;">
          <div style="font-size:11px;font-weight:700;color:{color};text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">{cat}</div>
          <div style="font-size:22px;font-weight:800;color:#1e293b;margin-bottom:4px;">{stats['count']}</div>
          <div style="font-size:11px;color:#64748b;">KW Coverage: <b>{pct(stats['avg_kw_coverage'])}</b></div>
          <div style="font-size:11px;color:#64748b;">Word Overlap: <b>{pct(stats['avg_word_overlap'])}</b></div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>eClerx KYC Chatbot — Evaluation Report</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'Segoe UI',-apple-system,sans-serif; background:#f8fafc; color:#1e293b; padding:32px 24px 64px; }}
  h1 {{ font-size:24px; font-weight:800; color:#1a2744; }}
  h2 {{ font-size:16px; font-weight:700; color:#374151; margin-bottom:16px; }}
  .card {{ background:white; border:1px solid #e2e8f0; border-radius:16px; padding:24px; margin-bottom:24px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ background:#f1f5f9; padding:10px 12px; text-align:left; font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; }}
  td {{ padding:10px 12px; border-bottom:1px solid #f1f5f9; vertical-align:top; }}
  tr:last-child td {{ border-bottom:none; }}
  tr:hover td {{ background:#f8fafc; }}
</style>
</head>
<body>

<div style="max-width:1200px;margin:0 auto;">

  <!-- Header -->
  <div style="margin-bottom:32px;">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
      <div style="background:linear-gradient(135deg,#1a2744,#2563eb);padding:8px 16px;border-radius:8px;">
        <span style="color:white;font-weight:800;font-size:15px;">eClerx</span>
      </div>
      <h1>KYC Chatbot — RAGAS Evaluation Report</h1>
    </div>
    <p style="color:#64748b;font-size:13px;">
      Generated: {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')} &nbsp;·&nbsp;
      Backend: <code style="background:#f1f5f9;padding:2px 6px;border-radius:4px;">{meta.get('backend_url','N/A')}</code> &nbsp;·&nbsp;
      Subset: <b>{meta.get('subset','all')}</b>
    </p>
  </div>

  <!-- KPI Row -->
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:16px;margin-bottom:24px;">
    <div class="card" style="text-align:center;padding:20px;">
      <div style="font-size:32px;font-weight:800;color:#2563eb;">{summary.get('total',0)}</div>
      <div style="font-size:12px;color:#64748b;margin-top:4px;">Total Questions</div>
    </div>
    <div class="card" style="text-align:center;padding:20px;">
      <div style="font-size:32px;font-weight:800;color:#22c55e;">{summary.get('total',0) - summary.get('errors',0)}</div>
      <div style="font-size:12px;color:#64748b;margin-top:4px;">Successful</div>
    </div>
    <div class="card" style="text-align:center;padding:20px;">
      <div style="font-size:32px;font-weight:800;color:#f59e0b;">{summary.get('avg_latency_s','?')}s</div>
      <div style="font-size:12px;color:#64748b;margin-top:4px;">Avg Latency</div>
    </div>
    <div class="card" style="text-align:center;padding:20px;">
      <div style="font-size:32px;font-weight:800;color:#8b5cf6;">{pct(summary.get('avg_keyword_coverage',0))}</div>
      <div style="font-size:12px;color:#64748b;margin-top:4px;">Keyword Coverage</div>
    </div>
    <div class="card" style="text-align:center;padding:20px;">
      <div style="font-size:32px;font-weight:800;color:#06b6d4;">{pct(summary.get('avg_word_overlap',0))}</div>
      <div style="font-size:12px;color:#64748b;margin-top:4px;">Word Overlap w/ GT</div>
    </div>
  </div>

  <!-- RAGAS + Category -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:24px;">
    <div class="card">
      <h2>🎯 RAGAS Scores</h2>
      {ragas_html}
    </div>
    <div class="card">
      <h2>📊 By Category</h2>
      <div style="display:flex;flex-wrap:wrap;gap:12px;">{cat_cards}</div>
    </div>
  </div>

  <!-- Detailed results table -->
  <div class="card">
    <h2>📋 Detailed Results ({len(results)} questions)</h2>
    <div style="overflow-x:auto;">
      <table>
        <thead>
          <tr>
            <th>ID</th><th>Category</th><th>Difficulty</th>
            <th>Question</th><th>Answer</th>
            <th>KW Coverage</th><th>GT Overlap</th><th>Latency</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </div>

  <p style="text-align:center;color:#94a3b8;font-size:12px;margin-top:32px;">
    eClerx KYC Chatbot Evaluation · Powered by RAGAS · {datetime.utcnow().year}
  </p>
</div>
</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html)
    print(f"✅ Report generated: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  default="eval_results.json")
    parser.add_argument("--output", default="eval_report.html")
    args = parser.parse_args()

    input_path = Path(__file__).parent / args.input
    output_path = Path(__file__).parent / args.output

    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        print("   Run evaluate.py first to generate results.")
        raise SystemExit(1)

    generate_report(str(input_path), str(output_path))
