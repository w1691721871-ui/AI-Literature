# Golden Demo Runbook

## Scenario boundary

**Customer:** a building-materials R&D team.
**Dataset label:** `Demo Dataset` — public research sources, never customer material.
**Golden Mission title:** `Analyze sustainable concrete material research opportunities`
**Golden Mission goal:** evaluate research opportunities for recycled materials in low-carbon concrete applications using traceable public evidence.

The Demonstration does not claim that a material is approved for a customer or
that a source is already verified Evidence. It shows the governed path that
keeps those decisions human-controlled.

## Data preparation

Use a **dedicated Demo deployment** only. The current paper library is
deployment-level, therefore the seed and reset scripts refuse a database with
another Workspace.

1. Attach persistent storage and configure `WORK_DIRECTORY=/var/data`.
2. Configure `DEMO_MODE=true`, Demo owner/reviewer credentials, and an
   embedding credential.
3. Provision the Demo identity once through the running service.
4. Set `RESEARCHOS_DEMO_CORPUS_TARGET=ResearchOS Demo Workspace`.
5. Seed public papers through the existing ingestion path:

   ```powershell
   python scripts/seed_demo_corpus.py
   python scripts/demo_diagnostics.py
   ```

Accept the corpus only when diagnostics show a dedicated Demo Workspace,
`papers > 0`, `chunks > 0`, `embeddings > 0`, `faiss: PASS`, and scenario
alignment `PASS`.

The seed's six public papers cover low-carbon concrete, recycled concrete
aggregate, lifecycle assessment, industrial by-products, aggregate quality,
and building-level lifecycle context. They are candidate sources, not an
automatic conclusion.

## Five-minute FDE walkthrough

### 0:00 — Home

Open the Demo Workspace. Point out the `Demo Dataset` boundary and explain:
ResearchOS is an AI Research Employee for a research team, not a chat answer.
Start the Golden Mission with the title and goal above.

### 1:00 — Mission Room

Show the Mission goal, current focus, and work journal. Start the existing
bounded Mission flow. The journal should record only actual Mission events.

### 2:00 — Evidence

Show the public source candidates returned through the normal retrieval path.
Explain source quality and the distinction between candidate material and
verified Evidence. If no candidate is returned, stop at the Evidence boundary;
do not narrate an unsupported conclusion.

### 3:00 — Human Review

Use a separately authenticated **Reviewer** identity. Show that the AI has
prepared a research result but cannot approve it. The Reviewer validates or
requests revision through the normal Review control.

### 4:00 — Delivery

Only after a real approval, generate the normal Research Brief / Delivery.
Show its research question, source-linked evidence summary, validation status,
and next steps. If review is still pending, show the Pending Review state and
explain that this is the intended control point.

### 5:00 — Solution Showcase

Open Solution Showcase to summarize the customer challenge, AI-supported work,
human governance, business value, and reusable Workspace knowledge.

## Roles

| Role | Demonstration responsibility |
| --- | --- |
| Owner | Confirms the Demo Workspace and frames the customer research goal. |
| Researcher | Creates/runs the Golden Mission and presents source candidates. |
| Reviewer | Makes the real Evidence / Mission review decision. |

No role should be simulated through a frontend state change or direct database
edit during the demonstration.

## Reset and recovery

Run this only while the API service is stopped and only against the dedicated
Demo database. The command takes a timestamped backup before it clears the
database, Demo PDFs, FAISS index, and generated delivery files.

```powershell
$env:DEMO_MODE = "true"
$env:RESEARCHOS_DEMO_CORPUS_TARGET = "ResearchOS Demo Workspace"
$env:RESEARCHOS_DEMO_RESET_CONFIRM = "RESET_RESEARCHOS_DEMO_DATA"
python scripts/reset_demo_workspace.py
python scripts/reset_demo_workspace.py --apply
python scripts/demo_diagnostics.py
```

The reset restores only Demo identity and the public corpus. It deliberately
does **not** fabricate a Mission, Evidence, Review, Insight, or Artifact. Run
the live governed workflow again after reset.

## Pre-flight checklist

- [ ] `python scripts/demo_diagnostics.py` exits `0`.
- [ ] Demo Workspace banner and `Demo Dataset` label are visible.
- [ ] The Golden Mission is real and belongs to the Demo Workspace.
- [ ] Candidate Evidence was retrieved from the seeded public corpus.
- [ ] A Reviewer session is available for the approval step.
- [ ] Delivery is shown only at its real current status.
- [ ] Backup location from any reset has been recorded.
