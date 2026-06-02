"""
Wing geometry renderer.

Generates 3-view and 3D renderings of a tube spar wing design,
showing planform, spar taper, rib locations, airfoil cross-sections,
and structural annotations.

Usage:
    from wingz.structures.tube_optimizer import optimize_wing, WingRequirements
    from wingz.structures.wing_renderer import render_wing

    req = WingRequirements(span_m=20, aspect_ratio=8, aircraft_mass_kg=50)
    design, result = optimize_wing(req)
    render_wing(design, req, result)          # show interactively
    render_wing(design, req, result, save="wing.png")  # save to file
"""

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Polygon
from matplotlib.collections import PatchCollection
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from wingz.structures.tube_optimizer import TubeDesign, WingRequirements, AnalysisResult


def _naca_airfoil(t_c: float, n_points: int = 60) -> tuple[np.ndarray, np.ndarray]:
    """NACA 4-digit symmetric airfoil coordinates (normalized 0-1)."""
    x = 0.5 * (1 - np.cos(np.linspace(0, np.pi, n_points)))
    yt = 5 * t_c * (
        0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2
        + 0.2843 * x**3 - 0.1015 * x**4
    )
    xu = x
    yu = yt
    xl = x
    yl = -yt
    return np.concatenate([xu, xl[::-1]]), np.concatenate([yu, yl[::-1]])


def render_wing(
    design: TubeDesign,
    req: WingRequirements,
    result: AnalysisResult,
    save: str | None = None,
    title: str | None = None,
):
    """
    Render a 4-panel wing visualization.

    Panels:
        Top-left:  Planform (top view) with spar and rib locations
        Top-right: Front view showing spar diameter taper and deflection
        Bot-left:  Root and tip airfoil cross-sections with spar
        Bot-right: 3D perspective view
    """
    if save:
        matplotlib.use("Agg")

    L = req.half_span
    root_chord = req.root_chord
    t_c = req.thickness_ratio
    n_stations = 30

    # Station data
    y_stations = np.linspace(0, L, n_stations + 1)
    frac = y_stations / L
    chord = root_chord * (1.0 - (1.0 - design.taper_ratio) * frac)
    od = design.spar_od_root + (design.spar_od_tip - design.spar_od_root) * frac
    wall = design.spar_wall_root + (design.spar_wall_tip - design.spar_wall_root) * frac

    # Spar at 30% chord
    spar_x_frac = 0.30

    # Rib locations
    n_ribs = max(2, int(np.ceil(req.span_m / design.rib_spacing)))
    rib_y = np.linspace(0, L, n_ribs // 2 + 1)

    # Deflection curve (approximate parabolic)
    defl = result.tip_deflection_m * (y_stations / L) ** 2

    fig = plt.figure(figsize=(18, 14))
    if title is None:
        title = (f"{req.span_m:.0f}m span, AR={req.aspect_ratio:.0f}, "
                 f"{req.aircraft_mass_kg:.0f} kg MTOW — "
                 f"Wing mass: {result.total_mass_kg:.1f} kg")
    fig.suptitle(title, fontsize=14, fontweight='bold')

    # ── Panel 1: Planform (top view) ────────────────────────────────
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.set_title("Planform (Top View)", fontsize=11)

    # Both halves of the wing
    for sign in [1, -1]:
        # Leading edge
        le_x = np.zeros_like(y_stations)
        # Trailing edge (chord extends aft from LE at x=0)
        te_x = chord

        y_plot = sign * y_stations

        # Wing outline
        ax1.plot(y_plot, le_x, 'k-', lw=1.5)
        ax1.plot(y_plot, te_x, 'k-', lw=1.5)
        # Tip closure
        ax1.plot([y_plot[-1], y_plot[-1]], [le_x[-1], te_x[-1]], 'k-', lw=1.5)
        # Root line
        ax1.plot([y_plot[0], y_plot[0]], [le_x[0], te_x[0]], 'k-', lw=1.5)

        # Spar line
        spar_x = chord * spar_x_frac
        ax1.plot(y_plot, spar_x, 'b-', lw=2, alpha=0.7)

        # Spar diameter envelope
        spar_upper = spar_x - od / 2
        spar_lower = spar_x + od / 2
        ax1.fill_between(y_plot, spar_upper, spar_lower, alpha=0.3, color='blue',
                         label='Spar tube' if sign == 1 else None)

        # Ribs
        for ry in rib_y:
            ry_plot = sign * ry
            idx = np.argmin(np.abs(y_stations - ry))
            ax1.plot([ry_plot, ry_plot], [0, chord[idx]], 'g-', lw=0.8, alpha=0.5)

    # Solar panel zone (shade upper surface)
    # Just show a subtle shading on the upper surface
    for sign in [1, -1]:
        y_plot = sign * y_stations
        ax1.fill_between(y_plot, chord * 0.15, chord * 0.85,
                         alpha=0.08, color='gold')

    ax1.set_xlabel("Span (m)")
    ax1.set_ylabel("Chord (m)")
    ax1.set_aspect('equal')
    ax1.legend(fontsize=8, loc='upper right')
    ax1.grid(True, alpha=0.2)
    ax1.invert_yaxis()

    # Annotations
    ax1.annotate(f"Root chord: {root_chord*100:.0f} cm",
                 xy=(0, root_chord), xytext=(L*0.3, root_chord*1.3),
                 fontsize=8, arrowprops=dict(arrowstyle='->', color='gray'))
    tip_chord = root_chord * design.taper_ratio
    ax1.annotate(f"Tip chord: {tip_chord*100:.0f} cm",
                 xy=(L, tip_chord), xytext=(L*0.7, root_chord*1.3),
                 fontsize=8, arrowprops=dict(arrowstyle='->', color='gray'))

    # ── Panel 2: Front view (deflected shape) ──────────────────────
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.set_title("Front View (1g Deflected Shape)", fontsize=11)

    # Undeflected
    for sign in [1, -1]:
        y_plot = sign * y_stations
        ax2.plot(y_plot, np.zeros_like(y_stations), 'k--', lw=0.8, alpha=0.4)

    # Deflected
    for sign in [1, -1]:
        y_plot = sign * y_stations
        ax2.plot(y_plot, defl, 'b-', lw=2)

        # Spar diameter as vertical bars at stations
        for i in range(0, len(y_stations), 3):
            ax2.plot([y_plot[i], y_plot[i]],
                     [defl[i] - od[i]/2, defl[i] + od[i]/2],
                     'b-', lw=3, alpha=0.4)

    # Deflection annotation
    ax2.annotate(f"Tip deflection: {result.tip_deflection_m:.2f} m\n"
                 f"({result.tip_deflection_pct:.1f}% of half-span)",
                 xy=(L, defl[-1]),
                 xytext=(L * 0.5, defl[-1] * 1.5 + 0.3),
                 fontsize=9,
                 arrowprops=dict(arrowstyle='->', color='red'))

    # Fuselage/body sketch at center
    body_w = root_chord * 0.3
    body_h = root_chord * t_c * 1.5
    ax2.add_patch(plt.Rectangle((-body_w/2, -body_h/2), body_w, body_h,
                                fc='lightgray', ec='gray', lw=1))

    ax2.set_xlabel("Span (m)")
    ax2.set_ylabel("Vertical deflection (m)")
    ax2.set_aspect('equal')
    ax2.grid(True, alpha=0.2)

    # ── Panel 3: Airfoil cross-sections ────────────────────────────
    ax3 = fig.add_subplot(2, 2, 3)
    ax3.set_title("Airfoil Cross-Sections (Root & Tip)", fontsize=11)

    airfoil_x, airfoil_y = _naca_airfoil(t_c)

    # Root airfoil
    root_ax = airfoil_x * root_chord
    root_ay = airfoil_y * root_chord
    ax3.plot(root_ax, root_ay, 'k-', lw=1.5, label='Root')
    ax3.fill(root_ax, root_ay, alpha=0.05, color='gray')

    # Root spar circle
    spar_cx = spar_x_frac * root_chord
    spar_cy = 0
    theta = np.linspace(0, 2 * np.pi, 60)
    # Outer diameter
    ax3.plot(spar_cx + od[0]/2 * np.cos(theta),
             spar_cy + od[0]/2 * np.sin(theta), 'b-', lw=2)
    # Inner diameter
    id_root = od[0] - 2 * wall[0]
    if id_root > 0:
        ax3.plot(spar_cx + id_root/2 * np.cos(theta),
                 spar_cy + id_root/2 * np.sin(theta), 'b--', lw=1)
    # Fill spar wall
    ax3.fill_between(spar_cx + od[0]/2 * np.cos(theta),
                      spar_cy + od[0]/2 * np.sin(theta),
                      spar_cx + id_root/2 * np.cos(theta) if id_root > 0 else spar_cy,
                      alpha=0.3, color='blue')

    # Tip airfoil (offset vertically for clarity)
    tip_chord_val = root_chord * design.taper_ratio
    offset_y = -root_chord * t_c * 2
    tip_ax = airfoil_x * tip_chord_val
    tip_ay = airfoil_y * tip_chord_val + offset_y
    ax3.plot(tip_ax, tip_ay, 'r-', lw=1.5, label='Tip')
    ax3.fill(tip_ax, tip_ay, alpha=0.05, color='red')

    # Tip spar circle
    spar_cx_tip = spar_x_frac * tip_chord_val
    ax3.plot(spar_cx_tip + od[-1]/2 * np.cos(theta),
             offset_y + od[-1]/2 * np.sin(theta), 'b-', lw=2)
    id_tip = od[-1] - 2 * wall[-1]
    if id_tip > 0:
        ax3.plot(spar_cx_tip + id_tip/2 * np.cos(theta),
                 offset_y + id_tip/2 * np.sin(theta), 'b--', lw=1)

    # Dimension annotations
    ax3.annotate(f"OD: {od[0]*1000:.1f} mm\nwall: {wall[0]*1000:.2f} mm",
                 xy=(spar_cx + od[0]/2, 0), xytext=(root_chord * 0.7, root_chord * t_c * 0.8),
                 fontsize=8, arrowprops=dict(arrowstyle='->', color='blue'))
    ax3.annotate(f"OD: {od[-1]*1000:.1f} mm\nwall: {wall[-1]*1000:.2f} mm",
                 xy=(spar_cx_tip + od[-1]/2, offset_y),
                 xytext=(tip_chord_val * 0.8 + 0.1, offset_y + root_chord * t_c * 0.5),
                 fontsize=8, arrowprops=dict(arrowstyle='->', color='blue'))

    ax3.set_xlabel("Chord position (m)")
    ax3.set_ylabel("Thickness (m)")
    ax3.set_aspect('equal')
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.2)

    # ── Panel 4: 3D perspective ────────────────────────────────────
    ax4 = fig.add_subplot(2, 2, 4, projection='3d')
    ax4.set_title("3D View", fontsize=11)

    # Build wing surface mesh
    n_span = 20
    n_chord = 30
    y_3d = np.linspace(-L, L, 2 * n_span + 1)
    frac_3d = np.abs(y_3d) / L
    chord_3d = root_chord * (1.0 - (1.0 - design.taper_ratio) * frac_3d)
    defl_3d = result.tip_deflection_m * frac_3d ** 2

    airfoil_x_norm, airfoil_y_norm = _naca_airfoil(t_c, n_points=n_chord)

    # Upper surface only (first half of airfoil coords)
    x_upper = airfoil_x_norm[:n_chord]
    z_upper = airfoil_y_norm[:n_chord]
    x_lower = airfoil_x_norm[n_chord:][::-1]
    z_lower = airfoil_y_norm[n_chord:][::-1]

    for surface, z_norm, color, alpha in [
        ('upper', z_upper, '#FFD700', 0.4),  # gold for solar panels
        ('lower', z_lower, '#C0C0C0', 0.2),  # silver for underside
    ]:
        X = np.zeros((len(y_3d), n_chord))
        Y = np.zeros((len(y_3d), n_chord))
        Z = np.zeros((len(y_3d), n_chord))

        for i, y_val in enumerate(y_3d):
            c = chord_3d[i]
            X[i, :] = x_upper * c if surface == 'upper' else x_lower * c
            Y[i, :] = y_val
            Z[i, :] = z_norm * c + defl_3d[i]

        ax4.plot_surface(X, Y, Z, alpha=alpha, color=color,
                         edgecolor='gray', linewidth=0.1)

    # Spar line in 3D
    od_3d = design.spar_od_root + (design.spar_od_tip - design.spar_od_root) * frac_3d
    spar_x_3d = chord_3d * spar_x_frac
    ax4.plot(spar_x_3d, y_3d, defl_3d, 'b-', lw=2, alpha=0.8)

    ax4.set_xlabel("Chord (m)")
    ax4.set_ylabel("Span (m)")
    ax4.set_zlabel("Height (m)")
    ax4.view_init(elev=25, azim=-60)

    # ── Mass breakdown text box ────────────────────────────────────
    info = (
        f"Mass Breakdown:\n"
        f"  Spar:  {result.spar_mass_kg:.2f} kg\n"
        f"  Ribs:  {result.rib_mass_kg:.2f} kg ({result.n_ribs} ribs)\n"
        f"  Skin:  {result.skin_mass_kg:.2f} kg\n"
        f"  LE:    {result.le_mass_kg:.2f} kg\n"
        f"  Total: {result.total_mass_kg:.1f} kg\n"
        f"\nConstraints:\n"
        f"  Stress margin: {result.stress_margin:.0%}\n"
        f"  Buckling: {result.min_buckling_margin:.1f}x\n"
        f"  Tip defl: {result.tip_deflection_pct:.1f}%\n"
        f"  Feasible: {'YES' if result.feasible else 'NO'}"
    )
    fig.text(0.02, 0.02, info, fontsize=8, fontfamily='monospace',
             verticalalignment='bottom',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    design_info = (
        f"Design:\n"
        f"  Spar OD: {design.spar_od_root*1000:.1f} → {design.spar_od_tip*1000:.1f} mm\n"
        f"  Wall:    {design.spar_wall_root*1000:.2f} → {design.spar_wall_tip*1000:.2f} mm\n"
        f"  Taper:   {design.taper_ratio:.2f}\n"
        f"  Ribs:    every {design.rib_spacing*100:.0f} cm\n"
        f"  Skin:    {design.skin_areal_density:.2f} kg/m²"
    )
    fig.text(0.98, 0.02, design_info, fontsize=8, fontfamily='monospace',
             verticalalignment='bottom', horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor='lightcyan', alpha=0.8))

    plt.tight_layout(rect=[0.03, 0.08, 0.97, 0.95])

    if save:
        fig.savefig(save, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved to {save}")
    else:
        plt.show()

    return fig
