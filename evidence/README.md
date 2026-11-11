# Qualification and provenance

The [2026-11-11 integration record](20261111-integration/manifest.json) covers
clean dependency builds, 21 shared workflow tests, six RF2 state-machine
scenarios, regressions for option parsing, output-cache invalidation and PROM buffers
(under AddressSanitizer), and DOSRAVI's 4 execution-boundary
and 10 CLI tests. Simulated writes do not exercise real rails or pulse timing.

No chip was programmed during repository migration. A fresh real T48 verify
was attempted. Both the new shared reader and the preserved working binary
read all zeros; contact testing then failed on every non-ground pin, indicating
an empty/disconnected socket. The verify was rejected. A contact preflight was
added to the RF2 tool and tested on the same hardware: it rejects before power.
A fresh positive verification awaits confirmed chip insertion/contact.
This is not a regression pass against a presently readable programmed chip.

Previous physical qualification remains at its immutable locations:

- [RF2/T48 W4 burn and fresh readbacks](https://github.com/ddanila/willem-v30/tree/ff2a7c3/programming/t48-rf2-w4-20261111).
- [Fujitsu 2732A W4 programming](https://github.com/ddanila/willem-v30/tree/ff2a7c3/programming/robotron-w4-20261111).
- [AMD 2732A Kaypro V3 programming](https://github.com/ddanila/willem-v30/tree/ff2a7c3/programming/kaypro-v3-20261111).

Only relevant logs and summaries are imported here. Original source histories,
firmware artifacts, readbacks, and inventory links remain intact. Matching
all-zero/all-FF diagnostic captures are not added to the firmware dumps repo.
