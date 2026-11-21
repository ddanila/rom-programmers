# PC1715 CRT 1.1 A25.3 RF2 programming — 2026-11-21

The user inserted an RF2 and authorized flashing the corrected cycle ROM.
Two explicit-backend reads confirmed blank contents and passed contact checks.
A one-byte image-compatible probe at 0201h passed writer verification and two
fresh full reads, with no changes at other addresses. The remaining image
then completed with 1732 additional programming pulses. Writer verification
and two fresh full-chip reads matched the intended 2048-byte image.

- Firmware: [RAVI CRT 1.1 cycle boot](https://github.com/ddanila/ravi/blob/585ef34/firmware/robotron1715-crt/images/cycle/boot.bin).
- SHA-256: `9c8eb6afbee0f77ac72e6926519e6408149b3859a17ba5566e54eb10cf6f1dca`.
- Suggested label: **A25.3 vidtest 1.1**; application not yet confirmed.
- T48 backend: pinned explicit RF2 pin-control tool; native M2716 excluded.
- Shutdown: pin drivers reported reset/off.
- Full RF2 marking unrecorded. This burn does not constitute a physical machine boot test.

Session manifests and the raw full-program log are retained here; raw binary
readbacks remain in the local session directory recorded by the manifests.
The A25.1/A25.2 glyph ROM images are unchanged from CRT 1.0.
