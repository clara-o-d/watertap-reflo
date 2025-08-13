"""Precipitation analysis module for lithium extraction flowsheet.

Analyzes solid phase precipitation data and fits mathematical models to predict
precipitation behavior as a function of water volume and TDS concentration.
"""

import os
import numpy as np
import csv
import re
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

MOLAR_MASS_LOOKUP = {
    'NaCl_Halite': (22.990 + 35.453, 22.990 + 35.453),
    'MgSO4.7H2O_Epsomite': (24.305 + 32.06 + 4*15.999, 24.305 + 32.06 + 4*15.999 + 7*18.015),
    'MgSO4.1H2O_Kieserite': (24.305 + 32.06 + 4*15.999, 24.305 + 32.06 + 4*15.999 + 1*18.015),
    'MgCl2.6H2O_Bischofite': (24.305 + 2*35.453, 24.305 + 2*35.453 + 6*18.015),
    'MgB6O10.7.5H2O': (24.305 + 6*10.81 + 10*15.999, 24.305 + 6*10.81 + 10*15.999 + 7.5*18.015),
    'Li2SO4.H2O': (2*6.94 + 32.06 + 4*15.999, 2*6.94 + 32.06 + 4*15.999 + 18.015),
    'KCl.MgSO4.3H2O_Kainite': (39.098 + 35.45 + 24.305 + 32.06 + 4*15.999, 39.098 + 35.45 + 24.305 + 32.06 + 4*15.999 + 3*18.015),
    'KCl.MgCl2.6H2O_Carnallite': (39.098 + 35.45 + 24.305 + 2*35.453, 39.098 + 35.45 + 24.305 + 2*35.453 + 6*18.015),
    'KCl_sylvite': (39.098 + 35.45, 39.098 + 35.45),
    'K2SO4.MgSO4.2CaSO4.2H2O_Polyhalite': (2*39.098 + 32.06 + 4*15.999 + 24.305 + 32.06 + 4*15.999 + 2*(40.078 + 32.06 + 4*15.999), 2*39.098 + 32.06 + 4*15.999 + 24.305 + 32.06 + 4*15.999 + 2*(40.078 + 32.06 + 4*15.999) + 2*18.015),
    'K2SO4.CaSO4.1H2O_Syngenite': (2*39.098 + 32.06 + 4*15.999 + 40.078 + 32.06 + 4*15.999, 2*39.098 + 32.06 + 4*15.999 + 40.078 + 32.06 + 4*15.999 + 18.015),
    'K2SO4.5CaSO4.H2O_Gorgeyite': (2*39.098 + 32.06 + 4*15.999 + 5*(40.078 + 32.06 + 4*15.999), 2*39.098 + 32.06 + 4*15.999 + 5*(40.078 + 32.06 + 4*15.999) + 18.015),
    'CaSO4_Anhydrite': (40.078 + 32.06 + 4*15.999, 40.078 + 32.06 + 4*15.999),
    'B_OH_3': (10.81 + 3*(15.999 + 1.008), 10.81 + 3*(15.999 + 1.008)),
}

def get_precipitation_vs_volume(solid_phase_dir):
    """Extract precipitation data from solid phase CSV files.
    
    Args:
        solid_phase_dir: Directory containing solid phase CSV files
        
    Returns:
        tuple: (master_vols, cumulative_dry_salt_mass, incremental_dry_salt_mass)
    """
    solid_files = [
        f for f in os.listdir(solid_phase_dir)
        if f.endswith('.csv') and f not in {'Solid Phase Formed.csv', 'solid_phase_formed.csv'}
    ]
    # Find the file with the most steps to use as the master grid
    max_steps = 0
    master_vols = None
    for fname in solid_files:
        with open(os.path.join(solid_phase_dir, fname), 'r') as f:
            rows = [row for row in csv.reader(f) if len(row) >= 2]
            if len(rows) > max_steps:
                max_steps = len(rows)
                master_vols = np.array([float(row[0]) for row in rows])
    if master_vols is None:
        raise ValueError("No valid solid phase data found to define a master volume grid.")
    # Sum incremental dry salt mass for each step
    incremental_dry_salt_mass = np.zeros_like(master_vols)
    for fname in solid_files:
        salt_key = fname.replace('.csv', '')
        salt_key = salt_key.rstrip('_')  # Remove trailing underscores for matching
        if salt_key not in MOLAR_MASS_LOOKUP:
            raise ValueError(f"No molar mass entry for {salt_key}")
        M_anhydrous, M_hydrate = MOLAR_MASS_LOOKUP[salt_key]
        print(f"{salt_key}: M_anhydrous={M_anhydrous}, M_hydrate={M_hydrate}")
        with open(os.path.join(solid_phase_dir, fname), 'r') as f:
            reader = csv.reader(f)
            rows = [row for row in reader if len(row) >= 2]
            vols = np.array([float(row[0]) for row in rows])
            mass_mt = np.array([float(row[1]) for row in rows])
            mass_kg = mass_mt * 1000
            dry_mass_kg = mass_kg * (M_anhydrous / M_hydrate)
            for i, vol in enumerate(vols):
                closest_idx = np.argmin(np.abs(master_vols - vol))
                incremental_dry_salt_mass[closest_idx] += dry_mass_kg[i]
    # Ensure volumes are sorted in decreasing order for cumulative calculation
    if master_vols[0] < master_vols[-1]:
        master_vols = master_vols[::-1]
        incremental_dry_salt_mass = incremental_dry_salt_mass[::-1]
    cumulative_dry_salt_mass = np.cumsum(incremental_dry_salt_mass)
    return master_vols, cumulative_dry_salt_mass, incremental_dry_salt_mass

def get_tds_vs_volume(master_vols, cumulative_dry_salt_mass):
    """Calculate TDS concentration as a function of water volume.
    
    Args:
        master_vols: Array of water volumes
        cumulative_dry_salt_mass: Array of cumulative precipitated salt mass
        
    Returns:
        tuple: (master_vols, TDS)
    """
    initial_concentrations_g_per_kg = {
        'Li_+1_': 0.65,
        'Na_+1_': 82.1,
        'K_+1_': 12.3,
        'Mg_+2_': 13.1,
        'Ca_+2_': 2.6,
        'Cl_-1_': 171.2,
        'SO4_-2_': 16.6, 
        'B_OH_3_': 3.5,   
        'HCO3_-1_': 0.22,
    }
    brine_density = 1229  # kg/m^3
    initial_volume = 1000
    initial_masses = {}
    for ion, conc_g_per_kg in initial_concentrations_g_per_kg.items():
        initial_masses[ion] = conc_g_per_kg * initial_volume * brine_density / 1000  # kg
    initial_total_mass_kg = sum(initial_masses.values())
    remaining_mass_kg = initial_total_mass_kg - cumulative_dry_salt_mass
    TDS = (remaining_mass_kg * 1000) / (master_vols * 1000)  # g/L
    return master_vols, TDS

if __name__ == "__main__":
    folder = os.path.dirname(__file__)
    solid_phase_dir = os.path.join(folder, 'solid_phase_data')
    # Read aggregated precipitation data: evaporated volume (m^3), instantaneous precipitation (metric tons)
    solid_phase_file = os.path.join(solid_phase_dir, 'solid_phase_formed.csv')
    if not os.path.exists(solid_phase_file):
        raise FileNotFoundError(f"Missing file: {solid_phase_file}")

    data = []
    with open(solid_phase_file, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                try:
                    evap_vol = float(row[0])
                    inst_precip_mt = float(row[1])
                    data.append((evap_vol, inst_precip_mt))
                except ValueError:
                    continue

    if len(data) == 0:
        raise ValueError("No valid rows found in solid_phase_formed.csv")

    data = np.array(sorted(data, key=lambda x: x[0]))
    evaporated_volume_m3 = data[:, 0]
    inst_precip_mt = data[:, 1]

    initial_volume_m3 = 1000.0
    water_remaining_m3 = initial_volume_m3 - evaporated_volume_m3
    inst_precip_kg = inst_precip_mt * 1000.0
    cumulative_precip_kg = np.cumsum(inst_precip_kg)

    # Merge nearby points into 45 even steps between ~1000 and ~50 m^3 (by water remaining)
    num_steps = 45
    edges_asc = np.linspace(50.0, 1000.0, num_steps + 1)
    centers_asc = 0.5 * (edges_asc[:-1] + edges_asc[1:])
    incremental_per_bin_kg = np.zeros(num_steps)
    bin_indices = np.digitize(water_remaining_m3, edges_asc) - 1
    bin_indices = np.clip(bin_indices, 0, num_steps - 1)
    for idx_point, bin_idx in enumerate(bin_indices):
        incremental_per_bin_kg[bin_idx] += inst_precip_kg[idx_point]

    # Order bins from 1000 -> 50 to accumulate as water decreases
    V_plot = centers_asc[::-1]
    incremental_desc_kg = incremental_per_bin_kg[::-1]
    cum_kg_plot = np.cumsum(incremental_desc_kg)

    # Fit quadratic model only for portion past 130 m^3 remaining (i.e., V in [50, 130])
    fit_mask = (V_plot <= 130.0) & (V_plot >= 50.0)
    V_fit_data = V_plot[fit_mask]
    cum_kg_fit_data = cum_kg_plot[fit_mask]
    coeffs_quad = np.polyfit(V_fit_data, cum_kg_fit_data, 2)
    p_quad = np.poly1d(coeffs_quad)
    a_coef, b_coef, c_coef = coeffs_quad

    def r_squared(y_true, y_pred):
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        return 1 - (ss_res / ss_tot)

    r2_cum = r_squared(cum_kg_fit_data, p_quad(V_fit_data))

    target_V = 130.0
    cum_at_target_kg = float(p_quad(target_V))

    plt.figure(figsize=(8, 5))
    plt.plot(V_plot, cum_kg_plot, 'o', markersize=4, label='Cumulative precipitation (kg), binned (45 steps)')
    V_fit_line = np.linspace(130.0, 50.0, 200)
    plt.plot(
        V_fit_line,
        p_quad(V_fit_line),
        'r-',
        linewidth=2,
        label=(
            f'Quadratic fit on V∈[50,130]: '
            f'{a_coef:.3e}*V^2 + {b_coef:.3e}*V + {c_coef:.3e}\n'
            f'R² = {r2_cum:.4f}'
        ),
    )
    plt.scatter([target_V], [cum_at_target_kg], color='k', zorder=3,
                label=f'Estimate at V={target_V:.0f} m³: {cum_at_target_kg:.2f} kg')
    plt.xlabel('Water Remaining (m³)')
    plt.ylabel('Cumulative Precipitation (kg)')
    plt.title('Cumulative Precipitation vs Water Remaining')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.xlim(1000, 50)
    plt.tight_layout()
    plt.show()

    print(f"Cumulative precipitation quadratic fit (kg): C(V) = {coeffs_quad[0]:.6e}*V^2 + {coeffs_quad[1]:.6e}*V + {coeffs_quad[2]:.6e} (R² = {r2_cum:.4f})")
    print(f"Estimated cumulative precipitation at 130 m^3 remaining: {cum_at_target_kg:.3f} kg")
