# Programmer workflow maintenance

Run `python3 -m unittest discover -s tests -v` for shared workflow changes.
Hardware is never required by tests or CI. Preserve the dependency lock and
build from pinned sources with `tools/bootstrap.py`; low-level fixes belong
in the linked programmer project, not copied into this package.

The native T48 M2716 algorithm falsely read FF from the tested RF2. Use the
explicit RF2 backend with contact preflight. Never qualify erased state or a
successful burn using that native path. RF2 remains experimental per specimen.

Keep `write_completed`, `verified`, and unknown execution/shutdown states
separate. A DOSRAVI ID is deduplicated only within the same running agent;
never infer durable replay protection after a target restart. Keep image
transforms explicit and retain original image hashes and raw backend evidence.

Session data is local by default. Preserve firmware in the dumps repository and
chip labels in inventory; link reviewed programming evidence rather than moving
historical records. Do not operate hardware as part of a documentation change.
