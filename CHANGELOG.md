# Changelog

Releases are tagged `vX.Y.Z`. Every release builds from an empty NetBox in one run and passes `verify.py`.

## 0.5.3

- Documentation only: the print plugin this dataset is used with was renamed from netbox-trace-print to
  **netbox-tracepath-plugin** (0.7.0); the README and the design notes use the new name and the new repository
  address. The data is unchanged. Entries below this one use the old name.

## 0.5.2

- An **Authors** section in the README: co-authored by JP and Claude (Claude Sonnet 5.5), the companies are
  fictional, and the hardware sources are named (NetBox Community Device Type Library, the generic patch panel
  defined here, Corning's ALTOS cable family, real places for the geography).
- The README says how the dataset relates to the plugin releases. The data is unchanged.

## 0.5.1

- Documentation only: design notes for the trunks, colours, strands and fiber circuits, a releases section and the
  link to netbox-trace-print. The data is unchanged.

## 0.5.0

- **Strands on panel ports.** Strands 2n-1 and 2n of every 48-fiber trunk are landed on port n of the panel at
  each end (netbox-fms), so the tube, fiber and colour of a pair can be read off.
- **FMS fiber circuits** `NF-FC-0001` to `-0005` (2 strands, two paths from one duplex port, 1550 nm, with
  end-to-end loss), one per trunk pair in use, each from the line panel port of one muxponder to the other's.
- `verify.py`: 52 checks.

## 0.4.0

- Trunk cables are **green** inside a site and **blue** between sites.

## 0.3.0

- **24-pair trunks.** Every panel-to-panel rear connection is one 24-pair (48-fiber) cable between two trunk
  panels (24 duplex LC front ports, one 24-position rear port), no longer 24 discrete cables.
- Baltic Retail Group has servers at both ends of `NF-BRG-0001`.
- Fuller fiber-plant records: serial number, install date, installer and route marks.

## 0.2.0

- The build rewritten as seven layered, reconciling scripts (`01_organization` to `07_finalize`, plus
  `verify.py` and `build.py`) that describe the final state directly and can be replayed on an empty NetBox.

## 0.1.0

- The baseline: 22 numbered phase scripts, kept in git and in `archive/` as history.
