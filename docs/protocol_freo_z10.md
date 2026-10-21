# Freo Z10 beta protocol

Version `0.11.0-beta.4` adds a deliberately isolated command profile for Freo
Z10 product keys `OlkUn3oUCu` and `tPQJmoIbEC`.

## Option B experiment (beta.4)

Only product `tPQJmoIbEC` in Vacuum mode (2) sends both pass-count fields 5
and 6, each set to the requested cycles. Both mode selectors remain 2. This
tests the reporter’s hypothesis; it does not establish vacuum-only semantics.
Modes 3–5, `OlkUn3oUCu`, YJCC012, Freo Mind, recall and response handling are
unchanged from beta.3. No physical robot was used for local regression tests.

In HACS use Redownload, show beta versions and select `v0.11.0-beta.4`, then
restart Home Assistant. Start one supervised whole-home Vacuum job, one cycle,
from the dock. Check that it continues beyond the prior 4–12 seconds **and only
vacuums**. Stop immediately if it begins mopping. Do not test other modes yet.
Report physical behavior, duration and any HA error/timeout, plus only redacted
route/completion lines. Never post credentials, device IDs or raw maps.
Rollback through HACS Redownload to `v0.10.1` and restart; beta.3 remains
available for comparison. Return-to-dock and Freo Mind are not fixed here.

## Start behavior

Manual cleaning modes 2–5 use `clean/start_clean`. The protobuf body carries:

- the current saved-map ID;
- the exact current room IDs;
- one `CleanParam` per room (mode, suction, mop humidity, and cycles);
- the selected task mode.

The integration waits for the matching response topic and requires Narwal's
field-1 `SUCCESS` result code. Publishing alone, a malformed response, and
explicit rejection codes are not reported as a successful start.

Freo Mind (mode 1) is not fixed by this beta and is expected not to start on the
reported `tPQJmoIbEC` robot. Its exact Z10 payload is not verified, so this beta
does not guess one. Runtime testing is limited to manual modes 2–5, beginning
with one whole-home vacuum task in mode 2.

## Map changes

When the map ID or room definition changes on the Z10 profile, cached templates
are invalidated. The integration performs a fresh activated `clean/plan/get`,
retries once if the Freo Mind plan is incomplete, and stores the new plans only
when every current room is covered. The YJCC012 map and template flow remains
unchanged. An incomplete old Z10 generation may remain useful for map display,
but is never used to start room cleaning.

## Isolation and rollback

The YJCC012 profile still uses its existing `clean/easy_clean/start` bytes. No
fallback sends both protocols. Unknown product IDs do not opt into the Z10
profile.

This implementation is a prerelease until it has been exercised on a physical
Freo Z10. Rollback target: `v0.10.1`.
