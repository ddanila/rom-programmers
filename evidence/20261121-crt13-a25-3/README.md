# PC1715 CRT 1.3 A25.3 RF2 programming — 2026-11-21

The user inserted another RF2 and authorized flashing. Two explicit RF2
backend reads confirmed blank contents and passed contact checks. The
single-byte probe at 0201h (4Fh) passed writer verification and two fresh
full reads, with no unintended changes. Full-image programming then completed;
writer verification and two fresh full-chip reads matched the intended image.

- Firmware: [RAVI CRT 1.3 cycle boot](https://github.com/ddanila/ravi/blob/1d17b64/firmware/robotron1715-crt/images/cycle/boot.bin).
- SHA256: fd4afbddec93baf878ac7111149cf16168b69d0628643a46f81bc97929a07abd.
- Suggested label: A25.3 vidtest 1.3; label application not yet confirmed.
- Shutdown: pin drivers reported off. Physical machine boot remains pending.
- Explicit RF2 backend used; native M2716 excluded.

Version 1.3 corrects the CRT underline parameter and shows each pattern title
for about one second, then the unobstructed pattern for about ten seconds.
A25.1 and A25.2 glyph ROM images are unchanged. Prior two failed specimens
remain reserved without erasure for future diagnostics, per user instruction.
This successful specimen does not establish the cause of their failures.

Reviewed manifests and raw programming log are retained here; binary readbacks
remain in the local session paths referenced by the manifests.
