# Software workaround demonstrated on first A9-sticker RF2

2026-11-21. The user retained both failed chips without erasure, marked them A9,
and inserted the first for experiments. No adapter changes or external components
were used. Production pinned MiniPro executable/configuration remain unchanged.

## Result

**Route A9 (DIP24 pin 22, T48 ZIF38) through the T48 VCC/GND power matrix,
with its normal digital driver configured as input, and request VCC=5.18 V.**
The measured internal VCC rail was about 5.08–5.09 V reading and 5.13–5.14 V
programming. VCCIO can remain at the normal measured 3.25 V. Read pin 21 stays
on VCC; programming VPP and nominal 50 ms pulse remain the existing values.

Power routes are disconnected before opposite routes are enabled, with OE
disabled while changing A9. The tested minimal writer uses 2 ms setup delays,
a hard single-address/one-pulse limit, preservation checks against the intended
baseline, and a repeated initial read. This is a bench workaround for this
specimen, not a default production algorithm or a qualification of all RF2s.

Five individually addressed bytes were programmed and verified independently:

| Address | Final value | A9 partner | Partner value |
|---|---|---|---|
| 0270 | FD | 0070 | FE (written separately afterward) |
| 0070 | FE | 0270 | FD (preserved) |
| 0670 | F7 | 0470 | FB (written separately afterward) |
| 0470 | FB | 0670 | F7 (preserved) |
| 0290 | FB | 0090 | FF (preserved) |

Each successful pulse had a matching writer full readback and two fresh full
reads with exactly the single requested change. The last write used default
VCCIO and short setup delays. Final alternating normal/workaround/normal/
workaround reads reproduce the alias in normal mode and recover the same
qualified full dump in workaround mode. All operations reported outputs off.

## Isolation of necessary read settings

Two reads per mode on the distinguishing pairs gave:

| Mode | VCC request | A9 drive | VCCIO request | Result |
|---|---|---|---|---|
| 0 | 5.0 | digital | default | mirrors |
| 1 | 5.0 | digital | 3.45 | mirrors |
| 5 | 5.0 | VCC/GND rails | default | mirrors |
| 6 | 5.18 | digital | 3.45 | mirrors |
| 12 | 5.18 | VCC/GND rails | 3.45 | independent |
| 14 | 5.18 | VCC/GND rails | default | independent |
| 15 | 5.0 | VCC/GND rails | 3.45 | mirrors |

This supports a voltage/drive-margin explanation, but is not a measurement of
loaded A9 voltage at the chip leg. Raising VCC also raises the rail-driven A9
high level, so these tests do not isolate chip supply from A9 input threshold.
Digital sense reported A9 low/high correctly even in failing modes, demonstrating
why programmer digital feedback alone could not establish sufficient margin.

OE gating, 1 ms read delays, CE cycling, descending and interleaved address
orders, rewriting all digital outputs, A9-high startup, and all-address/control
rail-driven reads at the original VCC setting did not fix the alias.

## Important reinterpretation of earlier results

Several upper-half cells previously read as copies of their lower partners.
The workaround reads 0210, 0230, 0310 and 0610 as FF while their lower partners
retain FC, F9, EF and F7. These differences are repeatable; treating all such
differences as random errors was premature. The normal reader also hid the
successful 0270-only write until its lower partner was programmed.

Thus earlier mirrored readbacks do not prove both physical cells were written.
At least a read-addressing failure is now demonstrated by switching reader
modes without programming in between. The original experiment manifests remain
unaltered and retain the observations made with their respective algorithms.

## Failed/intermediate experiments preserved

- A9 rail routing at the old VCC setting wrote a pulse at 0250. Normal reads
  reported FE at 0050/0250. One writer full read also showed DF at 03A0, absent
  from all subsequent repeated reads; its cause remains unresolved.
- First combined-settings attempt used a normal-mode baseline. Its generic
  scan selected existing 0201 rather than requested 0270, reporting old FF /
  target 4F. Subsequent standard reads showed no persistent change. This was
  not counted as a successful fresh-address experiment.
- An added address restriction and baseline guard then rejected a normal-mode
  target with no pulse. Using the repeated workaround-mode baseline allowed
  the controlled 0270 pulse and the subsequent independent writes.
- A completed pulse, successful target verification and shutdown are recorded
  separately. Experimental status observed is not a successful image burn.

## Code, checks and reproduction

Sources are retained beside raw manifests, logs, targets and full readbacks.
They derive from pinned MiniPro bench commit 0841ac8b658db74ec9c59070217a0c44fdaba629.
Executables remain under local sessions/20261121-a9-software, hashes in manifests.
The original mode 0–4 source is preserved separately to match its original hash.

- read-ablation.c mode 14: minimal successful read-only path.
- minimal-writer.c: tested write path, compiled with TEST_ADDRESS=0x0290 and
  TEST_VALUE=0xFB. Intentionally refuses other test targets and repeated writes.
- address-guarded-writer.c: earlier successful combined path, including higher
  VCCIO and 20 ms setup delays; compiled separately for each selected address.
- run-controlled-probe.py: serial lock, repeated baseline and fresh verification.
- mock-rails.c: host-only pin model resolves rail-driven address inputs and
  checks input direction, no overlapping VCC/GND routes, pulse and cleanup.
  Successful one-pulse tests passed. Baseline mismatch and wrong target tests
  both aborted with zero pulses and clean shutdown (guard-tests.json).

Compile against the pinned MiniPro src/*.o except main.o, using -Isrc and the
pkg-config libusb-1.0/zlib linker flags. Do not replace the pinned backend with
these experimental binaries. Read-only executable invocation is:

    read-ablation --serial EXPECTED_SERIAL OUTPUT.bin 14

The writer requires a complete target based on a repeated workaround-mode
read, never a normal-mode mirrored dump. The compile-time address restriction
and preserved-byte checks intentionally prevent unattended full-image use.

## Documentation reviewed

- [XGecu T48/T76 user guide](https://manuals.plus/m/bccf664b61e08fc868066f087f4ac84059a2d3900eaccbd0566c3ed91e8c458e.pdf), manufacturer-authored mirror: no RF2/A9-specific recipe found. The USB recommendation is at least 4.90 V; our programming ADC briefly reported around 4.79–4.81 V even in successful tests. That remains a supply-quality observation, not an isolated cause.
- [MiniPro bitbang implementation author](https://gitlab.com/DavidGriffith/minipro/-/merge_requests/248): separate VCCIO/VCC/VPP controls. Pinned local t48.c supplied the exact voltage tables and routing maps used here.
- [RadioKot first-hand T48 report](https://www.radiokot.ru/forum/viewtopic.php?start=40&t=197995): diode from pin 24 to 21 addresses false-FF reads, not a documented A9 fix. Our explicit reader already powers pin 21 from VCC.
- [RF2 supplier reference](https://static.chipdip.ru/lib/818/DOC054818967.pdf): address input high 2.4 V through supply voltage; supply range 4.75–5.25 V. The tested rail settings remain within that range by internal ADC; no chip-leg measurement was made.

## Scope

Confirmed on the first A9-sticker specimen, with independent pairs in both A10
regions and a final simplified write. Second chip, full-ROM programming,
retention and operation in a Robotron mainboard remain untested. Final qualified
contents have 13 non-FF bytes and 2035 FF bytes; the normal reader reports a
different 16-byte non-FF mirrored view. Preserve the qualified dump and the
chip for further diagnostics.
