"""Cost comparison visualization for lithium carbonate processing flowsheet.

Compares WaterTAP model capital cost breakdown (by unit model) against
SQM reported capital costs (Table 1.1 – Lithium Carbonate Plant, $521.64M in 2020 USD).

The WaterTAP bar separates direct equipment costs from the TIC (Total Installed Cost)
indirect overhead. Direct costs are grouped into SQM-matching categories (tanks, filters,
pumps) with reactors kept individual. The indirect pool is split into Buildings, Piping,
and Electrical using SQM proportions.
"""

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np


# ---------------------------------------------------------------------------
# WaterTAP capital cost breakdown (USD 2023, from flowsheet solve)
# These values already include TIC = 2.0, so direct = value / 2.0
# ---------------------------------------------------------------------------
WATERTAP_CAPEX = {
    "Storage tank":               291_988,
    "Brine pump":                  27_400,
    "Second pump":                201_219,
    "Soda ash reactor":        37_607_768,
    "Lime reactor":            33_337_850,
    "Li\u2082CO\u2083 reactor": 24_392_529,
    "Soda ash vacuum filter":     385_890,
    "Soda ash centrifuge":      3_882_001,
    "Lime press filter":        7_633_556,
    "Lime centrifuge":          2_789_429,
    "Li dewatering":           15_863_431,
}

TIC = 2.0

# Groupings of WaterTAP unit models into SQM-matching direct-cost categories.
# Keys are the display label; values are lists of WATERTAP_CAPEX keys to sum.
DIRECT_GROUPS = {
    "Tanks (TK)":              [
        "Soda ash reactor",
        "Lime reactor",
        "Li\u2082CO\u2083 reactor",
    ],
    "Filters & centrifuges":   [
        "Soda ash vacuum filter",
        "Soda ash centrifuge",
        "Lime press filter",
        "Lime centrifuge",
        "Li dewatering",
    ],
    "Centrifugal pumps":       ["Brine pump", "Second pump"],
    "Ponds":                   ["Storage tank"],
}

# Indirect cost breakdown fractions (from SQM indirect categories,
# normalized so they sum to 1.0 across the indirect pool).
# SQM indirect items (buildings + piping + electrical) total 50% of SQM capex,
# matching the 50% indirect share when TIC = 2.
INDIRECT_FRACTIONS = {
    "Buildings":                              0.28 / 0.50,
    "Piping, pumps, valves":                  0.15 / 0.50,
    "Electrical, instrumentation\n& control": 0.07 / 0.50,
}

# ---------------------------------------------------------------------------
# SQM capital cost breakdown (2020 USD, Table 10-4)
# ---------------------------------------------------------------------------
SQM_TOTAL_CAPEX_M = 521.64  # $M USD 2020

SQM_CAPEX_PCT = {
    "Buildings":                              0.28,
    "Filters & microfilter system":           0.16,
    "Piping, pumps, valves":                  0.15,
    "Ponds":                                  0.11,
    "Centrifugal pumps":                      0.08,
    "Electrical, instrumentation & control":  0.07,
    "Tanks (TK)":                             0.05,
    "Others":                                 0.10,
}



def create_cost_comparison_plot():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    ax1.set_frame_on(False)
    ax2.set_frame_on(False)

    fig.suptitle(
        "Capital Cost Comparison: WaterTAP Li\u2082CO\u2083 Model vs SQM Reported",
        fontsize=13, fontweight="bold", y=0.99,
    )

    width = 0.25
    x = 0.2

    # One color per SQM category, indexed by position
    sqm_colors = {label: plt.cm.Paired(i) for i, label in enumerate(SQM_CAPEX_PCT)}

    # -----------------------------------------------------------------------
    # Compute WaterTAP cost values
    # -----------------------------------------------------------------------
    wt_total = sum(WATERTAP_CAPEX.values())
    wt_total_M = wt_total / 1e6

    grouped_direct_M = {
        label: sum(WATERTAP_CAPEX[k] for k in keys) / TIC / 1e6
        for label, keys in DIRECT_GROUPS.items()
    }
    total_indirect_M = wt_total_M - sum(grouped_direct_M.values())
    indirect_costs_M = {
        label: total_indirect_M * frac
        for label, frac in INDIRECT_FRACTIONS.items()
    }

    # Map WaterTAP values onto the canonical SQM category order.
    # Each entry: (wt_value_M, wt_display_label, is_indirect)
    # Categories absent from WaterTAP get value 0 and label None (skipped in legend).
    wt_by_sqm = {
        "Buildings":                             (indirect_costs_M["Buildings"],
                                                  "Buildings (indirect)", True),
        "Filters & microfilter system":          (grouped_direct_M["Filters & centrifuges"],
                                                  "Filters & centrifuges", False),
        "Piping, pumps, valves":                 (indirect_costs_M["Piping, pumps, valves"],
                                                  "Piping, pumps, valves (indirect)", True),
        "Ponds":                                 (grouped_direct_M["Ponds"],
                                                  "Ponds", False),
        "Centrifugal pumps":                     (grouped_direct_M["Centrifugal pumps"],
                                                  "Centrifugal pumps", False),
        "Electrical, instrumentation & control": (indirect_costs_M["Electrical, instrumentation\n& control"],
                                                  "Electrical (indirect)", True),
        "Tanks (TK)":                            (grouped_direct_M["Tanks (TK)"],
                                                  "Tanks / Reactors", False),
        "Others":                                (0.0, None, False),
    }

    sqm_total_M = SQM_TOTAL_CAPEX_M
    y_max = max(wt_total_M, sqm_total_M) * 1.18

    # -----------------------------------------------------------------------
    # Left plot – WaterTAP (stacked in SQM category order)
    # -----------------------------------------------------------------------
    bars_wt = []
    bottom = 0.0
    for sqm_cat, (val, wt_lbl, is_indirect) in wt_by_sqm.items():
        if val == 0:
            continue
        color = sqm_colors[sqm_cat]
        kw = dict(hatch="//", alpha=0.85) if is_indirect else {}
        bar = ax1.bar(x, val, width, bottom=bottom, color=color,
                      edgecolor="white", linewidth=0.5, **kw)
        bars_wt.append((bar, wt_lbl, val, is_indirect))
        bottom += val

    ax1.scatter(x, wt_total_M, color="gold", s=80, zorder=5, edgecolors="black", linewidths=0.8)
    ax1.axhline(wt_total_M, color="black", linestyle=":", linewidth=1.5, alpha=0.6)
    ax1.set_ylabel("Capital Cost (USD millions)", fontsize=10)
    ax1.set_xticks([x])
    ax1.set_xticklabels(["WaterTAP Model\n(USD 2023)"], fontsize=11)
    ax1.set_xlim(0, 0.6)
    ax1.set_ylim(0, y_max)
    ax1.tick_params(axis="both", labelsize=9)
    ax1.grid(axis="y", alpha=0.3, linestyle="--")
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:.0f}M"))

    direct_bars  = [(b, l, v) for b, l, v, ind in bars_wt if not ind]
    indirect_bars = [(b, l, v) for b, l, v, ind in bars_wt if ind]

    legend_handles = [Line2D([0], [0], color="none", markersize=0)]
    legend_labels  = ["DIRECT EQUIPMENT COSTS"]
    for bar, lbl, val in direct_bars:
        legend_handles.append(bar)
        legend_labels.append(f"{lbl}  (${val:.1f}M, {val/wt_total_M*100:.0f}%)")
    legend_handles.append(Line2D([0], [0], color="none", markersize=0))
    legend_labels.append("INDIRECT COSTS (TIC overhead)")
    for bar, lbl, val in indirect_bars:
        legend_handles.append(bar)
        legend_labels.append(f"{lbl}  (${val:.1f}M, {val/wt_total_M*100:.0f}%)")
    legend_handles.append(Line2D([0], [0], marker="o", color="gold",
                                  markeredgecolor="black", markersize=7, linestyle="none"))
    legend_labels.append(f"Total: ${wt_total_M:.2f}M")
    ax1.legend(legend_handles, legend_labels, loc="upper right",
               frameon=True, fancybox=True, shadow=True, fontsize=6.8)

    # -----------------------------------------------------------------------
    # Right plot – SQM (same canonical order)
    # -----------------------------------------------------------------------
    bars_sqm = []
    bottom = 0.0
    for sqm_cat, pct in SQM_CAPEX_PCT.items():
        val = SQM_TOTAL_CAPEX_M * pct
        bar = ax2.bar(x, val, width, bottom=bottom, color=sqm_colors[sqm_cat],
                      edgecolor="white", linewidth=0.5)
        bars_sqm.append((bar, sqm_cat, val))
        bottom += val

    ax2.scatter(x, sqm_total_M, color="gold", s=80, zorder=5, edgecolors="black", linewidths=0.8)
    ax2.axhline(sqm_total_M, color="black", linestyle=":", linewidth=1.5, alpha=0.6)
    ax2.set_ylabel("Capital Cost (USD millions, 2020)", fontsize=10)
    ax2.set_xticks([x])
    ax2.set_xticklabels(["SQM Reported\n(USD 2020)"], fontsize=11)
    ax2.set_xlim(0, 0.6)
    ax2.set_ylim(0, y_max)
    ax2.tick_params(axis="both", labelsize=9)
    ax2.grid(axis="y", alpha=0.3, linestyle="--")
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:.0f}M"))

    legend_handles = [Line2D([0], [0], color="none", markersize=0)]
    legend_labels  = ["CATEGORIES"]
    for bar, lbl, val in bars_sqm:
        legend_handles.append(bar)
        legend_labels.append(f"{lbl}  (${val:.0f}M, {val/sqm_total_M*100:.0f}%)")
    legend_handles.append(Line2D([0], [0], marker="o", color="gold",
                                  markeredgecolor="black", markersize=7, linestyle="none"))
    legend_labels.append(f"Total: ${sqm_total_M:.1f}M")
    ax2.legend(legend_handles, legend_labels, loc="upper right",
               frameon=True, fancybox=True, shadow=True, fontsize=7.2)

    plt.tight_layout()
    return fig, (ax1, ax2)


def main():
    wt_total = sum(WATERTAP_CAPEX.values())
    total_indirect = wt_total * (1 - 1 / TIC)

    print("WaterTAP Capital Cost Breakdown:")
    print(f"  TIC factor: {TIC}")
    print("  Direct equipment costs (grouped, capital / TIC):")
    for label, keys in DIRECT_GROUPS.items():
        group_total = sum(WATERTAP_CAPEX[k] for k in keys) / TIC
        members = ", ".join(keys)
        print(f"    {label}  [${group_total:,.0f}]  ({members})")
    print(f"  Total direct: ${wt_total/TIC:,.0f}")
    print("  Indirect costs (TIC overhead):")
    for label, frac in INDIRECT_FRACTIONS.items():
        print(f"    {label.replace(chr(10), ' ')}: ${total_indirect * frac:,.0f}")
    print(f"  Total indirect: ${total_indirect:,.0f}")
    print(f"  GRAND TOTAL: ${wt_total:,.0f}")

    print(f"\nSQM Capital Cost Breakdown (2020 USD):")
    for k, v in SQM_CAPEX_PCT.items():
        print(f"  {k}: ${SQM_TOTAL_CAPEX_M * v:.1f}M  ({v*100:.0f}%)")
    print(f"  TOTAL: ${SQM_TOTAL_CAPEX_M:.2f}M")

    fig, axes = create_cost_comparison_plot()
    plt.show()


if __name__ == "__main__":
    main()
