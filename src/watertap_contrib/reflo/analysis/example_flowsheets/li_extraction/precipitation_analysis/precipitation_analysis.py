import os
import numpy as np
import csv
import re
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

# Simple periodic table for molar mass lookup (g/mol)
PERIODIC_TABLE = {
    'H': 1.0079,
    'O': 15.999,
    'Na': 22.9898,
    'Cl': 35.453,
    'Mg': 24.305,
    'S': 32.065,
    'K': 39.0983,
    'Ca': 40.078,
    'B': 10.81,
    'Li': 6.94,
    'C': 12.011,
}

def parse_formula(formula):
    parts = re.split(r'[_.]', formula)
    elements = {}
    for part in parts:
        matches = re.findall(r'([A-Z][a-z]*)([0-9\.]*)(?=[A-Z]|$)', part)
        for elem, count in matches:
            if count == '' or count == '.':
                count = 1
            else:
                count = float(count)
            elements[elem] = elements.get(elem, 0) + count
    return elements

def molar_mass(formula):
    elements = parse_formula(formula)
    mass = 0.0
    for elem, count in elements.items():
        if elem not in PERIODIC_TABLE:
            raise ValueError(f"Element {elem} not in periodic table.")
        mass += PERIODIC_TABLE[elem] * count
    return mass

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
        salt_formula = fname.replace('.csv', '')
        salt_formula = re.sub(r'_[^_]*_$', '', salt_formula)
        hydrate_match = re.search(r'(.*?)([0-9]*\.?[0-9]*)H2O', salt_formula)
        if hydrate_match:
            base_formula = hydrate_match.group(1).rstrip('.')
            n_h2o = float(hydrate_match.group(2)) if hydrate_match.group(2) else 1.0
            hydrate_formula = f"{base_formula}{n_h2o}H2O"
            anhydrous_formula = base_formula
        else:
            anhydrous_formula = salt_formula
            n_h2o = 0.0
            hydrate_formula = salt_formula
        try:
            M_hydrate = molar_mass(hydrate_formula)
        except Exception:
            M_hydrate = molar_mass(salt_formula)
        M_anhydrous = molar_mass(anhydrous_formula)
        with open(os.path.join(solid_phase_dir, fname), 'r') as f:
            reader = csv.reader(f)
            rows = [row for row in reader if len(row) >= 2]
            vols = np.array([float(row[0]) for row in rows])
            mass_mt = np.array([float(row[1]) for row in rows])
            mass_kg = mass_mt * 1000
            dry_mass_kg = mass_kg * (M_anhydrous / M_hydrate)
            interp_func = interp1d(vols, dry_mass_kg, kind='linear', bounds_error=False, fill_value=0.0)
            dry_mass_on_master = interp_func(master_vols)
            incremental_dry_salt_mass += dry_mass_on_master
    # Compute cumulative sum as volume decreases
    if master_vols[0] < master_vols[-1]:
        cumulative_dry_salt_mass = np.cumsum(incremental_dry_salt_mass[::-1])[::-1]
    else:
        cumulative_dry_salt_mass = np.cumsum(incremental_dry_salt_mass)
    return master_vols, cumulative_dry_salt_mass

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
    brine_density = 1200  # kg/m^3
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
    master_vols, cumulative_dry_salt_mass = get_precipitation_vs_volume(solid_phase_dir)
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

    # Plotting
    fig, ax1 = plt.subplots(figsize=(7, 5))
    ax1.plot(master_vols, TDS, 'm-', linewidth=2, label='TDS (from dry salts)')
    ax1.set_xlabel('Water Volume (m³)')
    ax1.set_ylabel('Total Dissolved Solids (g/L)')
    ax1.set_title('TDS vs Water Volume')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.set_xlim(1000, 0)
    plt.tight_layout()
    plt.show()
