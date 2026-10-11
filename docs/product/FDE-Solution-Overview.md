# ResearchOS FDE Solution Overview

## Customer Challenge

Enterprise research teams often work across scattered literature, project notes, and prior decisions. Finding support for a research direction takes time, source quality is difficult to verify consistently, and useful work can disappear when it is not connected to a team-owned delivery process.

ResearchOS addresses that operational gap. It is designed for teams that need to turn a research question into traceable support, a human decision, and a reusable outcome.

## AI Research Employee Solution

ResearchOS provides an **AI Research Employee for Enterprise Research Teams**. It works from an authorized Mission inside a Workspace and keeps the customer-facing process visible:

```text
Research goal → Mission → Evidence preparation → Human Review → Artifact Delivery → Organizational Knowledge
```

The product is not a chat response presented as a final answer. It prepares research work within a defined scope and makes the supporting Evidence and approval boundary visible to the people responsible for the decision.

## Technical Architecture

ResearchOS is organized around a single enterprise workflow rather than separate AI experiences. The browser workspace presents authorized research work; the application service enforces identity, Workspace scope, and role boundaries; and the durable research records preserve the relationship between a Mission, its Evidence, Human Review, and Delivery.

- **Frontend** — a browser Workspace where teams assign Missions, inspect Evidence, make Review decisions, and read Deliveries.
- **Backend** — the governed application service that applies identity, Workspace isolation, and permission checks before records are read or changed.
- **LLM and retrieval** — provider credentials remain server-side. Retrieval-assisted research (RAG) can locate authorized source passages, but a retrieved passage remains a candidate until Evidence validation and Human Review occur.
- **Controlled digital assistance** — research, document, and report preparation remain permission-bounded; high-impact actions require approval and verified outcomes.
- **Artifact Delivery** — a Delivery stays connected to its Mission, supporting Evidence, and review status for traceability.

This architecture keeps the customer story simple: the AI Research Employee can prepare work only within an authorized Workspace, and every consequential Delivery stays connected to visible Evidence and a Human Review decision.

## Mission-Driven Workflow

1. **Set a research goal** — a team creates an authorized Mission with the outcome it needs.
2. **Prepare research work** — the AI Research Employee organizes the next bounded research steps using the active Workspace context.
3. **Collect candidate sources** — relevant public or authorized material is kept separate from verified Evidence.
4. **Request Human Review** — a Reviewer validates consequential source, finding, and delivery decisions.
5. **Prepare a Delivery** — approved work becomes a reviewable research Artifact with clear next action.
6. **Retain organizational knowledge** — approved work remains scoped to the Workspace for future authorized Missions.

## Evidence-First Research

ResearchOS treats a candidate source as a starting point, not as a research conclusion. Evidence remains traceable to its source and validation state. When the available support is insufficient, the product pauses at the Evidence boundary rather than creating an unsupported insight or pretending a research outcome is complete.

## Human Review Governance

The AI Research Employee prepares work; authorized people make consequential decisions.

- Important research, delivery, and external-impact decisions require Human Review.
- Reviewers can approve, request revision, or reject based on visible supporting Evidence.
- Workspace membership and role boundaries control access to Missions, Evidence, Reviews, and Deliveries.
- The product does not expose credentials, private source bodies, prompts, or chain-of-thought as customer-facing data.

## Artifact Delivery

Every research outcome is organized as a review-aware Artifact rather than an untraceable file. The Delivery Center communicates whether an outcome is a Draft, in Review, Approved, or Delivered, alongside its purpose, supporting Evidence, and next action.

## Organizational Knowledge Growth

Validated work can become reusable Workspace knowledge: prior Missions, approved Evidence, review decisions, and delivered Artifacts remain connected to the context in which they were authorized. This gives a research team continuity without claiming hidden memory or access beyond its Workspace.

## FDE Solution Value

For an FDE discussion, ResearchOS demonstrates how an enterprise customer can move from a concrete business problem to a governed research workflow:

| Customer need | ResearchOS response |
| --- | --- |
| Research material is scattered | A Mission organizes the question and authorized context. |
| Sources are hard to trust | Evidence stays traceable and requires validation. |
| Experts need decision control | Human Review is explicit before consequential delivery. |
| Useful work is not retained | Approved outcomes become Workspace-scoped organizational knowledge. |

## Five-Minute Demonstration

1. Start on **Home** and introduce the AI Research Employee.
2. Open **Solution Showcase** to frame the customer challenge and governance model.
3. Open a Golden Demo **Mission** to show the goal, current focus, and work journal.
4. Show the supporting **Evidence** and explain the validation boundary.
5. Use a Reviewer session to demonstrate a real **Human Review** decision when one is available.
6. Close in **Deliveries** and the **Workspace** to connect the outcome to reusable team knowledge.

Do not simulate approval or describe candidate sources as validated Evidence. If a prerequisite is absent, the correct demonstration is the product's real paused state and the next required human action.
