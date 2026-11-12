# IntentWeft worked example

**Verdict:** Needs action  
**Mode:** Review  
**Scope:** The synthetic analytics function and its product brief. Static inspection only; no network request was executed. The `.invalid` endpoint is deliberately nonfunctional.

## Active requirements

| ID | Requirement | Source | Status |
| --- | --- | --- | --- |
| R1 | Keep precise device coordinates on the device | `product-brief.md`, Data promise | unmet in the inspected function |
| R2 | Limit analytics to event name and public region code | `product-brief.md`, Analytics | unmet in the inspected function |

## F1: Analytics payload includes precise coordinates

**Severity:** High, because the inspected path contradicts an explicit data promise.  
**Confidence:** Confirmed by static inspection of the request construction. Production transmission remains unverified.  
**Status:** Open.

**Evidence:** `analytics.ts`, `trackMapOpen()` constructs a POST request containing `latitude` and `longitude`. The brief explicitly limits the permitted fields. Permission to access location does not amend that requirement.

**Trigger:** A caller invokes `trackMapOpen()` with a device position. The function constructs a request whose body includes that position. Caller reachability and production endpoint configuration are outside the supplied example.

**Impact:** If used as written against a working analytics service, the implementation sends data outside the documented allowed payload. This example establishes a code/specification mismatch, not an observed production incident or a legal violation.

**Action:** Remove precise coordinate fields from the event, then remove the unused position parameter and update callers. Check the region value is a public region code as required. Review the actual analytics transport for additional location enrichment before closing R1.

**Verification:** Add or run an appropriate payload check proving that only the permitted fields are sent. Inspect outgoing traffic in a controlled environment when the real integration is available.

## Checks and unknowns

| Check | Result | Limit |
| --- | --- | --- |
| Compare request keys with the brief | failed | Static payload construction only |
| Inspect production analytics traffic | not-run | No deployed application or working endpoint supplied |

Unknown: whether a real application calls this function, and whether a real transport adds fields. Resolve by inspecting callers and the actual integration. Neither uncertainty removes the demonstrated local mismatch.

## Handoff

Fix the payload and callers, then refresh the source anchors and verification evidence. Keep R1 and R2 active until the permitted data flow is established. No risk acceptance or requirement supersession was supplied.
