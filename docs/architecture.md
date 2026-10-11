# ResearchOS Architecture

The canonical architecture reference is
[Architecture.md](architecture/Architecture.md). This compatibility entry is
kept for automated release checks and existing public links.

## Single execution gateway

`AIWorkerRuntime` is the single execution gateway for enterprise Mission work.
The public path is:

`Identity → Workspace → Mission → AIWorkerRuntime → Review → Artifact`

Legacy compatibility routes are not part of the ordinary user workflow.
