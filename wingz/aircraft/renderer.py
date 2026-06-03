"""
Full aircraft renderer for arbitrary configurations.

Draws whatever the optimizer produces: flying wing, twin-boom, tandem,
joined wing, box wing, canard, strut-braced, or anything in between.

6-panel layout:
    Top-left:     Top view (planform)
    Top-center:   Front view
    Top-right:    Side view
    Bottom-left:  3D perspective
    Bottom-center: Mass breakdown pie chart
    Bottom-right:  Performance summary table
"""

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Polygon
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from wingz.aircraft.geometry import AircraftGeometry
from wingz.aircraft.optimizer import AircraftResult


def _naca_airfoil(t_c: float, n_points: int = 40) -> tuple[np.ndarray, np.ndarray]:
    x = 0.5 * (1 - np.cos(np.linspace(0, np.pi, n_points)))
    yt = 5 * t_c * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2
                     + 0.2843 * x**3 - 0.1015 * x**4)
    return x, yt


def _wing_planform(geo: AircraftGeometry, x_offset: float = 0.0,
                   y_offset: float = 0.0, span: float = None,
                   root_chord: float = None, taper: float = None,
                   sweep_deg: float = None):
    """Generate wing planform coordinates for top view."""
    span = span or geo.span
    root_chord = root_chord or geo.root_chord
    taper = taper or geo.taper_ratio
    sweep_deg = sweep_deg if sweep_deg is not None else geo.sweep_deg
    tip_chord = root_chord * taper
    half_span = span / 2
    sweep_offset = half_span * np.tan(np.radians(sweep_deg))

    # Planform corners: LE root, LE tip, TE tip, TE root
    le_root = np.array([x_offset, y_offset])
    le_tip_r = np.array([x_offset + sweep_offset, y_offset + half_span])
    te_root = np.array([x_offset + root_chord, y_offset])
    te_tip_r = np.array([x_offset + sweep_offset + tip_chord, y_offset + half_span])

    le_tip_l = np.array([x_offset + sweep_offset, y_offset - half_span])
    te_tip_l = np.array([x_offset + sweep_offset + tip_chord, y_offset - half_span])

    return {
        'le_root': le_root, 'le_tip_r': le_tip_r, 'le_tip_l': le_tip_l,
        'te_root': te_root, 'te_tip_r': te_tip_r, 'te_tip_l': te_tip_l,
    }


def render_aircraft(result: AircraftResult, save: str | None = None,
                    title: str | None = None):
    """Render a 6-panel aircraft visualization."""
    if save:
        matplotlib.use("Agg")

    geo = result.geometry
    t_c = 0.14

    fig = plt.figure(figsize=(22, 16))
    if title is None:
        title = (f"Configuration: {result.config_type}\n"
                 f"MTOW: {result.mtow_kg:.1f} kg | "
                 f"Span: {geo.span:.1f}m | AR: {geo.aspect_ratio:.0f} | "
                 f"{'FEASIBLE' if result.feasible else 'INFEASIBLE'}")
    fig.suptitle(title, fontsize=13, fontweight='bold')

    # ═══════════════════════════════════════════════════════════════
    # Panel 1: Top view (planform)
    # ═══════════════════════════════════════════════════════════════
    ax1 = fig.add_subplot(2, 3, 1)
    ax1.set_title("Top View", fontsize=11)

    # Primary wing
    wp = _wing_planform(geo)
    _draw_wing_top(ax1, wp, color='steelblue', alpha=0.3, label='Wing')

    # Fuselage (top view = rectangle)
    fuse_x0 = geo.fuselage_x_offset - geo.fuselage_length * 0.3
    fuse_rect = plt.Rectangle(
        (fuse_x0, -geo.fuselage_diameter/2),
        geo.fuselage_length, geo.fuselage_diameter,
        fc='lightgray', ec='black', lw=1.5, zorder=5)
    ax1.add_patch(fuse_rect)

    # Boom
    if geo.has_tail:
        boom_x_start = fuse_x0 + geo.fuselage_length
        ax1.plot([boom_x_start, boom_x_start + geo.boom_length],
                 [0, 0], 'k-', lw=2)

        # H-tail
        htail_span = np.sqrt(geo.h_tail_area * geo.tail_aspect_ratio)
        htail_chord = geo.h_tail_area / htail_span if htail_span > 0 else 0.2
        htail_x = boom_x_start + geo.boom_length
        htail_pts = _wing_planform(geo, x_offset=htail_x, span=htail_span,
                                    root_chord=htail_chord, taper=0.6, sweep_deg=5)
        _draw_wing_top(ax1, htail_pts, color='coral', alpha=0.3, label='H-tail')

        # V-tail (top view = thin line)
        vtail_height = np.sqrt(geo.v_tail_area * geo.tail_aspect_ratio * 0.6)
        vtail_chord = geo.v_tail_area / vtail_height if vtail_height > 0 else 0.15
        ax1.plot([htail_x, htail_x + vtail_chord], [0, 0], 'r-', lw=3, alpha=0.5)

    # Second wing
    if geo.has_second_wing:
        wing2_root_chord = (2 * geo.wing2_area /
                            (geo.wing2_span * (1 + geo.wing2_taper))
                            if geo.wing2_span > 0 else 0.3)
        w2p = _wing_planform(geo, x_offset=geo.wing2_x_offset,
                              span=geo.wing2_span,
                              root_chord=wing2_root_chord,
                              taper=geo.wing2_taper, sweep_deg=0)
        _draw_wing_top(ax1, w2p, color='green', alpha=0.3, label='2nd wing')

        # Joined wing connections
        if geo.is_joined:
            wp_tip_y = geo.half_span
            w2_half = geo.wing2_span / 2
            sweep_off = geo.half_span * np.tan(np.radians(geo.sweep_deg))
            ax1.plot([sweep_off + geo.tip_chord/2, geo.wing2_x_offset + wing2_root_chord * geo.wing2_taper / 2],
                     [wp_tip_y, w2_half], 'k--', lw=1.5, alpha=0.5)
            ax1.plot([sweep_off + geo.tip_chord/2, geo.wing2_x_offset + wing2_root_chord * geo.wing2_taper / 2],
                     [-wp_tip_y, -w2_half], 'k--', lw=1.5, alpha=0.5)

    # Struts (top view)
    if geo.has_strut:
        strut_y = geo.half_span * geo.strut_span_frac
        ax1.plot([0, geo.root_chord * 0.3], [strut_y, strut_y], 'g-', lw=2, alpha=0.6)
        ax1.plot([0, geo.root_chord * 0.3], [-strut_y, -strut_y], 'g-', lw=2, alpha=0.6)

    # Motors
    n_motors = max(1, round(geo.n_motors))
    motor_positions = []
    if n_motors == 1:
        motor_positions = [0.0]
    elif n_motors == 2:
        motor_positions = [geo.half_span * geo.motor_span_frac,
                           -geo.half_span * geo.motor_span_frac]
    elif n_motors >= 3:
        motor_positions = [0.0,
                           geo.half_span * geo.motor_span_frac,
                           -geo.half_span * geo.motor_span_frac]
        if n_motors >= 4:
            motor_positions.extend([geo.half_span * geo.motor_span_frac * 0.5,
                                    -geo.half_span * geo.motor_span_frac * 0.5])

    for my in motor_positions[:n_motors]:
        ax1.plot(-0.1, my, 'ko', ms=6, zorder=10)
        # Propeller disc
        prop_r = 0.3
        circle = Circle((-0.1, my), prop_r, fill=False, ec='gray', lw=0.8, ls='--')
        ax1.add_patch(circle)

    ax1.set_xlabel("Chordwise (m)")
    ax1.set_ylabel("Spanwise (m)")
    ax1.set_aspect('equal')
    ax1.legend(fontsize=7, loc='upper right')
    ax1.grid(True, alpha=0.2)

    # ═══════════════════════════════════════════════════════════════
    # Panel 2: Front view
    # ═══════════════════════════════════════════════════════════════
    ax2 = fig.add_subplot(2, 3, 2)
    ax2.set_title("Front View", fontsize=11)

    # Wing with dihedral
    y_front = np.linspace(0, geo.half_span, 50)
    z_front = np.zeros_like(y_front)

    break_idx = int(geo.dihedral_break * len(y_front))
    for i in range(len(y_front)):
        if i <= break_idx:
            z_front[i] = y_front[i] * np.tan(np.radians(geo.dihedral_deg))
        else:
            z_front[i] = (z_front[break_idx] +
                          (y_front[i] - y_front[break_idx]) *
                          np.tan(np.radians(geo.dihedral_deg + geo.dihedral_break_angle)))

    # Both sides
    for sign in [1, -1]:
        ax2.plot(sign * y_front, z_front, 'b-', lw=2.5)
        # Spar diameter at stations
        frac = y_front / geo.half_span
        od = geo.spar_od_root + (geo.spar_od_tip - geo.spar_od_root) * frac
        for i in range(0, len(y_front), 5):
            ax2.plot([sign * y_front[i], sign * y_front[i]],
                     [z_front[i] - od[i]/2, z_front[i] + od[i]/2],
                     'b-', lw=3, alpha=0.4)

    # Fuselage cross-section
    fuse_circle = Circle((0, 0), geo.fuselage_diameter/2,
                          fc='lightgray', ec='black', lw=1.5, zorder=5)
    ax2.add_patch(fuse_circle)

    # Second wing (front view)
    if geo.has_second_wing:
        w2_half = geo.wing2_span / 2
        for sign in [1, -1]:
            ax2.plot([sign * 0.1, sign * w2_half],
                     [geo.wing2_z_offset, geo.wing2_z_offset],
                     'g-', lw=2)
        if geo.is_joined:
            for sign in [1, -1]:
                ax2.plot([sign * geo.half_span, sign * w2_half],
                         [z_front[-1], geo.wing2_z_offset], 'k--', lw=1.5)

    # Struts (front view)
    if geo.has_strut:
        strut_y = geo.half_span * geo.strut_span_frac
        strut_z_idx = int(geo.strut_span_frac * len(y_front)) - 1
        strut_z = z_front[max(0, strut_z_idx)]
        for sign in [1, -1]:
            ax2.plot([0, sign * strut_y], [-geo.fuselage_diameter/2, strut_z],
                     'g-', lw=1.5, alpha=0.7)

    # V-tail
    if geo.has_tail and geo.v_tail_area > 0.01:
        vtail_h = np.sqrt(geo.v_tail_area * geo.tail_aspect_ratio * 0.6)
        ax2.plot([0, 0], [0, vtail_h], 'r-', lw=2, alpha=0.5)

    ax2.set_xlabel("Spanwise (m)")
    ax2.set_ylabel("Vertical (m)")
    ax2.set_aspect('equal')
    ax2.grid(True, alpha=0.2)

    # ═══════════════════════════════════════════════════════════════
    # Panel 3: Side view
    # ═══════════════════════════════════════════════════════════════
    ax3 = fig.add_subplot(2, 3, 3)
    ax3.set_title("Side View", fontsize=11)

    # Wing airfoil at root (side view)
    af_x, af_y = _naca_airfoil(t_c)
    ax3.fill(af_x * geo.root_chord, af_y * geo.root_chord,
             alpha=0.2, color='steelblue')
    ax3.plot(af_x * geo.root_chord, af_y * geo.root_chord, 'b-', lw=1)
    ax3.fill(af_x * geo.root_chord, -af_y * geo.root_chord,
             alpha=0.2, color='steelblue')
    ax3.plot(af_x * geo.root_chord, -af_y * geo.root_chord, 'b-', lw=1)

    # Fuselage
    fuse_x0 = geo.fuselage_x_offset - geo.fuselage_length * 0.3
    ax3.add_patch(plt.Rectangle(
        (fuse_x0, -geo.fuselage_diameter/2),
        geo.fuselage_length, geo.fuselage_diameter,
        fc='lightgray', ec='black', lw=1.5, zorder=3))

    # Boom
    if geo.has_tail:
        boom_x_start = fuse_x0 + geo.fuselage_length
        boom_x_end = boom_x_start + geo.boom_length
        ax3.plot([boom_x_start, boom_x_end],
                 [0, 0], 'k-', lw=2)

        # H-tail airfoil
        htail_chord = (geo.h_tail_area / np.sqrt(geo.h_tail_area * geo.tail_aspect_ratio)
                       if geo.h_tail_area > 0.01 else 0.2)
        ax3.fill(boom_x_end + af_x * htail_chord, af_y * htail_chord * 0.7,
                 alpha=0.2, color='coral')
        ax3.plot(boom_x_end + af_x * htail_chord, af_y * htail_chord * 0.7,
                 'r-', lw=1)
        ax3.fill(boom_x_end + af_x * htail_chord, -af_y * htail_chord * 0.7,
                 alpha=0.2, color='coral')

        # V-tail
        if geo.v_tail_area > 0.01:
            vtail_h = np.sqrt(geo.v_tail_area * geo.tail_aspect_ratio * 0.6)
            vtail_chord = geo.v_tail_area / vtail_h if vtail_h > 0 else 0.15
            ax3.fill([boom_x_end, boom_x_end + vtail_chord * 0.8,
                      boom_x_end + vtail_chord, boom_x_end],
                     [0, 0, vtail_h, vtail_h],
                     alpha=0.2, color='red')
            ax3.plot([boom_x_end, boom_x_end + vtail_chord * 0.8,
                      boom_x_end + vtail_chord, boom_x_end],
                     [0, 0, vtail_h, vtail_h], 'r-', lw=1)

    # Second wing
    if geo.has_second_wing:
        wing2_root_chord = (2 * geo.wing2_area /
                            (geo.wing2_span * (1 + geo.wing2_taper))
                            if geo.wing2_span > 0 else 0.3)
        x_off = geo.wing2_x_offset
        z_off = geo.wing2_z_offset
        ax3.fill(x_off + af_x * wing2_root_chord,
                 z_off + af_y * wing2_root_chord,
                 alpha=0.2, color='green')
        ax3.plot(x_off + af_x * wing2_root_chord,
                 z_off + af_y * wing2_root_chord, 'g-', lw=1)
        ax3.fill(x_off + af_x * wing2_root_chord,
                 z_off - af_y * wing2_root_chord,
                 alpha=0.2, color='green')

    # Motor
    ax3.plot(-0.1, 0, 'ko', ms=8, zorder=10)

    ax3.set_xlabel("Longitudinal (m)")
    ax3.set_ylabel("Vertical (m)")
    ax3.set_aspect('equal')
    ax3.grid(True, alpha=0.2)

    # ═══════════════════════════════════════════════════════════════
    # Panel 4: 3D perspective
    # ═══════════════════════════════════════════════════════════════
    ax4 = fig.add_subplot(2, 3, 4, projection='3d')
    ax4.set_title("3D View", fontsize=11)

    n_span = 20
    n_chord = 20
    y_3d = np.linspace(-geo.half_span, geo.half_span, 2 * n_span + 1)
    frac_3d = np.abs(y_3d) / geo.half_span
    chord_3d = geo.root_chord * (1.0 - (1.0 - geo.taper_ratio) * frac_3d)
    sweep_3d = np.abs(y_3d) * np.tan(np.radians(geo.sweep_deg))

    # Dihedral
    z_dihed = np.zeros_like(y_3d)
    for i, y_val in enumerate(y_3d):
        abs_y = abs(y_val)
        frac_y = abs_y / geo.half_span
        if frac_y <= geo.dihedral_break:
            z_dihed[i] = abs_y * np.tan(np.radians(geo.dihedral_deg))
        else:
            break_y = geo.half_span * geo.dihedral_break
            z_dihed[i] = (break_y * np.tan(np.radians(geo.dihedral_deg)) +
                          (abs_y - break_y) * np.tan(np.radians(
                              geo.dihedral_deg + geo.dihedral_break_angle)))

    af_x_norm, af_y_norm = _naca_airfoil(t_c, n_points=n_chord)

    # Upper surface
    X_up = np.zeros((len(y_3d), n_chord))
    Y_up = np.zeros((len(y_3d), n_chord))
    Z_up = np.zeros((len(y_3d), n_chord))

    for i, y_val in enumerate(y_3d):
        c = chord_3d[i]
        X_up[i, :] = af_x_norm[:n_chord] * c + sweep_3d[i]
        Y_up[i, :] = y_val
        Z_up[i, :] = af_y_norm[:n_chord] * c + z_dihed[i]

    ax4.plot_surface(X_up, Y_up, Z_up, alpha=0.4, color='#FFD700',
                     edgecolor='gray', linewidth=0.1)

    # Lower surface
    X_lo = np.zeros((len(y_3d), n_chord))
    Y_lo = np.zeros((len(y_3d), n_chord))
    Z_lo = np.zeros((len(y_3d), n_chord))

    for i, y_val in enumerate(y_3d):
        c = chord_3d[i]
        X_lo[i, :] = af_x_norm[:n_chord] * c + sweep_3d[i]
        Y_lo[i, :] = y_val
        Z_lo[i, :] = -af_y_norm[:n_chord] * c + z_dihed[i]

    ax4.plot_surface(X_lo, Y_lo, Z_lo, alpha=0.2, color='#C0C0C0',
                     edgecolor='gray', linewidth=0.1)

    # Fuselage in 3D
    theta_fuse = np.linspace(0, 2 * np.pi, 16)
    x_fuse_pts = np.linspace(geo.fuselage_x_offset - geo.fuselage_length * 0.3,
                              geo.fuselage_x_offset + geo.fuselage_length * 0.7, 10)
    Y_fuse = np.zeros((len(x_fuse_pts), len(theta_fuse)))
    X_fuse = np.zeros_like(Y_fuse)
    Z_fuse = np.zeros_like(Y_fuse)
    for i, xf in enumerate(x_fuse_pts):
        r = geo.fuselage_diameter / 2
        X_fuse[i, :] = xf
        Y_fuse[i, :] = r * np.cos(theta_fuse)
        Z_fuse[i, :] = r * np.sin(theta_fuse)

    ax4.plot_surface(X_fuse, Y_fuse, Z_fuse, alpha=0.3, color='lightgray',
                     edgecolor='gray', linewidth=0.2)

    # Boom in 3D
    if geo.has_tail:
        boom_x_start = geo.fuselage_x_offset + geo.fuselage_length * 0.7
        boom_x_end = boom_x_start + geo.boom_length
        ax4.plot([boom_x_start, boom_x_end], [0, 0], [0, 0], 'k-', lw=2)

    ax4.set_xlabel("X (m)")
    ax4.set_ylabel("Y (m)")
    ax4.set_zlabel("Z (m)")
    ax4.view_init(elev=25, azim=-60)

    # ═══════════════════════════════════════════════════════════════
    # Panel 5: Mass breakdown
    # ═══════════════════════════════════════════════════════════════
    ax5 = fig.add_subplot(2, 3, 5)
    ax5.set_title("Mass Breakdown", fontsize=11)

    s = result.structure
    masses = {
        'Wing spar': s.get('wing_spar_mass', 0),
        'Wing ribs': s.get('wing_rib_mass', 0),
        'Wing skin': s.get('wing_skin_mass', 0),
        'Wing LE': s.get('wing_le_mass', 0),
        'Fuselage': s.get('fuse_mass', 0),
        'Boom': s.get('boom_mass', 0),
        'H-tail': s.get('htail_mass', 0),
        'V-tail': s.get('vtail_mass', 0),
        '2nd wing': s.get('wing2_mass', 0),
        'Struts': s.get('strut_mass', 0),
        'Motors': s.get('motor_mass', 0),
        'Battery': result.battery_mass_kg,
        'Panels': result.panel_mass_kg,
        'Payload': result.mtow_kg - result.structural_mass_kg - result.battery_mass_kg - result.panel_mass_kg - 0.4,
        'Avionics': 0.4,
    }
    # Filter out zero-mass components
    masses = {k: v for k, v in masses.items() if v > 0.05}

    colors = plt.cm.Set3(np.linspace(0, 1, len(masses)))
    wedges, texts, autotexts = ax5.pie(
        masses.values(), labels=masses.keys(), autopct='%1.0f%%',
        colors=colors, pctdistance=0.85, startangle=90, textprops={'fontsize': 7})
    for t in autotexts:
        t.set_fontsize(6)

    # Mass annotations
    total_str = f"MTOW: {result.mtow_kg:.1f} kg"
    ax5.text(0, -1.35, total_str, ha='center', fontsize=10, fontweight='bold')

    # ═══════════════════════════════════════════════════════════════
    # Panel 6: Performance summary
    # ═══════════════════════════════════════════════════════════════
    ax6 = fig.add_subplot(2, 3, 6)
    ax6.axis('off')
    ax6.set_title("Performance Summary", fontsize=11)

    lines = [
        f"{'Configuration:':<22s} {result.config_type}",
        f"{'MTOW:':<22s} {result.mtow_kg:.1f} kg",
        f"{'Span:':<22s} {geo.span:.1f} m",
        f"{'Aspect ratio:':<22s} {geo.aspect_ratio:.1f}",
        f"{'Wing area:':<22s} {result.wing_area_m2:.1f} m²",
        f"{'Taper ratio:':<22s} {geo.taper_ratio:.2f}",
        f"{'Sweep:':<22s} {geo.sweep_deg:.1f}°",
        "",
        f"{'V_cruise (day):':<22s} {result.velocity_day:.1f} m/s ({result.velocity_day * 3.6:.0f} km/h)",
        f"{'V_cruise (night):':<22s} {result.velocity_night:.1f} m/s",
        f"{'Power (day):':<22s} {result.power_day_W:.0f} W",
        f"{'Power (night):':<22s} {result.power_night_W:.0f} W",
        "",
        f"{'CD0:':<22s} {result.aero['CD0']:.4f}",
        f"{'Oswald e:':<22s} {result.aero['oswald_e']:.3f}",
        f"{'Panel coverage:':<22s} {result.panel_coverage:.0%}",
        f"{'Energy closes:':<22s} {'YES' if result.energy_closes else 'NO'}",
        "",
        f"{'Structural mass:':<22s} {result.structural_mass_kg:.1f} kg",
        f"{'Battery mass:':<22s} {result.battery_mass_kg:.1f} kg",
        f"{'Panel mass:':<22s} {result.panel_mass_kg:.1f} kg",
        f"{'Stress margin:':<22s} {result.structure['stress_margin']:.0%}",
        f"{'Buckling margin:':<22s} {result.structure['min_buckling']:.1f}x",
        f"{'Tip deflection:':<22s} {result.structure['tip_deflection_pct']:.1f}%",
        "",
        f"{'Feasible:':<22s} {'YES' if result.feasible else 'NO'}",
    ]

    # Fuselage / tail details
    if geo.has_tail:
        lines.append(f"{'Boom length:':<22s} {geo.boom_length:.2f} m")
    if geo.has_second_wing:
        lines.append(f"{'2nd wing area:':<22s} {geo.wing2_area:.1f} m²")
        lines.append(f"{'2nd wing offset:':<22s} x={geo.wing2_x_offset:.1f}m, z={geo.wing2_z_offset:.1f}m")
    if geo.has_strut:
        lines.append(f"{'Strut station:':<22s} {geo.strut_span_frac:.0%} span")

    text = "\n".join(lines)
    ax6.text(0.05, 0.95, text, transform=ax6.transAxes,
             fontsize=8, fontfamily='monospace', verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    plt.tight_layout(rect=[0.01, 0.01, 0.99, 0.94])

    if save:
        fig.savefig(save, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved to {save}")
    else:
        plt.show()

    return fig


def _draw_wing_top(ax, wp, color='steelblue', alpha=0.3, label=None):
    """Draw a wing planform on a top-view axis."""
    # Right half
    verts_r = [wp['le_root'], wp['le_tip_r'], wp['te_tip_r'], wp['te_root']]
    poly_r = Polygon(verts_r, closed=True, fc=color, ec='black',
                     alpha=alpha, lw=1.2, label=label)
    ax.add_patch(poly_r)

    # Left half
    verts_l = [wp['le_root'], wp['le_tip_l'], wp['te_tip_l'], wp['te_root']]
    poly_l = Polygon(verts_l, closed=True, fc=color, ec='black',
                     alpha=alpha, lw=1.2)
    ax.add_patch(poly_l)
    ax.autoscale_view()


def render_comparison(results: list[AircraftResult], save: str | None = None):
    """Render a comparison chart of multiple optimized configurations."""
    if save:
        matplotlib.use("Agg")

    n = len(results)
    fig, axes = plt.subplots(2, n, figsize=(6 * n, 10))
    if n == 1:
        axes = axes.reshape(2, 1)

    fig.suptitle("Configuration Comparison", fontsize=14, fontweight='bold')

    for i, res in enumerate(results):
        geo = res.geometry

        # Top view
        ax_top = axes[0, i]
        ax_top.set_title(f"#{i+1}: {res.config_type}\nMTOW: {res.mtow_kg:.1f} kg",
                         fontsize=9)

        wp = _wing_planform(geo)
        _draw_wing_top(ax_top, wp, color='steelblue', alpha=0.3)

        # Fuselage
        fuse_x0 = geo.fuselage_x_offset - geo.fuselage_length * 0.3
        ax_top.add_patch(plt.Rectangle(
            (fuse_x0, -geo.fuselage_diameter/2),
            geo.fuselage_length, geo.fuselage_diameter,
            fc='lightgray', ec='black', lw=1))

        if geo.has_tail:
            boom_x = fuse_x0 + geo.fuselage_length
            ax_top.plot([boom_x, boom_x + geo.boom_length], [0, 0], 'k-', lw=1.5)

        if geo.has_second_wing:
            w2_rc = (2 * geo.wing2_area /
                     (geo.wing2_span * (1 + geo.wing2_taper))
                     if geo.wing2_span > 0 else 0.3)
            w2p = _wing_planform(geo, x_offset=geo.wing2_x_offset,
                                  span=geo.wing2_span,
                                  root_chord=w2_rc, taper=geo.wing2_taper)
            _draw_wing_top(ax_top, w2p, color='green', alpha=0.3)

        ax_top.set_aspect('equal')
        ax_top.grid(True, alpha=0.2)

        # Mass breakdown bar
        ax_bar = axes[1, i]
        s = res.structure
        categories = ['Wing', 'Fuse+Boom', 'Tail', 'Battery', 'Panels', 'Payload']
        values = [
            s.get('wing_mass', 0),
            s.get('fuse_mass', 0) + s.get('boom_mass', 0),
            s.get('htail_mass', 0) + s.get('vtail_mass', 0),
            res.battery_mass_kg,
            res.panel_mass_kg,
            5.0,
        ]
        colors = ['steelblue', 'gray', 'coral', 'gold', 'orange', 'green']
        ax_bar.barh(categories, values, color=colors, alpha=0.7)
        ax_bar.set_xlabel("Mass (kg)")
        ax_bar.set_title(f"Span={geo.span:.0f}m AR={geo.aspect_ratio:.0f}", fontsize=9)

    plt.tight_layout(rect=[0.01, 0.01, 0.99, 0.95])

    if save:
        fig.savefig(save, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved to {save}")
    else:
        plt.show()

    return fig
