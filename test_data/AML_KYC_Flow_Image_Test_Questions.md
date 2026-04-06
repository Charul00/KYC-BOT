# AML KYC Flow – Image Test Questions
**Source:** `aml_kyc_flow [classic]_Creatly.png`
**Purpose:** Test chatbot's ability to read, analyze and answer questions from PNG/JPEG flowchart images
**Total Questions:** 35

---

## Category 1 — Basic Flow & Entry Point (5 Questions)

**Q1.** What is the starting point of this AML KYC flow diagram?

**Expected Answer:** The starting point is "Inbound Inquiry" shown at the top of the diagram as a parallelogram shape labeled "Start".

---

**Q2.** What is the very first decision a user must pass through in this KYC flow?

**Expected Answer:** The first decision is "Have they signed up?" — a diamond-shaped decision node right after the Inbound Inquiry start point.

---

**Q3.** If a user has NOT signed up yet, what is the first action they should take according to the flow?

**Expected Answer:** They should "Go to the link of the token sale and click 'sign up'".

---

**Q4.** How many decision points (diamond shapes) are there in this flowchart?

**Expected Answer:** There are multiple decision diamonds including: Have they signed up?, Have they agreed to terms and conditions?, Have they received an activation email?, Have they created a custom password and log in?, Did they find it?, Have they submitted their ID and selfie with ID?, Have they verified their information is correct?, Have they added a wallet address to receive ERC20 tokens?, Have they sent contribution to wallet address?

---

**Q5.** What does "Process Complete" represent in this flow and what shape is it shown as?

**Expected Answer:** "Process Complete" is the final successful end state of the KYC process, shown as a pink/red rounded rectangle at the bottom center of the diagram.

---

## Category 2 — Terms & Conditions Path (4 Questions)

**Q6.** After a user has signed up, what is the next check in the flow?

**Expected Answer:** After signing up, the next check is "Have they agreed to terms and conditions?"

---

**Q7.** What happens if a user has signed up but has NOT agreed to the terms and conditions?

**Expected Answer:** They are directed to "Get them to go back to sign up link and start process over."

---

**Q8.** If a user agrees to the terms and conditions, what is the next step in the process?

**Expected Answer:** The next step checks "Have they received an activation email?"

---

**Q9.** What are the two conditions a user must satisfy before reaching the activation email check?

**Expected Answer:** The user must have (1) signed up and (2) agreed to the terms and conditions.

---

## Category 3 — Activation Email Path (6 Questions)

**Q10.** What happens if the user has NOT received an activation email?

**Expected Answer:** The flow asks "Have they created a custom password and log in?" to determine the next action.

---

**Q11.** If the user has not received an activation email AND has not created a custom password, what should they do?

**Expected Answer:** They should "Get them to check Inbox and Junk email."

---

**Q12.** What happens after the user checks their Inbox and Junk email — what is the next decision?

**Expected Answer:** The next decision is "Did they find it?" (referring to the activation email).

---

**Q13.** If the user checks their inbox and junk folder but CANNOT find the activation email, what is the final instruction?

**Expected Answer:** "Get them to start the process over again."

---

**Q14.** If the user checks their inbox and junk folder and DOES find the activation email, what happens next?

**Expected Answer:** "Move them to the next step in the process."

---

**Q15.** If the user HAS received an activation email, what is the next step?

**Expected Answer:** They are directed to "Get them to submit KYC/AML information (review page 4 CM-Training document)."

---

## Category 4 — KYC/AML Submission Path (5 Questions)

**Q16.** What document is referenced when submitting KYC/AML information?

**Expected Answer:** "Page 4 of the CM-Training document" is referenced for KYC/AML information submission.

---

**Q17.** After submitting KYC/AML information, what is the next decision in the flow?

**Expected Answer:** "Have they submitted their ID and selfie with ID?"

---

**Q18.** What happens if the user has NOT submitted their ID and selfie with ID?

**Expected Answer:** The flow loops back — they are asked again to submit KYC/AML information (the No path loops back to the submission step).

---

**Q19.** After successfully submitting their ID and selfie, what is the next verification check?

**Expected Answer:** "Have they verified their information is correct?"

---

**Q20.** What happens if the user has NOT verified their information is correct after ID submission?

**Expected Answer:** There is another check "Have they verified their information is correct?" — the No path loops back for re-verification.

---

## Category 5 — Wallet & Contribution Path (5 Questions)

**Q21.** After verifying their information is correct, what is the next step in the KYC flow?

**Expected Answer:** "Have they added a wallet address to receive ERC20 tokens?"

---

**Q22.** What type of tokens require a wallet address in this KYC flow?

**Expected Answer:** ERC20 tokens require a wallet address.

---

**Q23.** What happens if the user has NOT added a wallet address for ERC20 tokens?

**Expected Answer:** They are directed to "Get them to verify their information is correct and add a wallet."

---

**Q24.** After adding a wallet address, what is the final decision before process completion?

**Expected Answer:** "Have they sent contribution to wallet address?"

---

**Q25.** If the user has NOT sent their contribution to the wallet address, what should they do?

**Expected Answer:** "Get them to send contribution to specified address inside portal."

---

## Category 6 — Scenario-Based Questions (5 Questions)

**Q26.** A new user calls with an inbound inquiry. They signed up, agreed to terms, but say they never received any activation email. Walk me through exactly what steps the agent should follow.

**Expected Answer:**
1. Confirm they signed up ✓
2. Confirm they agreed to terms ✓
3. Check activation email → No
4. Ask if they created a custom password and logged in → No
5. Ask them to check Inbox and Junk email
6. Did they find it? If Yes → move to next step. If No → start process over.

---

**Q27.** A user has completed all KYC steps, submitted ID and selfie, verified their information, but hasn't sent their contribution yet. What is the ONLY remaining step for Process Complete?

**Expected Answer:** They need to "send contribution to wallet address" (the specified address inside the portal). Once that is done, the Process is Complete.

---

**Q28.** How many different paths can lead to "starting the process over" in this flow?

**Expected Answer:** Two paths lead to restarting: (1) User agreed to sign up but did NOT agree to terms and conditions → "Go back to sign up link and start over", and (2) User could not find activation email in inbox/junk → "Start the process over again."

---

**Q29.** What is the longest possible path a user can take from Inbound Inquiry to Process Complete?

**Expected Answer:** The longest path goes through all Yes decisions: Signed up → Agreed to T&C → Received activation email → Submitted KYC/AML info → Submitted ID + selfie → Verified information → Added wallet address → Sent contribution → Process Complete.

---

**Q30.** Can a user reach "Process Complete" without ever adding a wallet address? Why or why not?

**Expected Answer:** No. Adding a wallet address to receive ERC20 tokens is a mandatory step in the flow. If they haven't added one, they are redirected to verify information and add a wallet. There is no path to Process Complete that bypasses the wallet address step.

---

## Category 7 — Visual & Structure Questions (5 Questions)

**Q31.** What color are most of the action/process boxes in this flowchart?

**Expected Answer:** Most action and process boxes are blue/dark blue in color.

---

**Q32.** What shape is used for decision points in this flowchart?

**Expected Answer:** Diamond shapes are used for decision points (Yes/No questions).

---

**Q33.** What is unique about the "Process Complete" box compared to all other boxes in the diagram?

**Expected Answer:** "Process Complete" is the only pink/red colored rounded rectangle in the diagram, making it visually distinct as the successful end state.

---

**Q34.** What shape is the "Inbound Inquiry" starting node and why is it different from regular process boxes?

**Expected Answer:** It is a parallelogram shape, which in flowchart conventions represents an input/output or trigger event — different from regular rectangles which represent processes/actions.

---

**Q35.** How are "Yes" and "No" paths indicated in this flowchart?

**Expected Answer:** Yes and No labels are written directly on the arrows/lines connecting decision diamonds to the next steps, with arrows indicating the direction of flow.

---

## Scoring Guide

| Score | Meaning |
|---|---|
| 90-100% | Excellent image analysis — chatbot reads PNG diagrams accurately |
| 70-89% | Good — minor details missed but flow understood |
| 50-69% | Average — main flow understood but decision paths confused |
| Below 50% | Poor — image not being analyzed properly, text-only retrieval happening |

## Test Notes
- Upload the PNG image first to the chatbot
- Then ask each question one by one
- Check if answers match the visual flow — NOT just text from other KYC documents
- If chatbot gives answers from other documents (policy manuals, etc.) instead of the image, that indicates a **conflict/mixing issue**
