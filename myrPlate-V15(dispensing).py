# -*- coding: utf-8 -*-
"""
myrPlate V15-Disp Dispensing
------------------------
Dispenses fresh media into myrPlate wells that already contain a tissue
construct cast with myrPlate_tissue_casting_8Ch1ml_Fast_V15.py (e.g. for a
media exchange 2 hr after casting).

This version keeps the original V1 task (aspirate from a 12-well reservoir,
dispense across all six myrPlate columns in three two-column batches) but
replaces the rectangular dispense path with the accurate elliptical route and
absolute flow-rate control introduced in V15, so fresh media is delivered
along the same well-wall-hugging path used during casting instead of an
approximate rectangle - keeping the pipette clear of the tissue in the well
center.
"""
from opentrons import protocol_api
import numpy as np
from opentrons.types import Point

metadata = {
    "protocolName": "myrPlate V15-Disp Dispensing",
    "description": "Dispenses fresh media into myrPlate wells (post V15 cast) along an elliptical route, in three two-column batches",
    "author": "HGH"
}
requirements = {"robotType": "Flex", "apiLevel": "2.18"}


def add_parameters(parameters: protocol_api.Parameters):
    parameters.add_int(
        variable_name="aspirate_location_Index",
        display_name="Reservoir well# A1-A12",
        description="Media well# in the nest_12_reservoir_15ml to aspirate fresh media from",
        default=1,
        minimum=1,
        maximum=12,
    )

    parameters.add_float(
        variable_name="aspirate_rate_uLs",
        display_name="Aspirate rate (µL/s, absolute)",
        description="Absolute aspirate flow rate when drawing fresh media from the reservoir",
        default=80,
        minimum=5,
        maximum=200,
        unit="µL/s"
    )

    parameters.add_float(
        variable_name="dispense_rate_uLs",
        display_name="Dispense rate (µL/s, absolute)",
        description="Absolute dispense flow rate into the myrPlate wells",
        default=65,
        minimum=5,
        maximum=200,
        unit="µL/s"
    )

    parameters.add_float(
        variable_name="z_height",
        display_name="Z height",
        description="Height above well bottom for dispense points (mm)",
        default=5,
        minimum=0.00,
        maximum=15.00,
        unit="mm"
    )

    parameters.add_float(
        variable_name="travel_height_mm",
        display_name="Travel height",
        description="Clearance when moving over the plate before descending into a well",
        default=20,
        minimum=5,
        maximum=40,
        unit="mm"
    )

    parameters.add_int(
        variable_name="num_points",
        display_name="Ellipse points/well",
        description="Number of points along the ellipse to dispense at per well",
        default=6,
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
        description="Total volume to dispense at each well",
        default=485,
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
    """Same accurate ellipse formulation used in V15 casting, reused here so
    the media feed follows the identical path the tissue was cast along."""
    base_t = np.linspace(np.pi / 2, 2 * np.pi + np.pi / 2, num_points, endpoint=False)
    total_sweeps = 1 + int(overlap)
    t = np.concatenate([base_t + (i * (2 * np.pi / num_points)) for i in range(total_sweeps)])
    updated_num_points = len(t)
    x = x_radius * np.cos(t)
    y = y_radius * np.sin(t)
    return list(zip(x, y)), updated_num_points


def run(protocol: protocol_api.ProtocolContext):
    p = protocol.params

    # Volume calculations (kept from V1: one aspiration feeds two columns,
    # 1.03x buffer, since a full media volume can't fit three columns in a
    # single 1000 uL tip the way V15's smaller casting volume can)
    dispense_volume_per_well = p.volume_per_well
    aspirate_volume = dispense_volume_per_well * 2 * 1.03

    z_height = p.z_height
    travel_height = p.travel_height_mm

    wait_time_aspirate = 4          # settle delay after aspirating, from V1
    wait_time_first_dispense = 1
    wait_time_halfway_dispense = 0.5

    # Load labware and instruments (same slots as V1)
    tip_rack_right = protocol.load_labware("opentrons_flex_96_tiprack_1000ul", "C2")
    pipette_right = protocol.load_instrument("flex_8channel_1000", "right", [tip_rack_right])

    plate = protocol.load_labware("myrplate_48_wellplate_800ul", "D3")
    media_rack = protocol.load_labware("nest_12_reservoir_15ml", "D2")
    trash = protocol.load_trash_bin("A3")

    # Absolute flow-rate control (V15 style) instead of the old /1000 scaled rate
    pipette_right.flow_rate.aspirate = p.aspirate_rate_uLs
    pipette_right.flow_rate.dispense = p.dispense_rate_uLs

    # Define and load liquid, same as V1
    Media = protocol.define_liquid(
        name="EHMM",
        description="Engineered Heart Myocardium Media solution for feeding myrPlates",
        display_color="#0000FF"
    )
    aspiration_location = f"A{p.aspirate_location_Index}"
    media_rack[aspiration_location].load_liquid(Media, volume=10000)

    ellipse_points, updated_num_points = generate_ellipse_points(
        p.num_points, p.overlap, p.ellipse_x_radius, p.ellipse_y_radius
    )

    # Same batch structure as V1 - covers all six columns in three passes
    first_batch = ["1", "2"]
    second_batch = ["3", "4"]
    third_batch = ["5", "6"]

    def aspirate_and_dispense(columns):
        """Aspirate fresh media once, then dispense along the elliptical
        route into each column in this batch (8 wells per column via the
        8-channel pipette)."""
        pipette_right.pick_up_tip()

        aspirate_well = media_rack[aspiration_location]
        pipette_right.move_to(aspirate_well.bottom(z=0.2))
        pipette_right.aspirate(aspirate_volume, aspirate_well)
        protocol.delay(seconds=wait_time_aspirate)

        for col in columns:
            well = plate[f"A{col}"]

            pipette_right.move_to(well.top(z=travel_height))

            total_dispensed = 0
            for i, (x, y) in enumerate(ellipse_points):
                target_position = well.bottom(z=z_height).move(Point(x, y, 0))
                pipette_right.move_to(target_position, speed=50)

                pipette_right.dispense(dispense_volume_per_well / updated_num_points)
                total_dispensed += dispense_volume_per_well / updated_num_points

                if i == 0:
                    protocol.delay(seconds=wait_time_first_dispense)
                elif i == len(ellipse_points) // 2:
                    protocol.delay(seconds=wait_time_halfway_dispense)

                if total_dispensed >= dispense_volume_per_well:
                    break

            pipette_right.move_to(well.top(z=travel_height))

        pipette_right.drop_tip()

    aspirate_and_dispense(first_batch)
    aspirate_and_dispense(second_batch)
    aspirate_and_dispense(third_batch)
