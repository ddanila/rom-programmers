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

## Positive M2716 read check — 2026-11-11

After the owner installed PC001's M2716 (suffix uncertain, reported IFI/1F1),
`t48-2716-read` passed contact checking and two complete 2048-byte reads. Both
match the public S550 image byte-for-byte: SHA-256
`37e58472a049e1785c3521ec6b23c2d269d93fa5fede696dc7bd72eabb4af031`,
CRC32 `0a96c754`, embedded identifier `111715W070887`. Outputs were reset after
each read; no programming was performed. This qualifies the shared read path
on this specimen, not RF2 programming or all 2716 variants.

[PC001 inventory record](https://github.com/ddanila/vintage-computer-inventory/tree/main/items/PC001-robotron-1715m/evidence/20261111-m2716-s550-t48).
The already-public firmware is retained only in the local session, not copied
into the dumps repository or this evidence directory.

## Positive PC003 2732 read check — 2026-11-11

PC003's sticker-covered, owner-identified 2732 passed contact checks and two
4096-byte reads through `t48-2732-read`. CRC32 `4918fb91` and SHA-1
`cd9f45cc3546bcaad7254b92c5d501c40e2ef0b2` match MAME's `81-232.u47`
boot ROM for Kaypro boards 81-240. Both address halves are distinct. No write
was performed; both reads reported reset. The exact underlying chip model
remains unknown. Known firmware is kept locally, not added to dumps.

[PC003 inventory record](https://github.com/ddanila/vintage-computer-inventory/tree/main/items/PC003-kaypro-2/evidence/20261111-2732-81-232-t48).
