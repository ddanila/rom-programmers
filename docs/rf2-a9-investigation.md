# RF2 A9 failures and the diode workaround — 2026-11-20

Two RF2 specimens selected for the plain-PC1715 CRT boot image failed at the
same address with identical subsequent dumps. The new evidence establishes
an A9 alias in the installed chip/programmer combination. It does **not**
establish whether the chip, its contact, the T48 drive voltage/timing or another
physical condition causes the alias. No additional hardware commands or burns
were performed during this retrospective investigation.

The two glyph-ROM specimens passed fresh full readbacks. Their images distinguish
229 and 556 of the 1024 unique A9 address pairs respectively. Their successes
therefore cannot be explained by an A9-symmetric target image. They are useful
controls against an unconditional software A9 omission, but not proof of
universal RF2 compatibility or of independent physical voltage margins.

## Exact failure reconstruction

The target is ravi's cycle `boot.bin`, SHA-256
`84998d3390e3ded5e9160bbc2cf17cb4f5f96bb168f44544b761817ceae6b0ff`.
Both failed specimens were initially read as all FF by the explicit RF2 reader.
An all-FF image cannot establish address independence.

- Address 0001h is first programmed to 3Eh.
- Address 0200h has target FFh, so the writer skips it using its initial read.
- At 0201h, the target is CCh. If A9 is ignored, this pulse accesses 0001h.
- EPROM programming can clear bits: **3Eh AND CCh = 0Ch**.
- The immediate verification therefore reads 0Ch, stops, and reports reset.
- Two new readbacks per specimen agree. Both complete dumps have the same hash:
  `12d373d8eda380d47d79db44e457815a11155a1acc07536ead72f2df3b366cf1`.
- The complete dumps mirror across address XOR 0200h. This is not merely a
  wrong byte at the verification boundary; earlier contents have been altered.

The pinned `rf2-direct.c` was executed against its host-only mock with initially
blank memory and an injected A9 alias on reads and writes. It failed after 507
pulses at exactly 0201h, and its entire 2048-byte modeled dump matched **both
physical dumps exactly**. With a healthy address model the same actual writer
and image completed successfully (1734 pulses). This proves that address aliasing
is sufficient to explain the observations; it does not locate its electrical
cause. No physical programmer is opened by the mock.

See [analysis.json](../evidence/20261120-rf2-a9/analysis.json) for hashes, actual
pulse counts, ADC ranges, local raw-session locations and simulation results.
The [mock-only patch](../evidence/20261120-rf2-a9/mock-a9.patch) applies to the
pinned fork's `tests/mock-t48.c`; it is not a production-driver modification.

## What our fork actually fixes

The currently installed driver matches MiniPro fork `bench` revision
`0841ac8b658db74ec9c59070217a0c44fdaba629` (also the remote branch head checked
for this investigation). Executable SHA-256:
`ddb8e506f9c6374b262b1f4efa87bf0c8a7c551eafaec8163b434dfb4d9bd730`.

The [2026-11-11 T48 investigation](https://github.com/ddanila/willem-v30/blob/ff2a7c3/programming/t48-rf2-w4-20261111/README.md)
found a different problem: the native M2716 algorithm returned false FF data
even after successful programming. Explicit pin control made those reads work.
The fork fixes pull-down output-cache invalidation and 40-versus-56-element
buffer misuse, and uses a separate RF2 writer. It explicitly connects chip
pins 24 and 21 to VCC during reads, and disconnects read VPP before selecting
programming VPP. It programs with nominal 50 ms positive CE pulses and checks
internal VCC/VPP ADC values. Those measurements are not actual chip-pin probes.

The previous writeup explicitly states that this workaround did not explain the
Willem A9 failures. Calling it an established general RF2 solution was too strong.

Source inspection confirms address bit 9 is assigned to DIP24 pin 22 (T48 ZIF
contact 38 in this tool's placement), with 11 address bits, not a truncated
9-bit counter. Direction changes invalidate output-level caches. No simple
missing-A9 assignment was found. The mock bypasses the USB/firmware/analog layer,
so its healthy result cannot clear those layers of suspicion. The address-output
rail reported in the new logs is about 3.24–3.25 V; the writer neither measures
loaded A9 directly nor checks its actual level at the chip.

## The two diode discussions are different

**T48 VCC-to-VPP diode.** A first-hand RadioKot report by Ed_Kl dated 2026-04-04
in [“Чтение с КС573РФ2,” page 3](https://radiokot.ru/forum/viewtopic.php?t=197995&start=40)
says adding a diode between pins 24 and 21, with **anode at 24 and cathode at
21**, allowed reading and writing on T48. The quoted symptom is native M2716
reads returning all FF. The report was available in the search index; direct
page retrieval timed out during this investigation.

Electrically, that orientation can feed read-mode VPP from VCC while blocking
programming VPP from flowing back into VCC. This is an interpretation of the
circuit, not a measurement of our programmer. Our direct reader already commands
pin 21 to the 5 V rail, addressing the same supply requirement without that
external diode. It has not been demonstrated that the added diode would cure
our A9 alias or that our pin-21 transitions are correct under every load.

Do not substitute a wire between pins 24 and 21 during programming: they carry
different supply voltages then. Nor should a diode be assumed compliant solely
because it helps another specimen: its forward drop and the actual pin-21
voltage must be checked against the chip specification.

**Willem D9.** Our [original-program comparison](https://github.com/ddanila/willem-v30/blob/ff2a7c3/docs/original-2716.md)
links the [PCB5.0 modification author](https://jopl.eu/willeprog_adapters.php).
That is a different diode: D9 is in the Willem A9 path, with a socket-side
pull-down. The author bypassed it for excessive drop during **3.3 V operation**.
It is a relevant signal-level lead, not evidence that a bypass is required on
our 5 V setup or that it applies to the T48.

The old Willem experiments used different scan orders, delays and the original
Windows program's address sequencing without eliminating the mirror. A known
nonblank control distinguished A9. One problematic read supply was measured
around 4.30 V, but high-VPP verification still mirrored. The old investigation
therefore also ended with loaded A9 measurement as the unresolved step.

## Protection gap in the T48 writer

The Willem writer acquired a first-programmed-byte alias preflight: it checked
other addresses before continuing the image. The T48 RF2 writer has no analogous
check. It checks blank/compatible contents once, then verifies only the current
address after each pulse. It does not notice an alias while each write still
reads back its intended value, and it does not detect changes to earlier bytes
until they cause a current-byte failure or the final full verification.

Its generated RF2 test image mostly repeats every 256 bytes and there is no
RF2 address-alias fault injection in the committed tests. The separate 2732
read test covers all address bits, but does not qualify RF2 programming.

A software improvement should check the entire image against a tracked expected
state after the first pulse, including all one-bit partner addresses, before
continuing. Test both A9 and other aliases, read-only versus write-only aliases,
and high-address transitions. For preprogrammed chips, some aliases can be
masked by existing equal data; no static all-FF preflight alone can prove a
blank chip has independent cells. This guard limits damage; it does not repair
an electrical addressing fault. No production driver or pinned dependency was
changed during this investigation.

## Next discriminating bench measurements

Before another burn, obtain the complete markings and package/suffix of the two
failed chips and the successful controls. The current chip-to-label history
is not sufficient to establish that these are the same type/batch.

On the already-programmed failed specimen, with programming VPP off:

1. Compare reads at 0000h and 0200h, while measuring **chip pin 22** relative to
   **pin 12 ground**, under chip load. Verify a low/high transition at the leg,
   not only at the programmer's unloaded socket or an internal ADC rail.
2. Measure **pins 24 and 21** during those reads. Repeat using a known working
   RF2 control with distinguishing contents, without writing anything.
3. If static levels are valid, capture A9, CE/OE and pin-21 supply transitions
   with a scope; a digital readback of a commanded output is not a calibrated
   voltage or timing measurement. Establish read-address independence before
   authorizing any further programming experiments.

The [RF2-family sheet](https://static.chipdip.ru/lib/818/DOC054818967.pdf)
uses one-based address names: pin 22 is called **A10**, corresponding to our
zero-based **A9 / 0200h**. It gives read supply ranges 4.75–5.25 V, address-input
high at least 2.4 V, low at most 0.4 V, and programming input 23.5–25.5 V.
Do not confuse the Willem ZIF26 position with T48 ZIF38; chip-pin numbering is
the common reference. The lower-capacity RF21/RF22 variants disconnect pin 19,
so a normal lower-capacity variant is not automatically an explanation for a
missing pin-22 address bit.

## Follow-up: new blank specimen, one-pulse probe

The user inserted a new blank RF2 for testing. Two fresh explicit-backend reads
were identical and all FF. With a hard maximum of one changed byte, the pinned
writer programmed FEh at 0201h in one pulse (reported host window 50.972 ms).
Contact preflight passed. Immediate verification and the writer's full readback
passed; two subsequent fresh full-chip reads agreed exactly with the target.
Only 0201h contains FEh; all other addresses, including 0001h, remain FFh.
The programmer reported pin drivers reset after writing and reading.

This specimen therefore did not exhibit the prior A9 mirror in this test.
A single cleared bit does not qualify every address/data pattern, sustained
programming, retention, or electrical margins. No second pulse or full-image
burn was performed. The full chip marking is still unrecorded. The chip can
be retained for further compatible programming experiments; restoring the
cleared bit requires UV erasure.

See [single-byte probe evidence](../evidence/20261120-rf2-a9/single-byte-probe.json).
Raw logs and binary readbacks remain in the local session directory.

## Follow-up: successful staged A25.3 boot-ROM burn

The user inserted another blank RF2 and authorized a staged full boot-image
burn. Two initial full reads were stable and all FF. A one-pulse probe wrote
the actual boot-image byte CCh at 0201h; the writer and two fresh full reads
confirmed that only that address changed. All other addresses remained FFh.

The remaining boot image was then programmed successfully with 1733 additional
pulses. The writer's full verification and two fresh independent reads matched
SHA-256 `84998d3390e3ded5e9160bbc2cf17cb4f5f96bb168f44544b761817ceae6b0ff`
exactly. Pin drivers were reported reset/off. No retries were needed.

This specimen is verified for the cycle A25.3 boot image. The suggested label
is `A25.3vidtest` (not yet confirmed applied by the user). This does not establish
why the earlier specimens aliased, nor constitute a physical PC1715 boot test.
See [staged-burn evidence](../evidence/20261120-rf2-a9/a25-3-staged-success.json);
raw programming logs and readbacks remain in the local session directory.
