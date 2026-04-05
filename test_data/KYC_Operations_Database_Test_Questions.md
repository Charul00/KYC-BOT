# KYC Operations Database — Chatbot Test Questions

Upload `KYC_Operations_Database.xlsx` to the chatbot, then ask these questions.
Tests all Excel operations: COUNTIF, SUM, AVERAGE, MAX, filtering, cross-sheet lookups.

---

## CATEGORY 1 — Customer Master: Basic Counts
*Tests: COUNTIF on large datasets, KYC status lookups*

**Q1.** How many total customers are in the database?
> ✅ Expected: **40,000**

**Q2.** How many customers have a Verified KYC status?
> ✅ Expected: **23,860**

**Q3.** How many customers are currently Pending KYC?
> ✅ Expected: **5,998**

**Q4.** How many customers have an Expired KYC status?
> ✅ Expected: **3,198**

**Q5.** How many customers require EDD (Enhanced Due Diligence)?
> ✅ Expected: **1,207**

**Q6.** How many customers were Rejected?
> ✅ Expected: **1,617**

**Q7.** How many customers are Under Review?
> ✅ Expected: **4,120**

---

## CATEGORY 2 — Customer Master: Risk & PEP
*Tests: risk classification counts, PEP flag filtering*

**Q8.** How many PEP (Politically Exposed Person) customers are in the database?
> ✅ Expected: **1,958**

**Q9.** How many customers are classified as Low Risk?
> ✅ Expected: **12,502**

**Q10.** How many customers are Medium Risk?
> ✅ Expected: **14,324**

**Q11.** How many customers are High Risk?
> ✅ Expected: **7,089**

**Q12.** How many customers are Very High Risk?
> ✅ Expected: **6,085**

**Q13.** What is the average risk score across all customers?
> ✅ Expected: **50.55**

**Q14.** What is the average annual income of customers in USD?
> ✅ Expected: **~$1,002,481**

---

## CATEGORY 3 — Transactions: Volume & Aggregates
*Tests: SUM, AVERAGE, MAX on 58,000 rows*

**Q15.** How many transactions are in the database?
> ✅ Expected: **58,000**

**Q16.** What is the total transaction volume in USD?
> ✅ Expected: **~$14.5 billion** / $14,503,358,623

**Q17.** What is the average transaction amount in USD?
> ✅ Expected: **~$250,058**

**Q18.** What was the largest single transaction amount in USD?
> ✅ Expected: **~$499,990**

**Q19.** What is the total processing fees collected in USD?
> ✅ Expected: **~$43.5 million** / $43,481,342

---

## CATEGORY 4 — Transactions: Alerts & Compliance
*Tests: conditional counts, compliance flag filtering*

**Q20.** How many transactions triggered an alert?
> ✅ Expected: **4,619**

**Q21.** What is the alert trigger rate as a percentage of total transactions?
> ✅ Expected: **~7.96%**

**Q22.** How many transactions were blocked by compliance?
> ✅ Expected: **1,746**

**Q23.** What is the most common transaction type in the database?
> ✅ Expected: **Trade Finance (5,874 transactions)**

**Q24.** What is the most common transaction channel used?
> ✅ Expected: **Online (9,740 transactions)**

---

## CATEGORY 5 — Risk Assessments
*Tests: assessment outcome counts, score calculations*

**Q25.** How many risk assessments are recorded in total?
> ✅ Expected: **18,000**

**Q26.** What is the average composite risk score across all assessments?
> ✅ Expected: **54.4**

**Q27.** How many assessments resulted in an Approved decision?
> ✅ Expected: **11,697**

**Q28.** How many assessments require EDD?
> ✅ Expected: **3,539**

**Q29.** How many assessments were Escalated?
> ✅ Expected: **1,278**

**Q30.** How many assessments resulted in Rejection?
> ✅ Expected: **1,486**

**Q31.** What is the highest composite risk score recorded in any assessment?
> ✅ Expected: **95.0**

**Q32.** What is the lowest composite risk score recorded?
> ✅ Expected: **13.1**

---

## CATEGORY 6 — AML Alerts
*Tests: SAR calculations, priority filters, alert type breakdown*

**Q33.** How many AML alerts are in the database?
> ✅ Expected: **12,000**

**Q34.** How many alerts are currently Open?
> ✅ Expected: **2,395**

**Q35.** How many SARs (Suspicious Activity Reports) have been filed?
> ✅ Expected: **1,469**

**Q36.** What is the SAR conversion rate (SARs filed as % of total alerts)?
> ✅ Expected: **~12.24%**

**Q37.** What is the total amount flagged across all AML alerts in USD?
> ✅ Expected: **~$6.04 billion** / $6,039,482,047

**Q38.** How many alerts are marked as Critical priority?
> ✅ Expected: **2,990**

**Q39.** How many alerts have been reported to the regulator?
> ✅ Expected: **988**

**Q40.** How many Sanctions Hit alerts are there?
> ✅ Expected: **1,167**

**Q41.** What is the average alert score?
> ✅ Expected: **75.1**

**Q42.** What is the average number of days that Open alerts have been outstanding?
> ✅ Expected: **~90.5 days**

**Q43.** What is the most common alert type in the database?
> ✅ Expected: **Round Tripping (1,240 alerts)**

---

## CATEGORY 7 — Cross-Sheet / Multi-Fact
*Tests: combining facts from multiple sheets, reasoning*

**Q44.** What percentage of total customers are classified as PEPs?
> ✅ Expected: **~4.9%** (1,958 / 40,000)

**Q45.** Out of all risk assessments, what percentage resulted in EDD being required?
> ✅ Expected: **~19.7%** (3,539 / 18,000)

**Q46.** What percentage of all transactions were blocked?
> ✅ Expected: **~3.01%** (1,746 / 58,000)

**Q47.** What is the ratio of Open alerts to total alerts?
> ✅ Expected: **~19.96%** (2,395 / 12,000)

**Q48.** How does the number of High Risk + Very High Risk customers compare to total customers?
> ✅ Expected: **13,174 out of 40,000 = ~32.9%** (7,089 + 6,085)

---

## CATEGORY 8 — Ranking & Top/Bottom
*Tests: sorting and ranking operations*

**Q49.** Which bank has the most customers in the database?
> ✅ Expected: **State Bank of India (4,077 customers)**

**Q50.** Which nationality has the most customers?
> ✅ Expected: **Canada (2,081 customers)**

**Q51.** Which occupation is most common among customers?
> ✅ Expected: **NGO Worker (2,312 customers)**

**Q52.** Which alert type appears most frequently in the AML Alerts sheet?
> ✅ Expected: **Round Tripping (1,240 alerts)**

---

## CATEGORY 9 — Edge Cases (Hallucination Check)
*Tests: bot must say "not available" — NOT make up answers*

**Q53.** Which individual customer has the highest transaction volume?
> ✅ Expected: Cannot be determined from this database without a join query — bot should say it cannot compute this directly or provide a caveat.

**Q54.** What is the total KYC compliance cost for FY2024?
> ✅ Expected: **Not in the database.** Bot should not make up a number.

**Q55.** How many customers were onboarded in January 2024 specifically?
> ✅ Expected: The data has Onboarding_Date but the bot may not be able to run a month-level filter — it should acknowledge this limitation rather than guess.

---

## CATEGORY 10 — Summary Dashboard Verification
*Tests: whether the bot reads the pre-calculated Summary_Dashboard sheet*

**Q56.** According to the Summary Dashboard, what is the KYC alert rate?
> ✅ Expected: **~7.96%** (from the Alert Rate formula cell on Summary_Dashboard)

**Q57.** What does the Summary Dashboard show as the total flagged amount across AML alerts?
> ✅ Expected: **~$6.04 billion**

**Q58.** According to the Summary Dashboard, how many assessments required EDD?
> ✅ Expected: **3,539**

---

## Quick Scoring Guide

| Score | What it means |
|---|---|
| Q1–Q7 correct | Basic COUNTIF on Customer_Master working ✅ |
| Q8–Q14 correct | Risk + PEP filtering working ✅ |
| Q15–Q24 correct | Transaction aggregates and filtering working ✅ |
| Q25–Q32 correct | Risk Assessment lookups working ✅ |
| Q33–Q43 correct | AML Alert operations working ✅ |
| Q44–Q52 correct | Cross-sheet reasoning and ranking working ✅ |
| Q53–Q55 says "cannot determine" | No hallucination on Excel edge cases ✅ |
| Q56–Q58 reads Summary_Dashboard | Summary sheet retrieval working ✅ |

**Most important checks:** Q53–Q55 (hallucination on things the bot cannot compute), Q36 (SAR rate calculation), and Q16 (billion-dollar total volume).
