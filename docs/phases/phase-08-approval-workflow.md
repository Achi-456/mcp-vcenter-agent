# Phase 8 - Approval Workflow

## Goal

Add human approval workflow for non-read-only operations without enabling
destructive execution by default.

## Planned Work

- Implement approval request lifecycle.
- Add dry-run preview storage.
- Add UI approval cards.
- Allow `approval_required` tools only after explicit approval.
- Keep `destructive` tools disabled until a separate production safety review.

## Boundaries

- No mass operations.
- No datastore delete/unmount.
- No host reboot/shutdown.
- No VM delete until destructive policy is explicitly revised.

## Acceptance Criteria

- Approval-required requests create pending approval records.
- Rejected requests remain blocked.
- Approved low-risk operations are audited with before/after metadata.

