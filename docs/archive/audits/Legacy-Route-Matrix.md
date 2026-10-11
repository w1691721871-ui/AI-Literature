# Legacy Route Matrix

## Scope

`app/routes/researchos.py` contains the historical product API surface. It is
retained for migration and administrator diagnostics only. Every route under
`/researchos` now has a router-wide Session requirement and OWNER/ADMIN
compatibility gate. It is not part of the enterprise user path.

| Route family | Historical purpose | Current consumer | Session / RBAC | Enterprise replacement | Visibility |
|---|---|---|---|---|---|
| `/researchos/agents`, `/overview`, `/agent-monitor`, `/diagnostics`, `/system-status` | Agent/runtime status | Historical dashboard | Session + ADMIN/OWNER | `/api/runtime/*`, `/api/audit/*` | Admin compatibility |
| `/researchos/ai-worker/*`, `/research-worker/*`, `/autonomous-runs/*`, `/operator/*` | Earlier AI and runtime variants | Historical AI workspace | Session + ADMIN/OWNER | `/api/runtime/missions/{id}` | Admin compatibility |
| `/researchos/computer/*`, `/computer/use/*`, `/computer/runtime/*`, `/computer/autonomous/*` | Earlier Computer execution variants | Historical Computer Studio | Session + ADMIN/OWNER | `/api/computer-missions/*` and Mission runtime | Admin compatibility |
| `/researchos/workspaces/*`, `/tasks/*`, `/workflows/*`, `/research-workspaces/*` | Earlier workspace/task models | Historical workspace views | Session + ADMIN/OWNER | `/api/missions/*`, `/api/workspace/context` | Admin compatibility |
| `/researchos/projects/*`, `/actions/*`, `/decisions/*`, `/outcomes/*`, `/evidence` | Earlier research planning data | Historical research console | Session + ADMIN/OWNER | Mission, Evidence, Review and Artifact APIs | Admin compatibility |
| `/researchos/organizations/*`, `/solutions*`, `/solution-*`, `/client-delivery/*` | Earlier enterprise/FDE surfaces | Historical admin and demo views | Session + ADMIN/OWNER | `/api/organizations/*`, `/api/artifacts/*`, `/api/approvals/*` | Admin compatibility |
| `/researchos/product/*`, `/bi`, `/value-assessment`, `/lab-profile/*` | Showcase and product analytics | Historical home/demo views | Session + ADMIN/OWNER | Workspace Home, Demo Center and Admin Console | Admin compatibility |

## Enterprise user path

```text
Identity → Workspace → Mission → AIWorkerRuntime → Review → Artifact
```

Normal Workspace initialization loads only Session-bound Workspace overview,
team collaboration, Missions, Knowledge and unified Context. It does not call
the legacy `/researchos` surface.

## Migration rule

New frontend code must not add a `/researchos` request. A compatibility feature
must be exposed only from `/admin/compatibility` and only after the current
Session has been verified as OWNER or ADMIN.
