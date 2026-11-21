# CRT 1.3 RF2 probe failure — 2026-11-21

Replacement chip passed two explicit RF2 backend blank reads and contact checks.
The single-byte probe requested 4Fh at 0201h, with a limit of one changed byte.
Immediate byte verification passed, but full writer readback found an unexpected
4Fh at 0001h as well. The writer exited 3, reporting changed=1 remaining=1 and
pin drivers reset. Two fresh full reads reproduced both programmed addresses;
all other bytes remained FFh. No full-ROM programming was attempted.

The intended CRT 1.3 image requires 3Eh at 0001h, which cannot be obtained from
4Fh by further EPROM programming. This specimen needs UV erasure before reuse
for this image. The address difference is A9 (0200h); this suggests address
aliasing or unintended programming, but does not establish whether the cause
is the chip, contact, adapter or programmer waveform.

Firmware: RAVI commit 1d17b64, firmware/robotron1715-crt/images/cycle/boot.bin.
Target SHA256: fd4afbddec93baf878ac7111149cf16168b69d0628643a46f81bc97929a07abd.
Fresh read SHA256: 325a208eccc3bf862ec5ac3a0d740534ab245e358b68ce0625a485f500746118.

The inspection session status verifies repeatability of the reads only;
matches_probe=false explicitly records that programming did not verify.
The failed write session retains its original state; writer shutdown is
established by the raw log and later reads report shutdown=reported-off.
Raw binary readbacks remain in the local sessions referenced by manifests.

User disposition: preserve this specimen without UV erasure for future
diagnostics. Both failed specimens are being retained with their current
contents (4Fh at 0001h and 0201h; all other bytes FFh).
