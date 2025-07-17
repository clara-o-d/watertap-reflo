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
    solid_files = [f for f in os.listdir(solid_phase_dir) if f.endswith('.csv') and f != 'Solid Phase Formed.csv']
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
    brine_density = 1269  # kg/m^3
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
    master_vols, cumulative_dry_salt_mass, incremental_dry_salt_mass = get_precipitation_vs_volume(solid_phase_dir)
    master_vols, TDS = get_tds_vs_volume(master_vols, cumulative_dry_salt_mass)

    # Diagnostics for mass balance
    initial_total_mass_kg = sum([
        0.65, 82.1, 12.3, 13.1, 2.6, 171.2, 16.6, 3.5, 0.22
    ]) * 1000 * 1200 / 1000  # sum(g/kg) * m3 * density / 1000
    print(f"Initial total dissolved mass (kg): {initial_total_mass_kg}")
    print(f"Total incremental dry salt mass (kg): {np.sum(np.diff(np.insert(cumulative_dry_salt_mass, 0, 0)))}")
    print(f"Max cumulative dry salt mass (kg): {np.max(cumulative_dry_salt_mass)}")
    print(f"Min remaining dissolved mass (kg): {np.min(initial_total_mass_kg - cumulative_dry_salt_mass)}")
    if np.any(cumulative_dry_salt_mass > initial_total_mass_kg):
        print("WARNING: Cumulative dry salt mass exceeds initial total dissolved mass! This will cause negative TDS.")

    # For TDS, use the left volume's TDS for each interval
    TDS_mid = TDS[:-1]
    precip_kg = incremental_dry_salt_mass[1:]
    vols_mid = master_vols[1:]  # Corresponding volumes for precipitation data
    cumulative_precip_kg = cumulative_dry_salt_mass[1:]  # Cumulative precipitation data

    # Fit quadratic: precip_kg = a1 * TDS^2 + a2 * TDS + intercept
    fit_mask = (TDS_mid > 0) & (precip_kg > 0)
    TDS_fit = TDS_mid[fit_mask]
    precip_fit = precip_kg[fit_mask]
    coeffs = np.polyfit(TDS_fit, precip_fit, 2)
    a1, a2, intercept = coeffs
    fit_curve = a1 * TDS_fit**2 + a2 * TDS_fit + intercept

    # Fit cumulative precipitation vs water volume
    # Linear fit
    vol_fit_mask = (vols_mid > 0) & (cumulative_precip_kg > 0)
    vol_fit = vols_mid[vol_fit_mask]
    cumulative_precip_vol_fit = cumulative_precip_kg[vol_fit_mask]
    
    # Linear fit: cumulative_precip = a * volume + b
    linear_coeffs = np.polyfit(vol_fit, cumulative_precip_vol_fit, 1)
    slope, intercept = linear_coeffs
    vol_linear_curve = slope * vol_fit + intercept
    
    # Calculate R-squared for linear fit
    def r_squared(y_true, y_pred):
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        return 1 - (ss_res / ss_tot)
    
    r2_linear = r_squared(cumulative_precip_vol_fit, vol_linear_curve)

    # Plotting
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
    
    # (1) TDS vs water volume
    ax1.plot(master_vols, TDS, 'm-', linewidth=2, label='TDS (from dry salts)')
    ax1.set_xlabel('Water Volume (m³)')
    ax1.set_ylabel('Total Dissolved Solids (g/L)')
    ax1.set_title('TDS vs Water Volume')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.set_xlim(1000, 0)
    
    # (2) Incremental precipitation (kg) vs water volume
    ax2.plot(master_vols[1:], precip_kg, 'b-', linewidth=2, label='Incremental Precipitation (kg)')
    ax2.set_xlabel('Water Volume (m³)')
    ax2.set_ylabel('Incremental Precipitation (kg)')
    ax2.set_title('Incremental Precipitation vs Water Volume')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    ax2.set_xlim(1000, 0)
    
    # (3) Incremental precipitation (kg) vs TDS (with fit)
    ax3.plot(TDS_mid, precip_kg, 'go', markersize=3, label='Incremental Precipitation (kg)')
    ax3.plot(TDS_fit, fit_curve, 'k-', linewidth=2, label=f'Fit: {a1:.2e}*C² + {a2:.2e}*C + {intercept:.2e}')
    ax3.set_xlabel('TDS (g/L)')
    ax3.set_ylabel('Incremental Precipitation (kg)')
    ax3.set_title('Incremental Precipitation vs TDS')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # (4) Cumulative precipitation (kg) vs water volume (with fits)
    ax4.plot(vols_mid, cumulative_precip_kg, 'ro', markersize=3, label='Cumulative Precipitation (kg)')
    ax4.plot(vol_fit, vol_linear_curve, 'b-', linewidth=2, 
             label=f'Linear: {slope:.2e}*V + {intercept:.2e}\nR² = {r2_linear:.4f}')
    ax4.set_xlabel('Water Volume (m³)')
    ax4.set_ylabel('Cumulative Precipitation (kg)')
    ax4.set_title('Cumulative Precipitation vs Water Volume (with fit)')
    ax4.grid(True, alpha=0.3)
    ax4.legend()
    ax4.set_xlim(1000, 0)
    
    plt.tight_layout()
    plt.show()

    print(f"Quadratic fit (TDS): precipitation [kg] = {a1:.4e} * TDS^2 + {a2:.4e} * TDS + {intercept:.4e}")
    print(f"Linear fit (Volume): cumulative precipitation [kg] = {slope:.4e} * V + {intercept:.4e} (R² = {r2_linear:.4f})")
