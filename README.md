# myrPlate ECT Casting — Opentrons Flex Protocol (V15, 8-Channel, Half-Plate)

Automated dispensing of fibroblast-laden collagen master mix into 24 of the 48
wells of a **myrPlate** (`myrplate_48_wellplate_800ul`) using an Opentrons
**Flex** with an **8-channel** 1000 µL pipette. A single tip strip aspirates
once from a 12-well reservoir and dispenses simultaneously into all 8 wells of
a column at a time, across 3 columns — filling half the plate in one run.

📄 **Preprint / manuscript:** `[DOI or bioRxiv link — will be added here once available]`
🎥 **Video of a live run:** `[filename — add once uploaded]` (5× sped up)
🔗 **Related project:** [myrPlate EHT Casting (V20, 1-channel)](https://github.com/Hosseinat11502/MyrplateTissueCasting-1channel1mltip-Version-20) — see comparison below.

---

## What this protocol does

- Aspirates once, with an 8-channel pipette, from a single well of a
  `nest_12_reservoir_15ml` at deck slot D2 (`aspirate_location_Index`,
  default well 5).
- Dispenses into **3 columns** of the myrPlate (`column_preference`: columns
  1–3 or 4–6), one column at a time. Because the pipette is 8-channel, each
  dispense fills all 8 wells (rows A–H) of that column **simultaneously** —
  so 3 dispense passes cover 24 wells (half the 48-well plate).
- Each of the 8 tips traces the same small ellipse path per well (as in the
  single-channel V20 protocol) to reduce bubble/edge artifacts, with a
  reverse pre-wet step before touching the plate.
- One tip strip, one aspirate, three dispense passes — no re-tipping, no
  pausing for refills mid-run.

## Application: Engineered Connective Tissue (ECT)

This run casts **human fibroblasts suspended in a collagen type I master mix
in DMEM-based culture medium**, following the 48-well casting-plate protocol
of Santos et al. (2021), *Fibroblast Derived Human Engineered Connective
Tissue for Screening Applications*, *J. Vis. Exp.* (174), e62700,
[doi:10.3791/62700](https://doi.org/10.3791/62700) — the same JoVE method
referenced at <https://www.jove.com/t/62700>.

## How this compares to the companion V20 (EHT) project

| | **This repo — V15** | [V20 (EHT)](https://github.com/Hosseinat11502/MyrplateTissueCasting-1channel1mltip-Version-20) |
|---|---|---|
| Tissue type | Engineered connective tissue (ECT) | Engineered heart tissue (EHT) |
| Cell type | Fibroblasts/stromal cells | Co-culture of fibroblasts and cardiomyocytes |
| Master mix | Collagen type I + fibroblasts | Collagen type I + cardiomyocytes+fibroblasts |
| Culture medium | DMEM-based (fibroblast growth medium) | EHMM (engineered heart muscle medium) |
| Culture protocol reference | Santos et al. 2021, *J. Vis. Exp.*, [doi:10.3791/62700](https://doi.org/10.3791/62700) | Tiburcy et al. 2017, *Circulation* 135:1832–1847, [doi:10.1161/CIRCULATIONAHA.116.024145](https://doi.org/10.1161/CIRCULATIONAHA.116.024145); also used in Goodarzi Hosseinabadi, [arXiv:2508.19854](https://arxiv.org/abs/2508.19854) |
| Pipette | 8-channel 1000 µL | 1-channel 1000 µL |
| Source labware | 12-well reservoir (D2) | 96-well deep-well plate (D2) |
| Wells filled per run | 24 (half the plate: 3 columns × 8 rows) | 4 (one column segment) |
| Tips used per run | 1 (8-channel strip) | 1 |
| Relative throughput | ~6× more wells per tip/run | baseline |

Filling by whole columns with an 8-channel head — instead of one well at a
time — is what gives V15 its speed advantage, making it suited to scaling up
tissue production when a larger batch of one construct type is needed.

## Requirements

- Opentrons **Flex**, API level `2.18`
- `flex_8channel_1000` pipette (right mount)
- `opentrons_flex_96_tiprack_1000ul` at **C2**
- `myrplate_48_wellplate_800ul` at **D3**
- `nest_12_reservoir_15ml` at **D2**
- Trash bin at **A3**

## Runtime parameters (set in the Opentrons App before each run)

| Parameter | Default | Description |
|---|---|---|
| `aspirate_location_Index` | 5 | Reservoir well to aspirate from (1 = A1 … 12 = A12) |
| `aspirate_rate_uLs` | 20 µL/s | Absolute aspirate flow rate |
| `dispense_rate_uLs` | 60 µL/s | Absolute dispense flow rate |
| `z_height` | 0.5 mm | Dispense height from well bottom |
| `travel_height_mm` | 15 mm | Clearance height over the plate |
| `pre_wet_volume` | 20 µL | Excess volume aspirated per tip for anti-bubble compensation (see below) |
| `num_points` | 10 | Ellipse points per well, before overlap sweeps |
| `overlap` | 2 | Extra full ellipse sweeps (0 = single pass) |
| `volume_per_well` | 193 µL | Dispense volume per myrPlate well |
| `column_preference` | 123 | `123` → fill columns 1–3; `456` → fill columns 4–6 |

## Anti-bubble design: what `pre_wet_volume` actually does here

Because this protocol uses an **8-channel** pipette, `pre_wet_volume` is a
**per-tip** quantity. At the default of 20 µL, all 8 tips together aspirate
`8 × 20 = 160 µL` more master mix than the 24 wells strictly need.

That excess is used in two stages:
1. **Reverse pre-wet:** immediately after aspiration, half of it
   (`pre_wet_volume / 2` = 10 µL per tip) is dispensed straight back into the
   reservoir. This clears any trapped air from the tip and normalizes the
   meniscus before the tip ever touches the myrPlate.
2. **Capillary compensation:** the remaining 10 µL per tip stays in the tip
   as a buffer. During the many-point elliptical dispense path, a small
   amount of master mix is continuously lost to capillary wetting on the
   tip's outer wall — without this reserve, that loss would show up as a
   short-dispensed, air-gapped final well. The reserve absorbs that loss
   invisibly, so every well still receives its full, bubble-free
   `volume_per_well` amount.

Net effect: **bubble-free, uniformly filled wells** with a consistent
meniscus across all 24 wells, which matters for producing tissues of uniform
thickness after collagen polymerization.

## Run time

The demonstration video linked above runs at **5× playback speed**. The
underlying real-time run — filling all 24 wells (half the 48-well myrPlate)
in a single pass — took **~2 minutes 40 seconds**. At 5× speed, the video
itself runs approximately 32 seconds.

## Usage

1. Load labware in the slots above; load the reservoir well with enough
   master mix for `volume_per_well × 3 + pre_wet_volume` per channel (≥ 10 mL
   total is comfortable for the full 15 mL reservoir well).
2. Upload `myrPlate_tissue_casting_8Ch1ml_Fast_V15-ECTsFinal.py` in the
   Opentrons App.
3. Set `aspirate_location_Index` and `column_preference` (and any other
   parameters) before starting.
4. Run.

## Repo contents

```
myrPlate_tissue_casting_8Ch1ml_Fast_V15-ECTsFinal.py   # protocol
README.md
LICENSE
CITATION.cff
```
(Add the demonstration video file to this list once uploaded, and update the
link at the top of this README.)

## Citation

If you use this protocol, please cite this repository and the accompanying preprint once posted (see `CITATION.cff`).

## License

MIT.
