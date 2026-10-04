# ResearchOS v2.0 Release Candidate

## Product position

ResearchOS is an evidence-driven AI Research Workspace. It turns an authorized
research goal into a reviewable Mission, traceable Evidence, human-reviewed
insights, and a governed delivery artifact. It is not an autonomous publishing
or external-action system.

## Five-minute demonstration

1. Sign in or choose **Try Demo**. Demo access is an isolated MEMBER-scoped
   Workspace and cannot open administration surfaces.
2. On Home, enter: `Analyze future research opportunities in low-carbon
   building materials.` Choose **Start Mission**.
3. Open the Mission. The AI Worker shows its authorized context, plan and
   user-readable activity. It can only use selected Workspace records.
4. In the controlled Computer workflow, public research metadata is discovered
   read-only. Every result is a **Candidate**, not Evidence.
5. Review candidate Evidence. Approved Evidence can support research insights
   and a Research Brief draft. A human still reviews the resulting artifact
   before release.

The demo must not be presented as a live external-literature claim unless its
sources were actually retrieved and approved in that Workspace.

## Security and governance

- Identity, Workspace membership and RBAC are enforced server-side.
- Mission, Evidence, Memory, Artifact, approval and collaboration records are
  Workspace-bound.
- Public source discovery accepts HTTPS metadata only; it does not log in,
  submit forms, write externally or store page bodies.
- Prompts, chain-of-thought, credentials and raw source bodies are excluded
  from public timeline, context and audit projections.
- Important changes stop at a human approval boundary. An Artifact is not a
  formal delivery until its review state is approved.

## Deployment handoff

Use [Deployment.md](Deployment.md) for Render/Vercel deployment and
[Permission-Matrix.md](Permission-Matrix.md) for role boundaries. Configure
secrets only in the deployment provider; copy `.env.example` for local setup
and do not commit `.env`, SQLite state, FAISS data or generated artifacts.

## Release acceptance

Before a public demo, confirm:

- `GET /health` is healthy and `/researchos/diagnostics` reflects the actual
  deployed corpus state.
- Login and Demo Session restore a Workspace identity before any protected
  request.
- Demo access receives `403` for administrative organization endpoints.
- A Mission can be created from a natural-language goal, reaches a visible
  review boundary, and no result is marked as approved without a reviewer.
- Browser source candidates remain candidates until the existing Evidence
  validation workflow approves them.
