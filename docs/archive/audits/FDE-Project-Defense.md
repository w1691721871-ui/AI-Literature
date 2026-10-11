# ResearchOS FDE Project Defense

## One-sentence positioning

ResearchOS is an **AI Research Employee** for enterprise research teams: it
organizes an explicit Mission, keeps sources traceable, pauses for human
Review, and prepares reusable research Deliveries inside a governed Workspace.

## Why is this not simply ChatGPT?

ChatGPT is optimized for a conversational answer. ResearchOS is organized
around accountable research work. A Mission has a Workspace boundary, an
Evidence requirement, a visible review state, an Artifact lifecycle, and an
audit-aware human decision point. The product is valuable when a team needs to
explain how a finding became a delivery—not only read a response.

ResearchOS does not claim that a conversational model is insufficient for all
research. It solves the different enterprise problem of making research work
repeatable, visible, and reviewable across people.

## What is the AI Employee’s core value?

The AI Employee turns a stated outcome into a governed sequence:

`Mission → research work → candidate sources → Evidence → human Review → Delivery`

The value is the continuity of this record. A team can see the current focus,
why an action matters, what requires a decision, and what knowledge is safe to
reuse in the same Workspace.

## Why is human Review required?

Review protects the point where research information becomes a consequential
decision or a delivery. Candidate sources can be useful, relevant, and still
be incomplete, conflicting, misapplied, or outside the project’s authorized
scope. ResearchOS therefore keeps these boundaries explicit:

- a source candidate is not automatically trusted Evidence;
- Evidence does not automatically become a decision;
- an Artifact is not automatically delivered.

This is a product choice for accountable enterprise use, not a cosmetic
approval screen.

## What is the distinction between RAG and an AI Employee?

Retrieval-augmented generation (RAG) is a technique for finding relevant
material and grounding a response in it. An AI Employee is the product-level
work model around that capability: it has a Mission, authorized Workspace
context, bounded actions, Evidence and review checkpoints, an Artifact
lifecycle, and a human decision boundary.

ResearchOS may use retrieval as part of research work, but retrieval alone
does not supply ownership, governance, review, or delivery accountability.

## How does ResearchOS maintain trust?

1. **Workspace isolation:** work and reusable research context are scoped to
   the authorized Workspace.
2. **Evidence separation:** candidate sources remain separate from verified
   Evidence.
3. **Human control:** review gates protect consequential Evidence, controlled
   work, and Delivery decisions.
4. **Traceable outputs:** Deliveries display their lifecycle and Evidence
   support rather than claiming an unverified final result.
5. **Bounded computer assistance:** the Computer Employee prepares authorized
   research, document, or report work; it does not silently log in, upload,
   publish, or change external systems.

The product does not store prompts, hidden reasoning, or fabricated
organizational learning as customer-facing research records.

## How would an enterprise deploy it?

The reference deployment separates the static frontend from the FastAPI API.
The API runs with managed secrets, explicit allowed browser origins, and a
persistent work directory. For a durable public demo or enterprise pilot:

1. Deploy the API with its documented environment variables and release
   identity.
2. Attach persistent storage at `/var/data` and set
   `WORK_DIRECTORY=/var/data` so SQLite, PDFs, FAISS, embeddings, and
   generated Artifacts survive restarts.
3. Configure CORS for the exact frontend origin—never a wildcard.
4. Provision Workspace roles and Reviewer access through the existing identity
   layer.
5. Import only authorized source material, verify the corpus, and run a
   managed restart check before claiming production readiness.

## How can the product extend safely?

ResearchOS can expand by adding authorized source providers, Delivery formats,
and domain-specific review policies while preserving the same core contract:

`Workspace → Mission → Evidence → Review → Delivery`

The safe extension principle is to add capability behind existing permissions,
Evidence requirements, and review boundaries—not to grant an AI Employee
unbounded external access. This makes the platform suitable for a controlled
pilot first, followed by domain and connector expansion based on observed
customer workflows.

## Honest limitations to state in an interview

- Research quality remains limited by the relevance and quality of authorized
  source material.
- A live building-materials demonstration requires a real, scenario-matched
  corpus; the existing public technical seed corpus is not a substitute.
- Review requires a real authorized Reviewer; the Demo Member path deliberately
  cannot approve a decision.
- Production durability must be validated on persistent infrastructure after a
  managed restart.

## Closing statement

ResearchOS is not trying to replace research judgment. It makes the work
between a research question and an accountable deliverable more visible,
grounded, collaborative, and reusable.
