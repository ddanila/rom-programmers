# PC1715 CRT 1.2 A25.3 RF2 programming — 2026-11-21

The user inserted an RF2 and authorized flashing the corrected cycle ROM.
Two explicit-backend reads confirmed blank contents and passed contact checks.
A one-byte image-compatible probe at 0201h passed writer verification and two
fresh full reads, with no changes at other addresses. The remaining image
then completed with 1720 additional programming pulses. Writer verification
and two fresh full-chip reads matched the intended 2048-byte image.

- Firmware: [RAVI CRT 1.2 cycle boot](https://github.com/ddanila/ravi/blob/7e9f6fa/firmware/robotron1715-crt/images/cycle/boot.bin).
- SHA-256: `8621b28cd8e4c4433d52b4161022e50ff36603d99571a06ea9ce3974f8024e82`.
- Suggested label: **A25.3 vidtest 1.2**; application not yet confirmed.
- T48 backend: pinned explicit RF2 pin-control tool; native M2716 excluded.
- Shutdown: pin drivers reported reset/off.
- Full RF2 marking unrecorded. Physical machine boot with this chip remains pending.

Session manifests and the raw full-program log are retained here; raw binary
readbacks remain in the local session directory recorded by the manifests.
The diagnostic A25.1/A25.2 glyph images are unchanged from CRT 1.0/1.1.
Version 1.2 removes the invalid CRT-status polling that stalled version 1.1.
