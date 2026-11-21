# CRT 1.3 RF2 second replacement probe failure — 2026-11-21

User identified the preceding specimen as one of the previous failures and
inserted another RF2, authorizing flashing. Two explicit RF2 backend reads
confirmed all FFh and contact checks passed.

A single-byte probe requested 4Fh at 0201h, limited to one programming pulse.
Immediate verification passed, but full writer readback also returned 4Fh at
0001h. Writer exited 3 with changed=1 remaining=1 and pin drivers reset.
Two fresh reads confirmed the exact same contents; all other bytes were FFh.
No full-image write was attempted. Outputs reported off after the fresh reads.

This repeats the preceding specimen's A9-separated address symptom. It does
not isolate chip defects from contact, adapter or programmer waveform issues.
Further blank-chip attempts should wait for investigation of the shared setup.
The target requires 3Eh at 0001h, incompatible with the observed 4Fh without
UV erasure. The chip is not a successfully programmed diagnostic ROM.

Firmware: RAVI commit 1d17b64, firmware/robotron1715-crt/images/cycle/boot.bin.
Target SHA256: fd4afbddec93baf878ac7111149cf16168b69d0628643a46f81bc97929a07abd.
Readback SHA256: 325a208eccc3bf862ec5ac3a0d740534ab245e358b68ce0625a485f500746118.

Inspection status verified means matching repeated reads, not successful
programming; matches_probe=false records the mismatch. Original failed-write
state and raw log are preserved. Binary readbacks remain in local sessions.

User disposition: preserve this specimen without UV erasure for future
diagnostics. Both failed specimens are being retained with their current
contents (4Fh at 0001h and 0201h; all other bytes FFh).
