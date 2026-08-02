# -*- coding: utf-8 -*-

from opentrons import protocol_api
import numpy as np
from opentrons.types import Point

metadata = {
    "protocolName": "myrPlate cast v15",
    "description": "Dispenses into columns of myrPlate",
    "author": "HGH"
}
requirements = {"robotType": "Flex", "apiLevel": "2.18"}

def add_parameters(parameters: protocol_api.Parameters):
    parameters.add_int(
        variable_name="aspirate_location_Index",
        display_name="Aspiration well index",
        description="Well in 12-reservoir to aspirate from (1=A1, 12=A12)",
        default=5,
        minimum=1,
        maximum=12,
    )

    parameters.add_float(
        variable_name="aspirate_rate_uLs",
        display_name="Aspirate rate(µL/s,absolute)",
        description="Absolute aspirate flow rate for viscous collageد",
        default=20,
        minimum=5,
        maximum=200,
        unit="µL/s"
    )

    parameters.add_float(
        variable_name="dispense_rate_uLs",
        display_name="Dispense rate(µL/s,absolute)",
        description="Absolute dispense flow rate for pre-wet return and dispensing.",
        default=60,
        minimum=5,
        maximum=200,
        unit="µL/s"
    )

    parameters.add_float(
        variable_name="z_height",
        display_name="Z height",
        description="Height from well bottom for dispensing (mm)",
        default=0.5,
        minimum=0.00,
        maximum=15.00,
        unit="mm"
    )

    parameters.add_float(
        variable_name="travel_height_mm",
        display_name="Travel height",
        description="Clearance when moving over plate before descending",
        default=15,
        minimum=5,
        maximum=40,
        unit="mm"
    )

    parameters.add_float(
        variable_name="pre_wet_volume",
        display_name="Pre-wet vol(µL)",
        description="Extra volume aspirated immediately returned to clear trapped air",
        default=20,
        minimum=0,
        maximum=50,
        unit="µL"
    )

    parameters.add_int(
        variable_name="num_points",
        display_name="Ellipse points/well",
        description="How many points on ellipse per well",
        default=10,
        minimum=1,
        maximum=32,
    )

    parameters.add_float(
        variable_name="overlap",
        display_name="Overlap ratio",
        description="0 = no overlap, 1 = full second sweep",
        default=2,
        minimum=0,
        maximum=10,
    )

    parameters.add_float(
        variable_name="volume_per_well",
        display_name="Volume per well",
        description="Total volume to dispense per well (µL)",
        default=193,
        minimum=33,
        maximum=310,
        unit="µL"
    )

    parameters.add_float(
        variable_name="column_preference",
        display_name="odd or even",
        description="Select to dispense in col# 1,2,3 or 4,5,6",
        default=123,
        minimum=123,
        maximum=456,
        unit="column#"
    )

def index_to_well(index):
    column = index  # 1 to 12
    return f"A{column}"

def generate_ellipse_points(num_points, overlap):
    base_t = np.linspace(np.pi / 2, 2 * np.pi + np.pi / 2, num_points, endpoint=False)
    total_sweeps = 1 + int(overlap)
    t = np.concatenate([base_t + (i * (2 * np.pi / num_points)) for i in range(total_sweeps)])
    updated_num_points = len(t)
    x = 5.5 * np.cos(t)
    y = 2.85 * np.sin(t)
    return list(zip(x, y)), updated_num_points

def run(protocol: protocol_api.ProtocolContext):
    p = protocol.params

    # Volume calculations
    total_dispense_volume = p.volume_per_well * 3  # enough for 3 columns
    aspirate_volume = total_dispense_volume / 1  # 0% buffer for residual/loss
    dispense_volume_per_column = aspirate_volume * 1 / 3

    aspiration_location = index_to_well(p.aspirate_location_Index)
    ellipse_points, updated_num_points = generate_ellipse_points(p.num_points, p.overlap)

    # Wait times (lengthened slightly for a viscous fluid to equilibrate)
    wait_time_aspirate = 2
    wait_time_prewet_return = 1
    wait_time_first_dispense = 0.5
    wait_time_halfway_dispense = 0.5

    # Load labware
    tip_rack = protocol.load_labware("opentrons_flex_96_tiprack_1000ul", "C2")
    pipette = protocol.load_instrument("flex_8channel_1000", "right", tip_racks=[tip_rack])
    plate = protocol.load_labware("myrplate_48_wellplate_800ul", "D3")
    media_rack = protocol.load_labware("nest_12_reservoir_15ml", "D2")
    protocol.load_trash_bin("A3")

    # Set absolute flow rates (µL/s) — bypasses the confusing "rate=" multiplier
    pipette.flow_rate.aspirate = p.aspirate_rate_uLs
    pipette.flow_rate.dispense = p.dispense_rate_uLs

    # Define media liquid
    media = protocol.define_liquid(
        name="Master Mix",
        description="Cell-laden collagen mix",
        display_color="#0000FF"
    )
    media_rack[aspiration_location].load_liquid(media, volume=10000)
    aspirate_well = media_rack[aspiration_location]

    # Choose target columns
    if p.column_preference == 123:
        target_columns = [1, 2, 3]
    else:
        target_columns = [4, 5, 6]

    pipette.pick_up_tip()

    # --- Aspiration with anti-bubble handling ---
    pipette.move_to(aspirate_well.bottom(z=1.5))
    pipette.aspirate(aspirate_volume + p.pre_wet_volume, aspirate_well)
    protocol.delay(seconds=wait_time_aspirate)

    # Reverse pre-wet: return the small extra volume to clear trapped air / normalize meniscus
    pipette.dispense(p.pre_wet_volume/2, aspirate_well)
    protocol.delay(seconds=wait_time_prewet_return)

    # Slow, controlled withdrawal from the liquid to avoid drips/air entrainment
    pipette.move_to(aspirate_well.top(z=5), speed=20)
    pipette.touch_tip(aspirate_well)

    for col in target_columns:
        well = plate.columns()[col - 1][0]  # Top well in column

        pipette.move_to(well.top(z=p.travel_height_mm))
        total_dispensed = 0

        for i, (x, y) in enumerate(ellipse_points):
            position = well.bottom(z=p.z_height).move(Point(x, y, 0))
            pipette.move_to(position, speed=50)
            vol = dispense_volume_per_column / updated_num_points
            pipette.dispense(vol)
            total_dispensed += vol

            if i == 0:
                protocol.delay(seconds=wait_time_first_dispense)
            elif i == len(ellipse_points) // 2:
                protocol.delay(seconds=wait_time_halfway_dispense)

            if total_dispensed >= dispense_volume_per_column:
                break

        pipette.move_to(well.top(z=p.travel_height_mm))

    pipette.drop_tip()
