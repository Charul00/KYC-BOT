# Goldman Sachs Annual Report 2025 — 20 Chatbot Test Questions
**Document:** annual-report.pdf (Goldman Sachs Annual Report 2025, 274 pages)
**Purpose:** Verify chatbot accuracy across text, financial tables, bar charts, leadership images, strategy sections, and multi-turn memory

Upload `annual-report.pdf` first and wait for "ready" status before running any question.

---

## 🟩 CATEGORY 1 — Direct Financial Metrics (Text Extraction)
*Tests: Can the bot find exact numbers stated in the shareholder letter?*

**Q1**
> What were Goldman Sachs's firmwide net revenues in 2025?

✅ Expected: **$58.3 billion** (net revenues increased 9% year over year)

---

**Q2**
> By how much did earnings per share grow in 2025 and what did it reach?

✅ Expected: EPS grew **27 percent** to **$51.32**

---

**Q3**
> What was Goldman Sachs's return on equity in 2025 and how much did it improve?

✅ Expected: ROE was **15.0 percent**, improved by **230 basis points**

---

**Q4**
> What was the total shareholder return since 2019?

✅ Expected: **+341 percent** (more than the peer group over that period)

---

## 🟦 CATEGORY 2 — Table Reading
*Tests: Can the bot read structured tables accurately?*

**Q5**
> What are the updated medium-term AWM targets for pre-tax margin and returns?

✅ Expected: Pre-Tax Margin updated to **~30%** (from Mid-Twenties). Returns updated to **High Teens** (from Mid-Teens)

---

**Q6**
> What are the 6 initial workstreams of One Goldman Sachs 3.0?

✅ Expected: **Client Onboarding/KYC, Vendor Management, Regulatory Reporting, Lending, Enterprise Risk Management, Sales Enablement**

---

**Q7**
> What are the 6 goals of One Goldman Sachs 3.0?

✅ Expected: Strengthening resilience & capacity to scale, Driving productivity and efficiency, Improving profitability, Enhancing the client experience, Elevating the employee experience, Bolstering risk management

---

**Q8**
> What was Goldman Sachs's book value per share in 2019 versus 2025?

✅ Expected: **$218.52** in 2019 → **$357.60** in 2025

---

## 🟧 CATEGORY 3 — Chart & Graph Reading
*Tests: Can the bot describe or answer questions about bar charts on pages 3 and 5?*

**Q9**
> What does the Firmwide Net Revenues chart show about growth from 2019 to 2025?

✅ Expected: Net revenues grew from **$36.55 billion in 2019** to **$58.28 billion in 2025** (chart also shows a ~$60.54B level before Apple Card transition adjustment of approximately -$2.26B)

---

**Q10**
> What was the FICC and Equities financing net revenues in 2025 and at what CAGR did they grow?

✅ Expected: Reached **$11.45 billion** in 2025. Grew at a **17% CAGR** since 2021. Represented **37%** of total FICC and Equities net revenues in 2025

---

**Q11**
> What does the More Durable Revenues Across AWM chart show between 2021 and 2025?

✅ Expected: AWM more durable revenues grew from **$9.40 billion (2021)** to **$14.89 billion (2025)** at a **12% CAGR**, split between Private banking and lending (dark) and Management and other fees (light)

---

## 🟥 CATEGORY 4 — Image & Leadership Recognition
*Tests: Can the bot identify people and visual content from image-heavy pages?*

**Q12**
> Who are the three executives shown in the photo in the annual report and what are their roles?

✅ Expected: **Denis Coleman** (Chief Financial Officer), **David Solomon** (Chairman and Chief Executive Officer), **John Waldron** (President and Chief Operating Officer)

---

**Q13**
> Who signed the Letter to Shareholders?

✅ Expected: **David Solomon**, Chairman and Chief Executive Officer

---

## 🟪 CATEGORY 5 — Strategy & Business Segment Questions
*Tests: Multi-paragraph reasoning across strategy sections*

**Q14**
> What is Goldman Sachs's target for fee-paying alternative assets under supervision by 2030?

✅ Expected: **$750 billion**

---

**Q15**
> How much did Goldman Sachs raise in alternatives in 2025 and how much has it raised in total since Investor Day 2020?

✅ Expected: Raised a record **$115 billion** in 2025. Total since Investor Day 2020: **$438 billion** in gross third-party fundraising

---

**Q16**
> What strategic partnerships and acquisitions did Goldman Sachs announce around 2025-2026?

✅ Expected: Three actions — (1) **T. Rowe Price** strategic partnership for retirement/wealth solutions, (2) Acquired **XIG (External Investing Group)** with $500B AUS — a secondaries market leader, (3) Announced acquisition of **Innovator Capital Management** to become a top 10 active ETF provider globally

---

**Q17**
> What is Goldman Sachs's ranking in M&A investment banking and for how many consecutive years?

✅ Expected: **#1 M&A advisor for 23 consecutive years**. In 2025 alone advised on over **$1.6 trillion** of announced M&A transaction volumes, more than $250 billion ahead of the closest peer

---

## 🔵 CATEGORY 6 — People, Culture & Hiring
*Tests: Factual extraction from narrative text sections*

**Q18**
> How many experienced hire applicants did Goldman Sachs receive in 2025 and what was the summer internship selection rate?

✅ Expected: Over **1.1 million** experienced hire applicants (a **33% increase** from prior year). Summer internship selection rate: **less than 1 percent**

---

## 🟤 CATEGORY 7 — Forward-Looking & Risk Themes
*Tests: Qualitative synthesis from the "Looking Ahead" section*

**Q19**
> What are the key risks and macroeconomic themes Goldman Sachs is monitoring heading into 2026?

✅ Expected: US military action against Iran, US-China relationship developments, AI disruption and market volatility, regulatory environment changes, credit cycle concerns (private credit underwriting quality, exposure to software companies affected by AI), European geopolitical leverage

---

## 🔁 CATEGORY 8 — Multi-Turn Memory (send Q20 immediately after Q3)
*Tests: Does the bot use the previous answer in memory to answer a follow-up?*

**Q20** *(follow-up to Q3 about ROE)*
> How does that compare to where it was at the time of Investor Day in 2020?

✅ Expected: Uses memory from Q3 (ROE = 15.0% in 2025). Answer should reference that ROE was **10.0% in 2019** (Investor Day baseline) and has improved by **500 basis points** since then, equivalent to a **50% improvement** in return on equity over that period

---

## 📊 Scoring Guide

| Score | Criteria |
|---|---|
| ✅ Full marks | Answer matches expected, cites page or section, no hallucination |
| ⚠️ Partial | Correct direction but missing a number or imprecise |
| ❌ Fail | Wrong number, hallucinated figure, or "couldn't find" on content that exists |

**Key things to verify:**
- Dollar figures are exact (e.g. $58.3B not $58B or $60B)
- Percentages are accurate (27% EPS growth, 15% ROE, 341% TSR)
- Chart descriptions mention both the start and end values
- Executive names and titles are correct
- Follow-up Q20 references the prior ROE answer without re-asking

---

## ⚙️ What Each Question Tests in Your Bot

| Q | Tests |
|---|---|
| Q1-Q4 | Text extraction from shareholder letter |
| Q5-Q8 | Markdown table reading (AWM targets table, GS 3.0 table, key metrics table) |
| Q9-Q11 | Bar chart / graph visual description via GPT-4o vision pipeline |
| Q12-Q13 | Leadership photo recognition via vision + caption extraction |
| Q14-Q17 | Multi-paragraph strategy synthesis across pages 5-7 |
| Q18 | Single-fact extraction from dense narrative text |
| Q19 | Qualitative synthesis from "Looking Ahead" (page 13) |
| Q20 | Session memory — follow-up resolution without re-retrieval |
