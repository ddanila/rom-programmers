# First A9-sticker RF2: controlled address experiments

2026-11-21. User marked both failed RF2 specimens A9, inserted the first,
and explicitly authorized experiments using unused addresses. This physical
label/order does not identify which of the two earlier session specimens it is.
Baseline two full reads match the previous dump: 4F at 0001/0201, FF elsewhere.

Used the unchanged pinned explicit RF2 backend, normal supply settings and
nominal 50 ms pulse. Each experiment supplied the current image with exactly
one requested byte change and a hard one-byte limit. No automatic retries.
Each writer exited 3 because the mirrored partner differed from its target;
all reported one completed pulse and reset drivers. Two subsequent full reads
per experiment matched the writer readback exactly. The wrapper status
observed records an experiment result, not successful target-image programming.

| Step | Requested address/value | Observed changed addresses | New value |
|---|---|---|---|
| 1 | 0010 FE | 0010, 0210 | FE |
| 2 | 0210 FC | 0010, 0210 | FC |
| 3 | 0230 FD | 0030, 0230 | FD |
| 4 | 0030 F9 | 0030, 0230 | F9 |
| 5 | 0410 F7 | 0410, 0610 | F7 |
| 6 | 0110 EF | 0110, 0310 | EF |

No changes outside each requested address and its XOR 0200 partner. Original
0001/0201 bytes remain 4F. Six pulses consumed eight previously FF readback
addresses; final dump has 2038 FF bytes. All logs, targets and binary readbacks
are included. Final shutdown reported off. No UV erasure or full-ROM write.

## Interpretation

The A9-pair symptom repeats with low-first and high-first writes, different
data bits, and in both A10 regions. The sampled A8 and A10 regions retain
distinct data. This rules out a problem restricted to address 0201 or its
first-write ordering; it does not qualify all other address lines or timing.

These observations do not distinguish an aliased read path, aliased write
selection, two cells programmed together, or a combination. Nor do they locate
the fault in the chip versus its contacts or electrical interface. Separate
successful specimens on the same backend remain useful controls, but do not
prove loaded address levels are valid for this chip.

Next discriminating check: measure chip pin 22 (A9, called A10 in one-based
RF2 documentation) relative to pin 12 under load while selecting each pair;
compare with a working specimen. Check pins 21/24 supply levels and scope
address/CE/OE transitions if static levels are correct. No voltage increases,
diodes, timing modifications or alternate native read algorithms were used.
