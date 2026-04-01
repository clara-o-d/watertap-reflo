"""
Li2CO3 precipitation kinetics — comparison of experimental data to the
current first-order approximation (k = 0.000853 s⁻¹).

No curve fitting is performed.  A data-based effective k is estimated at
each time point using the linearized first-order formula, and the geometric
mean of those values is reported.

Data files (in ../data/):
  SO4_Li_0_T_60.csv  - no extra SO4, 60°C
  SO4_Li_1_T_60.csv  - extra SO4,    60°C
  SO4_Li_0_T_90.csv  - no extra SO4, 90°C
  SO4_Li_1_T_90.csv  - extra SO4,    90°C

Columns (no header): time [min], Li [ppm]

Approximation model:
  C(t) = C_eq + (C0 - C_eq) * exp(-k_approx * t)
  k_approx = 0.000853 s⁻¹  (= 0.05118 min⁻¹)
  C_eq  = minimum Li concentration observed in each dataset
  C0    = first measured value

Reactor volume relationship (V ∝ 1/k):
  V_approx / V_data = k_data / k_approx
  % volume error     = (k_data / k_approx − 1) × 100

Reactor capital cost (from costing_parameters.yaml):
  C_cap = b * V^n   with b = 33 443.53 USD/m³^n,  n = 0.5585
  % cost error = ((k_data / k_approx)^n − 1) × 100
"""

import os
import glob
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
K_APPROX_S   = 0.000853         # s⁻¹  — current model approximation
K_APPROX_MIN = K_APPROX_S * 60 # min⁻¹

# Reactor capital cost: C_cap = B * V^N_COST  (V in m³)
B_COST  = 33_443.53   # USD / m³^N_COST
N_COST  = 0.5585      # scaling exponent  (from costing_parameters.yaml, Stainless 300 psi)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUT_DIR  = os.path.dirname(__file__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_condition(filename):
    base = os.path.splitext(os.path.basename(filename))[0].upper()
    parts = base.split("_")
    so4_level = parts[2] if len(parts) > 2 else "?"
    temp      = parts[4] if len(parts) > 4 else "?"
    return f"SO4={so4_level}, T={temp}°C", so4_level, temp


def approx_curve(t, C0, C_eq):
    """First-order approximation using the current k_approx."""
    return C_eq + (C0 - C_eq) * np.exp(-K_APPROX_MIN * t)


def estimate_k_data(t, C, C0, C_eq):
    """
    Estimate effective k from data using the linearized first-order formula:
        k_i = -ln((C_i - C_eq) / (C0 - C_eq)) / t_i

    Returns the geometric mean of valid k_i values (t > 0, argument > 0).
    This is a direct analytical estimate — no optimisation.
    """
    mask = t > 0
    t_pos = t[mask]
    C_pos = C[mask]
    arg = (C_pos - C_eq) / (C0 - C_eq)
    # arg=1 → C=C0 (no reaction yet, k≈0, uninformative)
    # arg≤0 → C≤C_eq (below equilibrium, physically invalid for log)
    valid = (arg > 0) & (arg < 1.0)
    if not np.any(valid):
        return np.nan
    k_vals = -np.log(arg[valid]) / t_pos[valid]
    return float(np.exp(np.mean(np.log(k_vals))))  # geometric mean


def load_file(filepath):
    df = pd.read_csv(filepath, header=None, names=["time_min", "Li_ppm"])
    df = df.sort_values("time_min").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    pattern = os.path.join(DATA_DIR, "SO4_L*.csv")
    files = sorted(glob.glob(pattern, recursive=False))
    if not files:
        raise FileNotFoundError(f"No SO4 CSV files found in {DATA_DIR}")

    # ---- Figure setup: 2×2 concentration plots ----
    fig, axes = plt.subplots(2, 2, figsize=(13, 10))
    axes = axes.flatten()

    summary_rows = []

    # ---- Header for console output ----
    pt_header = (
        f"\n{'Condition':<22} {'t (min)':>8} {'C_meas':>8} {'C_approx':>10} "
        f"{'Abs err':>9} {'% err':>7}"
    )
    print(pt_header)
    print("=" * len(pt_header.strip()))

    for idx, filepath in enumerate(files):
        label, so4_level, temp = parse_condition(filepath)
        df = load_file(filepath)
        t  = df["time_min"].values
        C  = df["Li_ppm"].values

        C0   = C[0]
        C_eq = float(np.min(C))   # use minimum observed as equilibrium estimate

        # Approximation curve values at data time points
        C_approx_pts = approx_curve(t, C0, C_eq)

        abs_err  = C_approx_pts - C
        pct_err  = abs_err / C * 100

        for ti, ci, ca, ae, pe in zip(t, C, C_approx_pts, abs_err, pct_err):
            print(
                f"{label:<22} {ti:>8.1f} {ci:>8.0f} {ca:>10.0f} "
                f"{ae:>+9.0f} {pe:>+6.1f}%"
            )
        print()

        # Data-based k (no optimisation)
        k_data = estimate_k_data(t, C, C0, C_eq)

        # Volume error: V ∝ 1/k  →  V_approx/V_data = k_data/k_approx
        vol_ratio   = k_data / K_APPROX_MIN
        vol_err_pct = (vol_ratio - 1.0) * 100.0

        # Capital cost error: C_cap = B*V^n  →  ratio = (V_approx/V_data)^n
        cost_ratio   = vol_ratio ** N_COST
        cost_err_pct = (cost_ratio - 1.0) * 100.0

        # MAPE at data points
        mape = float(np.mean(np.abs(pct_err)))

        summary_rows.append(
            {
                "label":             label,
                "SO4_level":         so4_level,
                "T_C":               int(temp),
                "C0_ppm":            C0,
                "C_eq_ppm":          C_eq,
                "k_approx_min":      K_APPROX_MIN,
                "k_data_min":        k_data,
                "k_ratio_data_approx": vol_ratio,
                "MAPE_pct":          mape,
                "vol_error_pct":     vol_err_pct,
                "cost_error_pct":    cost_err_pct,
            }
        )

        # ---- subplot ----
        ax = axes[idx]
        t_fine   = np.linspace(0, t.max(), 400)
        C_approx = approx_curve(t_fine, C0, C_eq)

        ax.scatter(t, C, color="steelblue", zorder=5, s=70, label="Data")
        ax.plot(
            t_fine, C_approx, color="tomato", linewidth=2,
            label=f"Approx (k={K_APPROX_S:.4e} s⁻¹)",
        )
        ax.axhline(C_eq, color="gray", linestyle="--", linewidth=1,
                   label=f"C_eq = {C_eq:.0f} ppm (data min)")

        # Residual tick marks at each measured point
        for ti, ci, ca in zip(t, C, C_approx_pts):
            ax.plot([ti, ti], [ci, ca], color="tomato", linewidth=0.9,
                    alpha=0.55, linestyle=":")

        ax.set_title(label, fontsize=11, fontweight="bold")
        ax.set_xlabel("Time (min)")
        ax.set_ylabel("Li (ppm)")
        ax.legend(fontsize=8)
        ax.annotate(
            f"k_data = {k_data:.4f} min⁻¹\n"
            f"k_approx = {K_APPROX_MIN:.4f} min⁻¹\n"
            f"MAPE = {mape:.1f}%\n"
            f"ΔV = {vol_err_pct:+.1f}%\n"
            f"ΔCost = {cost_err_pct:+.1f}%",
            xy=(0.97, 0.97),
            xycoords="axes fraction",
            ha="right", va="top",
            fontsize=8.5,
            bbox=dict(boxstyle="round,pad=0.35", fc="white", alpha=0.88),
        )

    # ---- Summary table ----
    df_summary = pd.DataFrame(summary_rows)

    print("\n" + "=" * 85)
    print(
        f"{'Condition':<22} {'k_data':>10} {'k_approx':>10} {'k ratio':>8} "
        f"{'MAPE':>6}  {'ΔV (%)':>8}  {'ΔCost (%)':>10}"
    )
    print("=" * 85)
    for _, row in df_summary.iterrows():
        print(
            f"{row['label']:<22} {row['k_data_min']:>10.4f} "
            f"{row['k_approx_min']:>10.4f} {row['k_ratio_data_approx']:>8.2f} "
            f"{row['MAPE_pct']:>5.1f}%  {row['vol_error_pct']:>+8.1f}%  "
            f"{row['cost_error_pct']:>+10.1f}%"
        )
    print("=" * 85)
    print(
        f"\nPositive ΔV / ΔCost → approximation OVER-sizes reactor (conservative).\n"
        f"Negative ΔV / ΔCost → approximation UNDER-sizes reactor (unconservative).\n"
        f"\nReactor cost equation: C_cap = {B_COST:,.2f} × V^{N_COST}  "
        f"(Stainless, 300 psi, V in m³)\n"
        f"Volume relationship: V ∝ 1/k  →  ΔV = k_data/k_approx − 1\n"
        f"Cost relationship:   ΔCost = (k_data/k_approx)^{N_COST} − 1\n"
    )

    # ---- Finish figure ----
    for ax in axes[len(files):]:
        ax.set_visible(False)

    fig.suptitle(
        f"Li₂CO₃ Precipitation — Data vs. Current Approximation\n"
        f"k_approx = {K_APPROX_S:.4e} s⁻¹ = {K_APPROX_MIN:.5f} min⁻¹  |  "
        f"C_eq = min(data) per condition",
        fontsize=11, y=1.01,
    )
    fig.tight_layout()

    out_plot = os.path.join(OUT_DIR, "reaction_rate_fitting.png")
    fig.savefig(out_plot, dpi=150, bbox_inches="tight")
    print(f"Plot saved → {out_plot}")

    out_csv = os.path.join(OUT_DIR, "reaction_rate_results.csv")
    df_summary.to_csv(out_csv, index=False)
    print(f"Results saved → {out_csv}\n")

    return df_summary


if __name__ == "__main__":
    main()
