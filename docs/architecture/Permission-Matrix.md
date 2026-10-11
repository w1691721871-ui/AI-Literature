# Permission Matrix

Permissions are enforced from the authenticated server-side session and the active Workspace membership. Client-provided user or workspace identifiers are not authority.

| Role | Organization / Workspace | Missions | Evidence / Knowledge | Artifacts | Computer Skill | Reviews |
| --- | --- | --- | --- | --- | --- | --- |
| OWNER | Full organization access | Create, view, execute, approve | View, approve | View, download, release | Controlled execution | Approve |
| ADMIN | Workspace administration | Create, view, execute, approve | View, approve | View, download, release | Controlled execution | Approve |
| MANAGER | Project administration | Create, view, execute, approve within workspace | View | View, download | Controlled execution | Approve in scope |
| MEMBER | No administration | Create, view, execute | View | View, download when released | Controlled execution | Submit for review |
| REVIEWER | No administration | View | View | View, download, review | No execution | Approve / reject / request changes |
| VIEWER | Read-only | View | View | View released artifacts | No execution | No approval |

Artifact release, high-risk controlled computer actions and reviewable decisions remain human-gated regardless of role.
