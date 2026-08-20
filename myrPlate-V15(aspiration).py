# -*- coding: utf-8 -*-
"""
myrPlate V15-Asp Aspiration
-----------------------
Aspirates spent/supernatant media from myrPlate wells that already contain a
tissue construct cast with myrPlate_tissue_casting_8Ch1ml_Fast_V15.py, and
disposes the aspirate into a waste reservoir (block C3) before each tip is
discarded.

This version keeps the original V3 task (per-well aspiration -> dispose to
C3 -> fresh tip every column) but replaces the single-corner aspiration point
with the accurate elliptical sweep route and absolute flow-rate control
introduced in V15, so the pipette follows the same well-wall-hugging path
used during casting and avoids the tissue sitting in the well center.
"""
from opentrons import protocol_api
import numpy as np
from opentrons.types import Point

metadata = {
    "protocolName": "myrPlate V15-Asp Aspiration",
    "description": "Aspirates spent media from myrPlate wells (post V15 cast) along an elliptical route, disposing into block C3 before tip replacement",
    "author": "HGH"
}
requirements = {"robotType": "Flex", "apiLevel": "2.18"}


def add_parameters(parameters: protocol_api.Parameters):
    parameters.add_int(
        variable_name="aspirate_location_Index",
        display_name="Start well/column A1-A6",
        description="First myrPlate column to aspirate; remaining columns up to A6 are processed too",
        default=1,
        minimum=1,
        maximum=6,
    )

    parameters.add_float(
        variable_name="aspirate_rate_uLs",
        display_name="Aspirate rate (µL/s, absolute)",
        description="Absolute aspirate flow rate for removing spent media",
        default=40,
        minimum=5,
        maximum=200,
        unit="µL/s"
    )

    parameters.add_float(
        variable_name="dispense_rate_uLs",
        display_name="Dispense rate (µL/s, absolute)",
        description="Absolute dispense/blow-out flow rate used at the disposal block",
        default=60,
        minimum=5,
        maximum=200,
        unit="µL/s"
    )

    parameters.add_float(
        variable_name="z_height",
        display_name="Z height",
        description="Height above well bottom for aspiration points (mm) - clear of media, above the cast tissue",
        default=1.5,
        minimum=0.00,
        maximum=15.00,
        unit="mm"
    )

    parameters.add_float(
        variable_name="travel_height_mm",
        display_name="Travel height",
        description="Clearance when moving over the plate before descending into a well",
        default=15,
        minimum=5,
        maximum=40,
        unit="mm"
    )

    parameters.add_int(
        variable_name="num_points",
        display_name="Ellipse points/well",
        description="Number of points along the ellipse to aspirate from per well",
        default=8,
        minimum=1,
        maximum=32,
    )

    parameters.add_float(
        variable_name="overlap",
        display_name="Overlap ratio",
        description="0 = single pass around the ellipse, 1 = full second sweep",
        default=0,
        minimum=0,
        maximum=10,
    )

    parameters.add_float(
        variable_name="volume_per_well",
        display_name="Volume per well",
        description="Total volume to aspirate from each well",
        default=400,
        minimum=100,
        maximum=485,
        unit="µL"
    )

    parameters.add_float(
        variable_name="ellipse_x_radius",
        display_name="Ellipse X radius",
        description="Semi-axis (mm) along the well's long axis - matches the V15 casting route by default",
        default=5.5,
        minimum=2.0,
        maximum=6.5,
        unit="mm"
    )

    parameters.add_float(
        variable_name="ellipse_y_radius",
        display_name="Ellipse Y radius",
        description="Semi-axis (mm) along the well's short axis - matches the V15 casting route by default",
        default=2.85,
        minimum=1.0,
        maximum=4.2,
        unit="mm"
    )


def generate_ellipse_points(num_points, overlap, x_radius, y_radius):
    """Same accurate ellipse formulation used in V15 casting - reused here so
    aspiration follows the identical path the tissue was cast along."""
    base_t = np.linspace(np.pi / 2, 2 * np.pi + np.pi / 2, num_points, endpoint=False)
    total_sweeps = 1 + int(overlap)
    t = np.concatenate([base_t + (i * (2 * np.pi / num_points)) for i in range(total_sweeps)])
    updated_num_points = len(t)
    x = x_radius * np.cos(t)
    y = y_radius * np.sin(t)
    return list(zip(x, y)), updated_num_points


def run(protocol: protocol_api.ProtocolContext):
    p = protocol.params

    aspirate_volume = p.volume_per_well
    z_height = p.z_height
    travel_height = p.travel_height_mm
    wait_time_aspirate = 1  # settle delay after aspirating, as in V3

    # Load labware and instruments (same slots as V3)
    tip_rack_right = protocol.load_labware("opentrons_flex_96_tiprack_1000ul", "C2")
    pipette_right = protocol.load_instrument("flex_8channel_1000", "right", [tip_rack_right])

    plate = protocol.load_labware("myrplate_48_wellplate_800ul", "D3")           # myrPlate location
    disposal_block = protocol.load_labware("nest_1_reservoir_195ml", "C3")       # Disposal location
    trash = protocol.load_trash_bin("A3")

    # Absolute flow-rate control (V15 style) instead of the old /1000 scaled rate
    pipette_right.flow_rate.aspirate = p.aspirate_rate_uLs
    pipette_right.flow_rate.dispense = p.dispense_rate_uLs

    ellipse_points, updated_num_points = generate_ellipse_points(
        p.num_points, p.overlap, p.ellipse_x_radius, p.ellipse_y_radius
    )

    start_column = p.aspirate_location_Index
    selected_columns = list(range(start_column, 7))  # e.g. start=3 -> [3, 4, 5, 6]

    disposal_well = disposal_block["A1"]

    def aspirate_and_dispose(columns):
        """Sweep the accurate elliptical route in each well to aspirate spent
        media, dispose into C3, then discard the tip before the next column."""
        for col in columns:
            well = plate[f"A{col}"]

            pipette_right.pick_up_tip()
            pipette_right.move_to(well.top(z=travel_height))

            vol_per_point = aspirate_volume / updated_num_points
            total_aspirated = 0

            for i, (x, y) in enumerate(ellipse_points):
                position = well.bottom(z=z_height).move(Point(x, y, 0))
                pipette_right.move_to(position, speed=50)
                pipette_right.aspirate(vol_per_point)
                total_aspirated += vol_per_point

                if total_aspirated >= aspirate_volume:
                    break

            protocol.delay(seconds=wait_time_aspirate)

            # Move up and out before heading to the disposal block
            pipette_right.move_to(well.top(z=travel_height))

            pipette_right.move_to(disposal_well.top(z=3))
            pipette_right.blow_out()

            pipette_right.drop_tip()

    aspirate_and_dispose(selected_columns)
