# Migration and maintenance

This is an additive migration. Existing DOS commands, repositories, records,
and inventory links remain usable. The shared CLI calls DOSRAVI's generic
`run` operation; it reuses CRC-based upload skipping, persistent execution IDs,
stdout retrieval and transport logging. There is no copied serial protocol.
Existing DOSRAVI `willem-read`, `willem-write` and sweep commands remain available;
moving their qualification-specific logic is deferred until equivalent shared
coverage is established.

MiniPro changes live in our fork's `bench` branch. The original dependency was
whaslbeck/minipro at cfe2171ca1b23399558b8d2a603a2ac3fa3faf5d. The fork keeps that
history, including contact-test provenance, and splits our general fixes from
experimental RF2 support. Do not push to the original author or David Griffith's
upstream without an explicit request. The original successful checkout at
`minipro-t48` remains a comparison baseline; fresh builds use the lock file.

The central repository invokes GPL MiniPro and Willem as separate executables;
DOSRAVI remains its own MIT-licensed transport project. It does not redistribute
vendor firmware, Windows executables, or proprietary databases from Xgpro.

New session data defaults to ignored `sessions/`. Promote a reviewed evidence
summary, relevant logs and hashes into `evidence/` when warranted. Firmware
preservation goes to `dumps`, not this repository, and all-FF captures are not
archival firmware. Inventory records should link to the evidence and identify
the actual chip/label; don't silently substitute a newer ROM or double an image.

Dependency updates are deliberate: update one pinned revision, rebuild, run the
relevant tests and compare read-only behavior where hardware is available.
Keep physical qualifications per chip/profile. Do not turn experimental support
into a broad compatibility claim because compilation or simulations pass.

Deferred work: isolate the exact native T48/RF2 read defect; qualify additional
RF2 specimens; migrate other writer families only with their original voltage
and verification requirements; optionally contribute the generic MiniPro fixes
upstream. GUI and firmware updates are outside this first release.
