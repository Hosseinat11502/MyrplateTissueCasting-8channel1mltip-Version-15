# myrPlate V15-Asp / V15-Disp Protocols

Companion Opentrons Flex protocols for `myrPlate_tissue_casting_8Ch1ml_Fast_V15.py`.
Use these on a myrPlate that has already been cast with V15 to perform a media
exchange: aspirate spent media, then feed fresh media.

## Files

| File | Purpose |
|---|---|
| `myrPlate_V15-Asp_aspiration.py` | Aspirates spent media from myrPlate wells, disposes into block C3, fresh tip per column |
| `myrPlate_V15-Disp_dispensing.py` | Aspirates fresh media from a 12-well reservoir and dispenses into myrPlate wells in three two-column batches |

## What changed vs. the earlier V3 / V1 protocols

Both scripts keep the original task and deck slots from their V3/V1
predecessors, but adopt V15's movement and flow-rate conventions:

- **Elliptical route**: replaces V3's single fixed aspiration point and V1's
  approximate rectangle path with the same accurate ellipse equation used by
  V15 during casting (`x = x_radius·cos(t)`, `y = y_radius·sin(t)`, default
  5.5 / 2.85 mm semi-axes), so both scripts stay on the same well-wall-hugging
  path the tissue was cast along and avoid the construct in the well center.
- **Absolute flow rates**: `aspirate_rate_uLs` / `dispense_rate_uLs` set
  directly on `pipette.flow_rate`, replacing the old `.../1000` scaled rate
  parameter.
- **Travel height**: explicit `travel_height_mm` parameter for clearance
  moves over the plate, matching V15.
- **Tunable ellipse radii**: `ellipse_x_radius` / `ellipse_y_radius` exposed
  as parameters (still defaulting to V15's values) in case a wider/narrower
  sweep is needed away from the tissue.

Task-specific behavior preserved from the originals:

- Aspiration keeps V3's fresh-tip-per-column and disposal-into-C3 behavior.
- Dispensing keeps V1's three two-column batches (rather than V15's
  three-column-per-tip grouping), since a full media volume (up to 485 µL/well)
  does not fit three columns in a single 1000 µL tip the way V15's smaller
  193 µL casting volume does.
- Dispensing keeps V1's bubble-prevention wait times (4 s / 1 s / 0.5 s)
  rather than V15's shorter ones, since those were tuned specifically for
  media (a lower-viscosity liquid than the collagen mastermix).

## Requirements

- Opentrons Flex, API level 2.18
- `flex_8channel_1000` pipette, right mount
- `opentrons_flex_96_tiprack_1000ul` in slot C2
- `myrplate_48_wellplate_800ul` in slot D3
- Aspiration: `nest_1_reservoir_195ml` (waste) in slot C3, trash bin in A3
- Dispensing: `nest_12_reservoir_15ml` (media) in slot D2, trash bin in A3

## Typical workflow

1. Cast tissue with `myrPlate_tissue_casting_8Ch1ml_Fast_V15.py`.
2. ~2 hr later, run `myrPlate_V15-Asp_aspiration.py` to remove spent media.
3. Run `myrPlate_V15-Disp_dispensing.py` to feed fresh media.
4. Repeat aspirate/dispense on your normal media-exchange schedule.
