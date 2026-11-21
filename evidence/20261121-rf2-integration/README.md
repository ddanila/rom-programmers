# RF2 default backend integration — 2026-11-21

User authorized enabling the A9 workaround for RF2 operations. The MiniPro
fork main commit is 3e89e0fac87c9da21ab912cce2787aa3eaee8d07; the shared
workflow dependency lock now points to it. Standard `t48-rf2` reads/writes
use A9 VCC/GND routing and requested VCC 5.18 V automatically. Generic
single-supply 2716 and 2732 reads retain their previous drive/supply behavior
through separate commands. The profile remains experimental.

The production writer adds two initial matching reads, full tracked-image
verification after the first pulse, and A9 partner verification after later
pulses. A mismatch stops without retry; actual failed readback is saved after
reset. Full-image host-model tests use nonperiodic data and injected addressing
faults; tests also cover first-pulse aliases on other bits, later partner
corruption, initial read instability and cleanup. All backend checks passed,
including the existing cache, pulse and buffer tests. Shared suite: 36 passed.

Backend CI passed: https://github.com/ddanila/minipro/actions/runs/44934440154

Local rebuild used the new T48-only bootstrap option, avoiding the absent DOS
compiler (an earlier all-backend build stopped on missing bcc after T48 tests
passed). Generated default bench.json contains the actual serial, new revision
and executable SHA256:

e6e074c2816c27c77e8ee7f0c759e661b6254e0ca23ebd6d30271a7693202d6c

The previous custom bench-pc003-read.json was left untouched and its old binary
and configuration archived locally. Use the generated default bench.json with
the new tool; old pinned executable hashes are intentionally not bypassed.

## Read-only live check

The integrated CLI passed its configuration/hash checks and invoked contact
preflight on the connected T48. Every non-ground pin failed contact, consistent
with an empty/disconnected socket. The backend reported Reset pin drivers: OK
and exited before normal chip power/read or any programming. The preserved
session is failed with shutdown unknown; the raw log supplies the reset report.
Do not reinterpret this as a successful RF2 read or image verification.

Earlier physical qualification remains the independent-byte experiments on
both A9-marked chips. No chip was programmed during integration. Full-image
physical programming, retention, and mainboard validation remain pending.
