# Second A9-sticker RF2: software workaround confirmed

2026-11-21. User inserted the second A9-marked RF2 and authorized testing.
No hardware modifications or UV erasure. Same minimal software workaround
as the first specimen: A9 on T48 VCC/GND routing with normal digital output
released, VCC request 5.18 V, default VCCIO, 2 ms setup delays, nominal 50 ms
programming pulse. Measured read VCC 5.10–5.11 V, programming VCC 5.13–5.16 V,
VCCIO 3.25 V, programming VPP 24.34–24.41 V. These are internal ADC readings.

Two initial normal reads returned 4F at 0001 and 0201. Two workaround reads
returned 4F only at 0001; 0201 and every other address were FF. This confirms
that the original mirrored dump did not establish two programmed cells.

Four explicit single-address writes were performed, in this order:

| Address | Value | Verified partner preservation |
|---|---|---|
| 0270 | FD | 0070 remains FF |
| 0070 | FE | 0270 remains FD |
| 0670 | F7 | 0470 remains FF |
| 0470 | FB | 0670 remains F7 |

Each stage used two matching fresh workaround reads as its baseline, a
compile-time address/value guard, full preserved-byte preflight, a repeated
internal pre-read, and a hard one-pulse limit. Each writer completed exactly
one pulse, verified its full target, and two fresh full reads matched exactly.
All other addresses remained unchanged. No retry or full-ROM write occurred.

Final normal/workaround/normal/workaround reads reproduce the normal reader's
mirrors (0270=FE, 0670=FB, 0201=4F), while each workaround read recovers the
correct full image (0270=FD, 0670=F7, 0201=FF). Thus the workaround now has
independent-pair read/write evidence on both A9-marked specimens, in both A10
regions. This does not yet qualify full-image programming, retention, or
mainboard operation. Production pinned backend remains unchanged.

Final workaround dump: 0001=4F, 0070=FE, 0270=FD, 0470=FB, 0670=F7;
all other 2043 bytes FF. Final SHA256: e418d133fff0a3b656b45ffdcb225be9804732549fdcd44fde3e786ecfaf1a37.
All operations reported pin drivers reset/off. Chip remains reserved for
future diagnostics without erasure.

Source is byte-identical to the first specimen's minimal-writer.c; compiled
separately with TEST_ADDRESS/TEST_VALUE for each row. The existing host-only
mock and guard checks cover this unchanged source. Raw logs, manifests,
source, runner, target images and readbacks are retained here; executable
hashes are in manifests and binaries remain in local sessions.
