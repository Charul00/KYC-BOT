# Microsoft 2024 Annual Report — Chatbot Test Questions

Upload `2024_Annual_Report.docx` to the chatbot, then ask these questions one by one.
Each question tests a different capability of the RAG pipeline.

---

## CATEGORY 1 — Simple Factual Retrieval
*Tests: basic chunk retrieval, exact answer extraction*

**Q1.** What was Microsoft's total annual revenue in fiscal year 2024?
> ✅ Expected: $245,122 million / over $245 billion (16% growth YoY)

**Q2.** When was Microsoft founded?
> ✅ Expected: 1975

**Q3.** What stock exchange is Microsoft listed on, and what is its ticker symbol?
> ✅ Expected: NASDAQ, symbol MSFT

**Q4.** How many full-time employees did Microsoft have as of June 30, 2024?
> ✅ Expected: Approximately 228,000

**Q5.** When did Microsoft's acquisition of Activision Blizzard King close?
> ✅ Expected: October 2023

---

## CATEGORY 2 — Exact Financial Numbers
*Tests: structured data extraction, table reading, numeric precision*

**Q6.** What was Microsoft's net income in fiscal year 2024?
> ✅ Expected: $88,136 million / ~$88.1 billion (22% growth)

**Q7.** What was the diluted earnings per share (EPS) for fiscal year 2024?
> ✅ Expected: $11.80 (vs $9.68 in FY2023, 22% growth)

**Q8.** What was Microsoft's operating income in FY2024 and by what percentage did it grow?
> ✅ Expected: $109,433 million, grew 24% year-over-year

**Q9.** What was the total cash, cash equivalents, and short-term investments as of June 30, 2024?
> ✅ Expected: $75.5 billion / $75,543 million

**Q10.** What was Microsoft's gross margin in FY2024?
> ✅ Expected: $171,008 million (17% growth)

---

## CATEGORY 3 — Year-over-Year Comparison
*Tests: multi-fact retrieval, comparison reasoning*

**Q11.** How did Microsoft's revenue change from FY2023 to FY2024? Give both the dollar amounts and the growth rate.
> ✅ Expected: From $211,915M to $245,122M — 16% growth

**Q12.** Compare net income between FY2023 and FY2024.
> ✅ Expected: $72,361M (FY2023) → $88,136M (FY2024), up 22%

**Q13.** Did Microsoft's cash position increase or decrease from 2023 to 2024? By how much?
> ✅ Expected: Decreased — from $111.3B to $75.5B (dropped ~$35.8B)

**Q14.** How did diluted EPS change between FY2023 and FY2024?
> ✅ Expected: $9.68 → $11.80, an increase of 22%

---

## CATEGORY 4 — Operational / Segment Data
*Tests: multi-section retrieval, segment understanding*

**Q15.** What are Microsoft's three operating segments?
> ✅ Expected: Productivity and Business Processes, Intelligent Cloud, More Personal Computing

**Q16.** How many Microsoft employees are based in the United States vs internationally?
> ✅ Expected: 126,000 in the US, 102,000 internationally

**Q17.** Break down Microsoft's total employees by function/department.
> ✅ Expected: 86,000 operations, 81,000 product R&D, 45,000 sales & marketing, 16,000 general & admin

**Q18.** What products are included in Microsoft's Intelligent Cloud segment?
> ✅ Expected: Azure, SQL Server, Windows Server, Visual Studio, GitHub, Nuance, Enterprise Support Services, etc.

**Q19.** What does the More Personal Computing segment include?
> ✅ Expected: Windows, Devices (Surface, HoloLens), Gaming (Xbox, Activision Blizzard), Search & news advertising (Bing, Copilot, Edge)

---

## CATEGORY 5 — Strategic / Qualitative
*Tests: long-form summarization, concept extraction*

**Q20.** What is the Secure Future Initiative (SFI) and why did Microsoft launch it?
> ✅ Expected: A cybersecurity initiative launched in FY2024 bringing together every part of Microsoft's organization to advance cybersecurity protection; security was the top priority.

**Q21.** What are Microsoft's three stated priorities going forward as mentioned in the CEO letter?
> ✅ Expected: 1) Prioritizing fundamentals with security above all else, 2) Driving trustworthy AI innovation while scaling cloud, 3) Managing cost structure dynamically for long-term operating leverage

**Q22.** How is Microsoft using AI to help customers across different industries? Give at least three examples from the annual report.
> ✅ Expected: Any 3 from — Coles (1.6B daily AI predictions), Unilever (AI simulations for product development), Itaú (GitHub Copilot for coding), Khan Academy (tutoring/lesson planning), Indonesia aquafarmers (Azure ML for yield improvement), M-Kopa Kenya (credit access via Azure ML)

**Q23.** What is Microsoft's mission statement?
> ✅ Expected: "To empower every person and every organization on the planet to achieve more"

---

## CATEGORY 6 — Gaming / Acquisitions
*Tests: specific domain retrieval*

**Q24.** How many gaming franchises does Microsoft have that have generated over $1 billion in lifetime revenue?
> ✅ Expected: 20 franchises (including Candy Crush, Diablo, Halo, Warcraft, Elder Scrolls, Gears of War)

**Q25.** What happened with Microsoft's share repurchase program?
> ✅ Expected: Board approved a $60 billion share repurchase program (after completing the prior $40B program approved Sept 2019)

**Q26.** How many registered holders of Microsoft common stock were there on July 25, 2024?
> ✅ Expected: 81,346 registered holders of record

---

## CATEGORY 7 — Multi-Hop Reasoning
*Tests: connecting facts across multiple chunks*

**Q27.** Microsoft's operating income grew by 24% in FY2024. What was the actual dollar increase compared to FY2023?
> ✅ Expected: $109,433M - $88,523M = ~$20.9 billion increase

**Q28.** If Microsoft had approximately 228,000 employees and revenue of $245 billion, what was the approximate revenue per employee?
> ✅ Expected: ~$1.07 million per employee (tests math + multi-fact retrieval)

**Q29.** The report mentions the Activision Blizzard King acquisition drove R&D expense growth. By how much did R&D expenses increase, and what portion was from Activision?
> ✅ Expected: R&D increased $2.3 billion or 9%; Activision drove 7 percentage points of that growth

---

## CATEGORY 8 — Edge Cases (Hallucination Check)
*Tests: bot should say "not found" / "not mentioned" — NOT make up answers*

**Q30.** What was Microsoft's stock price on June 30, 2024?
> ✅ Expected: The document does NOT contain the stock price. Bot should say this info is not in the document.

**Q31.** Who is Microsoft's Chief Financial Officer?
> ✅ Expected: Not explicitly mentioned in the annual report content provided. Bot should not hallucinate a name.

**Q32.** What is Microsoft's revenue forecast for fiscal year 2025?
> ✅ Expected: Not in the document. Bot should not make up projections.

**Q33.** How many data centers does Microsoft operate globally?
> ✅ Expected: Exact number not stated in this document. Bot should acknowledge this.

---

## CATEGORY 9 — Conversational Memory
*Tests: multi-turn conversation, context retention — ask these in sequence*

**Q34a.** What was Microsoft's revenue in FY2024?
> ✅ Expected: $245 billion

**Q34b.** *(follow-up, same session)* How does that compare to the previous year?
> ✅ Expected: Bot should remember FY2024 revenue and compare to FY2023 ($211.9B), 16% growth — without you repeating the year

**Q34c.** *(follow-up)* Which segment contributed most to this growth?
> ✅ Expected: Bot should continue the revenue conversation and talk about Intelligent Cloud / Azure growth

---

## CATEGORY 10 — Tone & Format Quality
*Tests: response formatting, conciseness, no hallucination padding*

**Q35.** Give me a one-paragraph executive summary of Microsoft's FY2024 financial performance.
> ✅ Expected: Concise, factual paragraph covering revenue ($245B, +16%), operating income ($109B, +24%), net income ($88B, +22%), EPS ($11.80, +22%) — no made-up numbers.

**Q36.** List the key financial metrics for FY2024 in a table format.
> ✅ Expected: A clean table with Revenue, Gross Margin, Operating Income, Net Income, EPS and their FY2024 values, FY2023 values, and % change.

**Q37.** What risks does Microsoft face in its Windows business?
> ✅ Expected: Mix of devices, market demand between developed/growth markets, AI PC growth, pricing changes, piracy, supply chain constraints — all from the document.

---

## Quick Scoring Guide

| Score | What it means |
|---|---|
| Answers Q1-Q14 correctly | Basic retrieval working ✅ |
| Answers Q15-Q26 correctly | Segment + operational data retrieval working ✅ |
| Answers Q27-Q29 correctly | Multi-hop reasoning working ✅ |
| Says "not in document" for Q30-Q33 | No hallucination ✅ |
| Q34a-c maintains context | Memory working ✅ |
| Q35-Q37 formatted cleanly | Output quality good ✅ |

**If the bot hallucinates on Q30-Q33 — that's the most critical issue to fix.**
