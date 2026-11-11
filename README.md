# ROM programmers

One bench command for T48 and Willem acquisition, programming, and independent
verification. Low-level signalling stays in pinned projects; this repository
owns profiles, orchestration, reproducible setup, and session evidence.

| Project | Responsibility |
| --- | --- |
| [ddanila/minipro, bench branch](https://github.com/ddanila/minipro/tree/bench) | T48 driver fixes, contact checking, experimental RF2 tool |
| [ddanila/willem-v30](https://github.com/ddanila/willem-v30) | DOS reader/writer, LPT signals, timing and emulation |
| [ddanila/dosravi](https://github.com/ddanila/dosravi) | DOS transport, upload caching and execution recovery |
| [ddanila/dumps](https://github.com/ddanila/dumps) | Preserved firmware acquisitions |
| [Vintage inventory](https://github.com/ddanila/vintage-computer-inventory) | Machines, chips, labels and installed firmware |

## Setup

Python 3.11+, Git, a C compiler, make, libusb/zlib development headers, bcc and
nasm are needed to build both backends. Bootstrap uses an isolated virtualenv
and never installs system packages or changes programmer firmware.

```sh
python3 tools/bootstrap.py --build --t48-serial YOUR_T48_SERIAL \
  --dos-port /dev/serial/by-id/YOUR_ADAPTER
python3 -m rom_programmers info
```

Sources are fetched at the exact revisions in `dependencies.lock.json` into
ignored `.tools/` directories. `bench.json` contains local paths, device
identity and generated executable hashes; it is not committed. If it already
exists, bootstrap writes `.tools/bench.generated.json` for review instead.
Optional `MINIPRO_LIBUSB_INCLUDE` supports locally extracted libusb headers.
Source-tree execution needs no installation of this package. For an installed
command use `python3 -m pip install .` in your environment.

See `config/bench.example.json` for the format. Paths resolve relative to the
configuration file, including its interpreter path. Keep generated binary
hashes: an unexpected reader/writer change is rejected before hardware access.
`program_vpp` documents the bench setting; it does not adjust Willem jumpers.

## Commands

```sh
# Setup information: no hardware access.
python3 -m rom_programmers info --profile t48-rf2

# Each acquisition performs two fresh reads and compares them.
python3 -m rom_programmers read --profile t48-rf2
python3 -m rom_programmers blank-check --profile t48-rf2
python3 -m rom_programmers verify --profile t48-rf2 --image W4.BIN

# Explicit programming, after checking the selected physical setup.
python3 -m rom_programmers program --profile t48-rf2 --image W4.BIN \
  --setup-confirmed
python3 -m rom_programmers program --profile willem-2732a-21v --image ROM4K.BIN \
  --setup-confirmed

# Explicit duplication; writes an adjacent transformation manifest.
python3 -m rom_programmers prepare-image --image W4.BIN --repeat 2 --output ROM4K.BIN
```

Use `--config FILE` and `--session DIRECTORY` to choose bench and evidence
locations. Existing session directories are never overwritten. Image sizes
must exactly match the profile; padding and repetition are never implicit.

Supported profiles:

- `t48-rf2`: experimental 2 KiB RF2 read/program via explicit pin control.
  Contact preflight, matching serial, per-byte verify and final fresh reads.
  The known-bad native M2716 read/verify path is never selected.
- `willem-2732a-21v`: 4 KiB read/program for qualified 21 V, 50 ms 2732A parts.
  The DOS writer requires an erased chip, checks for first-byte aliasing and
  performs full verification after a power cycle. Fixed LPT base 378h.
- `willem-2716-read`, `willem-2764-read`, `willem-27512-read`: established
  conservative read commands; no programming capability is inferred.

An all-FF capture is marked explicitly. Matching captures establish
repeatability; the manifest is not a claim of universal chip compatibility.
An empty/disconnected T48 socket fails the RF2 contact preflight.

## Sessions and recovery

`session.json` records the request, profile, configuration, tool hashes, exact
commands, step outcomes, source metadata, artifacts and shutdown reports.
A programming exit code alone is insufficient: successful sessions require
fresh full readbacks matching the intended image. `write_completed` is separate
from `status=verified`. Raw backend logs and DOSRAVI sub-sessions are retained.
`shutdown=reported-off` means the software reported shutdown, not an independent
voltage measurement. Exceptions retain an explicit unknown state when needed.

A per-connection lock prevents this CLI from operating the same bench twice
concurrently. It cannot lock out unrelated direct invocations of MiniPro or
DOS tools: do not run those at the same time.

To recover a failed/interrupted session, repeat the original command with
`--resume SESSION_DIRECTORY` instead of `--session`. The request, image,
configuration and tool hashes must match. Completed step output hashes are
checked. An uncertain DOSRAVI execution reuses its original persistent ID and
cached completion; binaries are uploaded only when remote size/CRC differ.
**DOSRAVI's cache does not survive a DOS agent restart.** Recovery of an
uncertain write therefore requires `--same-agent-session`, an explicit assertion
that the same agent is still running. If it restarted or you cannot establish
that fact, inspect/read the chip instead; this protocol cannot prove durable
write deduplication across reboot.
An uncertain direct T48 write is never automatically replayed. Read the chip
and inspect the session before starting a new programming operation.

The host does not kill a child merely because a wall-clock timeout elapsed:
a DOS execution might still be running. DOSRAVI owns its transport/execution
timeouts and recovery. The RF2 tool handles ordinary errors and interrupts,
but cannot provide a hardware pulse watchdog after USB loss or SIGKILL.

## Tests and qualification

```sh
python3 -m unittest discover -s tests -v
make -C .tools/minipro test-bench
```

The shared tests cover success, exact sizes, incorrect images, mismatched
reads, missing shutdown evidence, tool identity, exclusive access, interrupted
writes, upload caching, recovery without a second write, and artifact tampering.
Backend simulations are not physical electrical tests.

See [qualification evidence](evidence/README.md) and [migration notes](docs/migration.md).
The earlier successful RF2 burn and all historical acquisitions retain their
original URLs. No firmware update or reprogramming is part of this migration.
