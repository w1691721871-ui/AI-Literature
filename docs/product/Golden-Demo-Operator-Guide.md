# ResearchOS Golden Demo Operator Guide

## Purpose and operating rule

This guide makes the five-minute FDE demonstration repeatable without
fabricating a Mission, Evidence record, review decision, Artifact, reviewer,
or customer result. The Golden Demo uses the existing Workspace, Mission,
Evidence, Review, and Delivery flows only.

**Golden customer scenario:** a building-materials R&D team is investigating
future opportunities in low-carbon building materials.

**Golden research goal:**

> Analyze future research opportunities in low-carbon building materials using
> traceable evidence.

## Current readiness assessment

| Gate | Local observation | Production requirement | Status |
| --- | --- | --- | --- |
| Demo identity | Existing Demo Workspace flow is documented and visibly labelled in the product. | `DEMO_MODE=true` and provisioned Demo credentials. | Verify in deployed environment. |
| Corpus integrity | Read-only local check reported 7 papers, 180 chunks, 180 embeddings, and `faiss: PASS`. | Persisted material and FAISS must be available after a managed restart. | Local pass; production not verified. |
| Scenario relevance | The Golden source manifest contains six public, low-carbon-building-materials PDFs. | All six sources must be persisted and reported by the scenario-alignment check. | **Waiting for seed in the Demo environment.** |
| Reviewer handoff | The product enforces the Reviewer boundary. | A separately authenticated Reviewer or higher-role session. | Required for approval demo. |
| Delivery | Lifecycle is available in the product. | A real Artifact created by the governed Mission path. | Verify before the meeting. |

Do not describe a corpus as customer evidence merely because it is indexed.
The Golden Dataset is ready only when the scenario-alignment check confirms
the documented building-materials sources are actually persisted.

## Standard Golden Demo Dataset

The dataset must be prepared through the existing authorized paper-library
ingestion and indexing flow. It is not front-end sample data.

### Required records

| Record | Standard | Evidence of preparation |
| --- | --- | --- |
| Research Mission | One persisted Mission using the Golden research goal above. | Visible in Mission Room with its real current status. |
| Source corpus | At least five authorized public papers or reports directly relevant to low-carbon building materials. Keep publisher, DOI/landing URL, title, year, and access date in the source record. | Read-only corpus check reports non-zero papers, chunks, embeddings, and `faiss: PASS`. |
| Candidate Evidence | Extracted from the persisted source corpus by the existing Mission flow. | Candidate state remains distinct from approved Evidence. |
| Review state | One real candidate-Evidence or Delivery decision awaiting the prepared Reviewer. | Visible Review state; never manually renamed to “approved.” |
| Artifact state | One real Research Brief or Artifact draft tied to the Mission and its Evidence. | Delivery Center shows its actual Draft, Review, Approved, or Delivered stage. |

### Allowed source scope

Use only openly accessible, authorized material relevant to the scenario, for
example peer-reviewed papers, public standards bodies, or public institutional
reports covering low-carbon concrete, recycled aggregate, lifecycle assessment,
durability, or carbon-mineralized materials. Record source provenance before
uploading. Do not use private customer documents unless the customer has
authorized them for the demo.

### Seed and verification procedure

1. Attach the production persistent disk at `/var/data` and set
   `WORK_DIRECTORY=/var/data` before importing any material.
2. Provision the Demo Workspace using `DEMO_MODE=true` and deployment-managed
   Demo Owner and Reviewer credentials.
3. Run the repeatable, approved import through the existing authorized library
   ingestion path:

   ```text
   python scripts/seed_demo_corpus.py
   ```

   Let the normal parser, embedding, and FAISS indexing steps finish.
4. Run the read-only check in the deployed service environment:

   ```text
   python scripts/check_demo_corpus.py
   ```

   It must report `papers >= 6`, `chunks > 0`, `embeddings > 0`,
   `faiss: PASS`, and `scenario alignment: PASS`.
5. Create the Golden Mission through the normal Mission form. Allow the
   existing workflow to produce candidate Evidence; do not insert Evidence
   records manually.
6. Use the separately authenticated Reviewer to make a real review decision.
   Generate the Delivery only through the existing governed path.

`python scripts/seed_demo_corpus.py` uses the approved public source manifest
in [Golden Demo Corpus Guide](Golden-Demo-Corpus-Guide.md). It is idempotent,
hash-checks existing sources, and uses the normal ingestion path. It is not
proof of readiness until the deployed persistent environment reports scenario
alignment as `PASS`.

## Operator preflight: 10 minutes before the meeting

- [ ] Open the deployed product in a clean browser profile and select **Try
  Demo**.
- [ ] Confirm the Demo banner names **ResearchOS Demo Environment**.
- [ ] Confirm the Demo banner reports indexed sources as available.
- [ ] Run `python scripts/check_demo_corpus.py` on the deployed persistent
  environment, not only on a laptop.
- [ ] Open the Golden Mission and confirm the current focus and work journal
  are real persisted records.
- [ ] Confirm at least one candidate Evidence item or a clear Evidence boundary
  is visible.
- [ ] Sign in to the separately prepared Reviewer session in a second browser
  profile.
- [ ] Confirm the Delivery Center reflects a real Artifact lifecycle stage.
- [ ] Keep **Solution Demo** open in a second tab as the narrative fallback.

## Five-minute operator script

### 00:00 — Product introduction

Open **Home**.

Say: “ResearchOS is an AI Research Employee for enterprise research teams. It
turns a research goal into traceable Evidence, a human review decision, and a
reviewable Delivery.”

Point to the AI Employee identity and the statement that human decisions stay
in control.

### 01:00 — Customer challenge

Open **Solution Demo**.

Say: “Our customer is a building-materials R&D team. Their sources and
handoffs are fragmented, so it is hard to connect a research claim to a
decision and a reusable result.”

Point to **Before AI Employee** and **With ResearchOS**. Do not claim a
quantified productivity result unless it has been measured for that customer.

### 02:00 — AI Employee Mission

Open the prefilled **Research Mission** or the prepared Golden Mission.

Say: “The employee works from an explicit Mission. Here is its current focus
and the work journal. It is not a hidden chat conversation.”

Point to the Mission goal, current focus, and research timeline.

### 03:00 — Evidence Review

Show supporting sources and the Evidence section.

Say: “These are source candidates until a Reviewer validates them. The system
will pause rather than turn an unverified source into a conclusion.”

If a live decision is prepared, switch to the Reviewer session and show the
real approval boundary. Do not approve an item merely for theatre.

### 04:00 — Delivery

Open **Research Delivery Center**.

Say: “Research results move through Draft, Review, Approved, and Delivered.
The stage shown here comes from the real Artifact record, not a presentation
mock-up.”

Show the actual Evidence support and next action for the prepared Artifact.

### 05:00 — Business value

Return to **Workspace** or the Solution Showcase.

Say: “The durable value is not one answer. It is a governed research record:
the team retains verified Evidence, review context, and a traceable Delivery
inside its Workspace.”

## Recovery paths

| Condition | Honest operator message | Recovery action |
| --- | --- | --- |
| Database is empty | “This Workspace is clean; ResearchOS will not invent a research history.” | Restore the approved persistent dataset, then repeat the corpus check. Use Solution Demo only for the product narrative. |
| Reviewer is unavailable | “This identity can prepare research but cannot approve it. That separation is intentional.” | Use the prepared Reviewer profile. Do not weaken the role boundary. |
| Evidence is insufficient | “The AI Employee is building a research foundation and is correctly pausing before an unsupported conclusion.” | Verify source scope and indexing; add only approved, relevant public material through the existing ingestion flow. |
| Backend is unavailable | “No live Workspace record can be claimed at this moment.” | Stop the live-workflow claim, use Solution Demo as narrative only, and restore the backend before retrying. |
| Delivery is absent | “A Delivery appears only after the governed path has created a real Artifact.” | Show the lifecycle and prepare the Artifact through the live reviewed Mission. |

## Non-negotiable statements

- Candidate source ≠ verified Evidence.
- Verified Evidence ≠ final business decision.
- Artifact draft ≠ delivered result.
- A Demo Member ≠ Reviewer.
- A local corpus check ≠ a production persistence check.
