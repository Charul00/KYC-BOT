# KYC Chatbot — 25 Test Questions
**Data files required (upload in this order):**
1. `KYC_Customer_Database.xlsx` (28 MB — 75K customers, 100K transactions, 20K alerts)
2. `KYC_Policy_and_Procedures.pdf` (17 MB — 25-section policy manual with embedded images)
3. `KYC_BRD_Process_Rules.pptx` (20 MB — 20+ slides with BRD rules and escalation matrix)
4. `KYC_Identity_Document_CUST00042.png` (17 MB — scanned identity document image)

**Expected routes per query:**
- **EXCEL_QUERY** → Pandas execution on structured data
- **RAG_QUERY** → Hybrid vector + BM25 retrieval from policy/BRD documents
- **RULE_QUERY** → BRD rule application against Excel customer data
- **MIXED_QUERY** → Both Excel data + document context required

---

## 🟩 EXCEL_QUERY — Structured Data Analysis

**Q1 — Count & Filter**
> How many customers in the database have a risk level of VERY HIGH?

*Expected:* SQL-style count from Customer Master sheet filtered on risk_level = "VERY HIGH". Should return a number close to 3,750 (5% of 75,000).

---

**Q2 — Aggregation**
> What is the total transaction volume (in USD) recorded in the transaction history?

*Expected:* Sum of `amount_usd` column across all 100,000 rows in Transaction History sheet. Should return a large number in the billions range.

---

**Q3 — Top-N Ranking**
> Which 5 customers have the highest number of transactions flagged by the monitoring system?

*Expected:* GROUP BY customer_id on Transaction History where monitoring_flag = "YES", COUNT, ORDER BY DESC, TOP 5. Returns customer IDs with counts.

---

**Q4 — Cross-Sheet Lookup**
> How many HIGH risk customers currently have OPEN alerts in the alerts log?

*Expected:* Requires joining Customer Master (risk_level = HIGH) with Alerts Log (status = OPEN). Should return a joined count.

---

**Q5 — Percentage Calculation**
> What percentage of all transactions were flagged by the automated monitoring system?

*Expected:* COUNT(monitoring_flag = "YES") / COUNT(*) * 100 from Transaction History. Should be close to 8% based on generation parameters.

---

**Q6 — Distribution Analysis**
> Break down customers by risk level — how many are LOW, MEDIUM, HIGH, and VERY HIGH?

*Expected:* GROUP BY risk_level with counts for all 4 levels. Low ~37,500, Medium ~22,500, High ~11,250, Very High ~3,750.

---

**Q7 — Follow-up Memory Test (send immediately after Q6)**
> What percentage of those are PEP customers?

*Expected:* Uses `last_excel_result` from session memory. Calculates PEP counts from Customer Master, does not re-query from scratch.

---

## 🟦 RAG_QUERY — Policy & Document Retrieval

**Q8 — Policy Definition**
> What is the difference between Customer Due Diligence (CDD) and Enhanced Due Diligence (EDD)?

*Expected:* Retrieved from Section 3 (CDD) and Section 4 (EDD) of KYC Policy PDF. Should explain risk tiers, when EDD triggers, what EDD requires vs. CDD.

---

**Q9 — Threshold Lookup**
> At what transaction amount does a Suspicious Activity Report (SAR) need to be filed?

*Expected:* From Appendix C of PDF — "$5,000 or more when funds derived from illegal activity". Also mentions structuring regardless of amount.

---

**Q10 — Jurisdiction Question**
> Which countries are on the FATF blacklist according to our KYC policy?

*Expected:* From Appendix B of PDF — "Democratic People's Republic of Korea (DPRK), Iran, Myanmar".

---

**Q11 — BRD Slide Content**
> What are the Level 3 and Level 4 escalation triggers in the KYC escalation matrix?

*Expected:* Retrieved from PPTX "Escalation Matrix" slide — Level 3: PEP approvals, VERY HIGH risk, correspondent banking; Level 4: CCO — sanctions matches, SAR decisions, regulatory inquiries.

---

**Q12 — Retention Policy**
> How long must KYC documents be retained after account closure?

*Expected:* From Section 10 of PDF — "5 years from account opening or last transaction" and "7 years for EDD customers".

---

**Q13 — PEP Definition**
> Who qualifies as a Politically Exposed Person under our KYC policy?

*Expected:* From Section 11 of PDF — heads of state, senior politicians, government officials, judicial, military, state-owned corporation executives, political party officials, plus their family members and close associates.

---

**Q14 — Image OCR Test**
> What information is visible on the KYC identity document image that was uploaded?

*Expected:* Retrieved from the PNG image via OCR + GPT-4o vision pipeline. Should describe the content of the KYC identity document image (customer name area, document type, etc.).

---

**Q15 — PPTX Acceptance Criteria**
> What are the acceptance criteria for the KYC chatbot system according to the BRD?

*Expected:* Retrieved from PPTX "Acceptance Criteria" slide — 7 criteria including 95% accuracy, 5-second response time, 10-turn memory, 2-second streaming start, no hallucinations.

---

## 🟧 RULE_QUERY — BRD Rule Execution on Customer Data

**Q16 — Sanctions Rule**
> Based on the BRD rules, which customers should have their accounts frozen immediately?

*Expected:* RULE B4 — customers with sanctions_match_score > 70. Should execute against Customer Master, return count/list of matching customer IDs.

---

**Q17 — FATF Risk Upgrade**
> Which customers need their risk level upgraded because they're from FATF grey-list countries but not currently rated HIGH?

*Expected:* RULE A5 — customers with country IN FATF_GREYLIST AND risk_level != HIGH. Cross-reference Appendix B from policy doc with Excel data.

---

**Q18 — ID Renewal Rule**
> According to BRD rules, which customers need to be contacted for ID document renewal?

*Expected:* RULE B2 — id_expiry_date < TODAY + 90 DAYS. Execute date comparison against Customer Master id_expiry_date column.

---

**Q19 — Overdue Review Rule**
> Which LOW risk customers are overdue for their 36-month periodic review?

*Expected:* RULE B5 — last_review_date > 36 months ago AND risk_level = LOW. Date arithmetic on Customer Master.

---

**Q20 — Adverse Media Rule**
> Which customers should be escalated to the CCO based on adverse media hits according to BRD rules?

*Expected:* RULE B3 — adverse_media_hits > 3 → trigger_EDD AND escalate_to_ccm. Execute against Customer Master, return customer list with their adverse media scores.

---

## 🟥 MIXED_QUERY — Cross-Document + Data Required

**Q21 — Policy + Data Compliance Check**
> Are there any customers with PEP status who don't have a HIGH or VERY HIGH risk classification, which would be a policy violation?

*Expected:* Requires both: BRD/Policy (PEP must be HIGH+) AND Excel data (PEP = YES customers with risk_level = LOW/MEDIUM). Should return violating customer count.

---

**Q22 — Transaction Threshold + SAR Policy**
> How many wire transfers exceeded $50,000 to high-risk destination countries, and what does our policy say should happen in such cases?

*Expected:* Excel → Transaction History filter (transaction_type = WIRE, amount_usd > 50000, destination_country IN high-risk list). Policy → SAR filing thresholds and monitoring rules from PDF/PPTX.

---

**Q23 — Escalation Matrix + Alert Data**
> Looking at CRITICAL severity alerts that are still OPEN, which escalation level do they require according to the BRD?

*Expected:* Excel → Alerts Log (severity = CRITICAL, status = OPEN) — count/list. PPTX → Escalation Matrix slide — maps CRITICAL alerts to Level 4 (CCO). Combined answer.

---

**Q24 — EDD Trigger + Customer Data**
> Which customers currently trigger Enhanced Due Diligence requirements based on the policy criteria, and how many do we have?

*Expected:* Policy (EDD triggers: PEP, FATF high-risk country, HIGH/VERY HIGH risk, adverse media) cross-referenced with Excel Customer Master. Multi-condition filter with count.

---

**Q25 — Multi-Turn Conversation Test**
*(Send Q21 first, then wait for answer, then send this)*

> Of those non-compliant PEP customers, how many have active alerts in the alerts log?

*Expected:* Uses session memory from Q21 result (the non-compliant PEP customer list). Joins against Alerts Log where status = OPEN for those specific customer IDs. Tests memory + new Excel sub-query.

---

## ✅ How to Use These Questions

1. **Upload all 4 files** via the Upload Documents panel (use async upload — files are large)
2. **Wait for all 4 documents to reach "ready" status** in the upload panel before asking questions
3. **Run questions in order within their category** — follow-up questions (Q7, Q25) depend on earlier answers being in session memory
4. **Evaluate responses** on:
   - **Accuracy** — does the answer match the data/policy?
   - **Grounding** — does it cite the source document or data?
   - **No hallucination** — does it refuse to answer when data is insufficient?
   - **Route correctness** — check backend logs for expected route type

---

## 🔍 Scoring Rubric

| Criterion | What to Check |
|---|---|
| EXCEL accuracy | Verify numbers against the actual data |
| RAG accuracy | Cross-check answer with the policy PDF/PPTX content |
| RULE accuracy | Manually verify rule logic matches BRD slides |
| Memory retention | Q7 and Q25 should reference previous answer, not start fresh |
| Source citation | Answer should mention which document/section/sheet |
| Hallucination check | Ask about non-existent customers — bot should say "not found" |
| Image OCR quality | Q14 answer quality reflects OCR + vision pipeline performance |
