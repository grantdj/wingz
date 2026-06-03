#!/usr/bin/env python3
"""
Full aircraft configuration explorer.

Runs the monolithic optimizer with multiple seeds to discover novel
aircraft configurations. Each seed starts from a different random
point in the 28-dimensional design space, potentially finding
different local optima (flying wing, tandem, box wing, etc.).

Usage:
    python scripts/explore_aircraft.py                    # quick run (1 seed, 500 iter)
    python scripts/explore_aircraft.py --seeds 5          # multi-seed exploration
    python scripts/explore_aircraft.py --full             # full run (5 seeds, 2000 iter)
    python scripts/explore_aircraft.py --workers 8        # explicit core count
"""

import argparse
import sys
import time

from wingz.aircraft.geometry import PayloadBay
from wingz.aircraft.optimizer import OptimizationConfig, optimize_aircraft, sweep_seeds
from wingz.aircraft.renderer import render_aircraft, render_comparison


def main():
    parser = argparse.ArgumentParser(description="Aircraft configuration explorer")
    parser.add_argument('--seeds', type=int, default=1, help="Number of random seeds")
    parser.add_argument('--maxiter', type=int, default=500, help="Max iterations per seed")
    parser.add_argument('--popsize', type=int, default=40, help="Population size")
    parser.add_argument('--full', action='store_true', help="Full exploration (5 seeds, 2000 iter)")
    parser.add_argument('--workers', type=int, default=1, help="Parallel workers (-1=all cores)")
    parser.add_argument('--payload-mass', type=float, default=5.0, help="Payload mass (kg)")
    parser.add_argument('--payload-power', type=float, default=50.0, help="Payload power (W)")
    parser.add_argument('--payload-length', type=float, default=0.4, help="Payload bay length (m)")
    parser.add_argument('--payload-diameter', type=float, default=0.15, help="Payload bay diameter (m)")
    parser.add_argument('--latitude', type=float, default=30.0, help="Operating latitude (deg)")
    parser.add_argument('--cost-weight', type=float, default=0.001, help="Cost weight in objective ($/kg equiv)")
    parser.add_argument('--formation-n', type=int, default=6, help="Formation fleet size")
    parser.add_argument('--production-run', type=int, default=10, help="Production run for cost amort")
    parser.add_argument('--no-formation', action='store_true', help="Disable formation controllability req")
    parser.add_argument('--save', type=str, default=None, help="Save prefix for output files")
    parser.add_argument('--no-render', action='store_true', help="Skip rendering")
    args = parser.parse_args()

    if args.full:
        args.seeds = 5
        args.maxiter = 2000

    bay = PayloadBay(
        length_m=args.payload_length,
        diameter_m=args.payload_diameter,
        mass_kg=args.payload_mass,
        power_W=args.payload_power,
    )

    opt = OptimizationConfig(
        payload=bay,
        latitude_deg=args.latitude,
        maxiter=args.maxiter,
        popsize=args.popsize,
        workers=args.workers,
        cost_weight=args.cost_weight,
        formation_N=args.formation_n,
        production_run=args.production_run,
        require_formation=not args.no_formation,
    )

    print("=" * 70)
    print("AIRCRAFT CONFIGURATION EXPLORER")
    print("=" * 70)
    print(f"Payload: {bay.mass_kg} kg, {bay.power_W} W")
    print(f"  Bay: {bay.length_m:.1f}m × {bay.diameter_m:.2f}m diameter")
    print(f"Latitude: {args.latitude}°")
    print(f"Seeds: {args.seeds}, maxiter: {args.maxiter}, popsize: {args.popsize}")
    print(f"Workers: {args.workers}")
    print()

    t0 = time.time()

    if args.seeds == 1:
        result = optimize_aircraft(opt)
        results = [result]
    else:
        results = sweep_seeds(opt, n_seeds=args.seeds)

    elapsed = time.time() - t0

    print()
    print("=" * 70)
    print(f"RESULTS (completed in {elapsed:.0f}s)")
    print("=" * 70)
    print()

    for i, res in enumerate(results):
        geo = res.geometry
        print(f"#{i+1}: {res.config_type}")
        print(f"  MTOW:       {res.mtow_kg:.1f} kg")
        print(f"  Span:       {geo.span:.1f} m")
        print(f"  AR:         {geo.aspect_ratio:.1f}")
        print(f"  Taper:      {geo.taper_ratio:.2f}")
        print(f"  Sweep:      {geo.sweep_deg:.1f}°")
        print(f"  Wing area:  {res.wing_area_m2:.1f} m²")
        print(f"  V_day:      {res.velocity_day:.1f} m/s ({res.velocity_day * 3.6:.0f} km/h)")
        print(f"  Power day:  {res.power_day_W:.0f} W")
        print(f"  Power night:{res.power_night_W:.0f} W")
        print(f"  CD0:        {res.aero['CD0']:.4f}")
        print(f"  Oswald e:   {res.aero['oswald_e']:.3f}")
        print(f"  Panels:     {res.panel_coverage:.0%} coverage")
        print(f"  Structure:  {res.structural_mass_kg:.1f} kg")
        print(f"  Battery:    {res.battery_mass_kg:.1f} kg")
        print(f"  Panels:     {res.panel_mass_kg:.1f} kg")
        print(f"  Unit cost:  ${res.unit_cost_usd:,.0f}")
        print(f"  Fleet cost: ${res.fleet_cost_usd:,.0f} ({args.formation_n} aircraft)")
        print(f"  Feasible:   {'YES' if res.feasible else 'NO'}")
        if geo.has_tail:
            print(f"  Tail:       boom={geo.boom_length:.1f}m, "
                  f"h={geo.h_tail_area:.2f}m², v={geo.v_tail_area:.2f}m²")
        if geo.has_second_wing:
            print(f"  2nd wing:   {geo.wing2_area:.1f}m², "
                  f"x={geo.wing2_x_offset:.1f}m, z={geo.wing2_z_offset:.1f}m")
            if geo.is_joined:
                print(f"  Joined:     YES (box wing)")
        if geo.has_strut:
            print(f"  Strut:      at {geo.strut_span_frac:.0%} span")
        print()

    if not args.no_render:
        for i, res in enumerate(results):
            save_path = f"{args.save}_{i+1}.png" if args.save else None
            render_aircraft(res, save=save_path)

        if len(results) > 1:
            save_comp = f"{args.save}_comparison.png" if args.save else None
            render_comparison(results, save=save_comp)


if __name__ == "__main__":
    main()
