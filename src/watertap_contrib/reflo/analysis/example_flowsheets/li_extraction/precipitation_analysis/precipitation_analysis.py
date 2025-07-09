import os
import numpy as np
import glob
import csv
from scipy.interpolate import interp1d
import math

# Hardcoded initial concentrations for Salar de Uyuni #1 (g/kg)
# Only include ions for which we have CSVs
initial_concentrations_g_per_kg = {
    'Li_+1_': 0.65,
    'Na_+1_': 82.1,
    'K_+1_': 12.3,
    'Mg_+2_': 13.1,
    'Ca_+2_': 2.6,
    'Cl_-1_': 171.2,
    'B_+3_': 3.5,
}

# Use the correct brine density (kg/m^3)
brine_density = 1200  # kg/m^3

folder = os.path.dirname(__file__)
ion_files = [f for f in os.listdir(folder) if f.endswith('.csv') and f != 'Solid Phase Formed.csv']

# Read all ion data into a dict: {ion: (volumes, fractions)}
ion_data = {}
all_volumes = set()
for ion_file in ion_files:
    ion_name = ion_file.replace('.csv', '')
    if ion_name not in initial_concentrations_g_per_kg:
        continue  # skip ions not in the initial concentration dict
    volumes = []
    fractions = []
    with open(os.path.join(folder, ion_file), 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            v, frac = float(row[0]), float(row[1])
            volumes.append(v)
            fractions.append(frac / 100.0)  # convert % to fraction
            all_volumes.add(v)
    ion_data[ion_name] = (np.array(volumes), np.array(fractions))

# Build a sorted array of all unique volume points
all_volumes = np.array(sorted(all_volumes))

# Initial volume (m^3)
initial_volume = 1000

# Calculate initial mass of each ion (kg) in the pond
# initial_concentration (g/kg) * initial_volume (m^3) * brine_density (kg/m^3) = g -> /1000 = kg
initial_masses = {}
for ion, conc_g_per_kg in initial_concentrations_g_per_kg.items():
    initial_masses[ion] = conc_g_per_kg * initial_volume * brine_density / 1000  # kg

# Interpolate each ion's fraction-remaining to all_volumes
interpolated_fractions = {}
for ion, (vols, fracs) in ion_data.items():
    # Extrapolate with nearest value to avoid NaNs outside range
    interp_func = interp1d(vols, fracs, kind='linear', bounds_error=False, fill_value=fracs[0])
    right_interp_func = interp1d(vols, fracs, kind='linear', bounds_error=False, fill_value=fracs[-1])
    interp_vals = interp_func(all_volumes)
    # For values above the max, use the last value
    interp_vals[all_volumes > np.max(vols)] = fracs[-1]
    # For values below the min, use the first value
    interp_vals[all_volumes < np.min(vols)] = fracs[0]
    interpolated_fractions[ion] = interp_vals

# Find the intersection of all ions' volume ranges
ion_min_vols = [np.min(vols) for vols, _ in ion_data.values()]
ion_max_vols = [np.max(vols) for vols, _ in ion_data.values()]
valid_min_volume = max(ion_min_vols)
valid_max_volume = min(ion_max_vols)

# Restrict all_volumes to the safe range
valid_mask = (all_volumes >= valid_min_volume) & (all_volumes <= valid_max_volume)
all_volumes_valid = all_volumes[valid_mask]

# For each ion, restrict interpolated fractions to valid range and clip to [0, 1]
interpolated_fractions_valid = {}
for ion, vals in interpolated_fractions.items():
    clipped = np.clip(vals[valid_mask], 0, 1)
    interpolated_fractions_valid[ion] = clipped

# For each volume step, calculate total dissolved mass and TDS (in valid range)
TDS = []  # g/L
for i, v in enumerate(all_volumes_valid):
    total_mass_kg = 0.0
    for ion in initial_concentrations_g_per_kg:
        frac = interpolated_fractions_valid[ion][i]
        mass = initial_masses[ion] * frac
        total_mass_kg += mass
    tds_g_per_L = total_mass_kg * 1000 / (v * 1000)
    TDS.append(tds_g_per_L)
TDS = np.array(TDS)

# Reverse arrays so volume decreases
all_volumes_valid = all_volumes_valid[::-1]
TDS = TDS[::-1]

# Print preview
print("Volume (m^3):", all_volumes_valid[:40])
print("TDS (g/L):", TDS[:40])

# --- SOLIDS PRECIPITATION RATE CALCULATION ---

# Constants for precipitation rate calculation
salt_density_kg_m3 = 2200  # kg/m^3
pond_area_m2 = 25550000    # m^2
evaporation_time_months = 15
months_to_years = 12

evaporation_time_years = evaporation_time_months / months_to_years

# Read Solid Phase Formed.csv (volume, solids precipitated in metric tons)
solids_file = os.path.join(folder, 'Solid Phase Formed.csv')
solids_data = []
with open(solids_file, 'r') as f:
    reader = csv.reader(f)
    for row in reader:
        v = float(row[0])
        s = float(row[1])
        solids_data.append((v, s))
solids_data = np.array(solids_data)

# Group by unique volume, sum solids precipitated at each volume
from collections import defaultdict
grouped_solids = defaultdict(float)
for v, s in solids_data:
    grouped_solids[v] += s
unique_volumes_solids = np.array(sorted(grouped_solids.keys()))
total_solids_mt = np.array([grouped_solids[v] for v in unique_volumes_solids])  # metric tons

# Convert metric tons to kg
solids_kg = total_solids_mt * 1000

# Calculate cumulative solids precipitated (kg) as volume decreases
cumulative_solids_kg = np.cumsum(solids_kg[::-1])[::-1]  # reverse cumsum so it matches decreasing volume

# Calculate precipitation rate (thickness per year)
# thickness = mass / (density * area) [m]
# rate = thickness / evaporation_time_years [m/yr], then convert to ft/yr
thickness_m = cumulative_solids_kg / (salt_density_kg_m3 * pond_area_m2)
precip_rate_m_per_yr = thickness_m / evaporation_time_years
precip_rate_ft_per_yr = precip_rate_m_per_yr * 3.28084

# Reverse arrays so volume decreases from ~1000 to ~50
unique_volumes_solids = unique_volumes_solids[::-1]
precip_rate_ft_per_yr = precip_rate_ft_per_yr[::-1]

# Print preview
print("\nSolid Precipitation Rate (ft/yr) vs. Volume (m^3):")
print("Volume (m^3):", unique_volumes_solids[:40])
print("Precipitation Rate (ft/yr):", precip_rate_ft_per_yr[:40])

# --- FITTING PRECIPITATION RATE AS FUNCTION OF TDS ---

# Interpolate precipitation rate to TDS volume points (or vice versa) for matching arrays
from scipy.interpolate import interp1d

# Find overlapping volume range
min_overlap = max(np.min(all_volumes_valid), np.min(unique_volumes_solids))
max_overlap = min(np.max(all_volumes_valid), np.max(unique_volumes_solids))

# Mask for overlapping range
tds_mask = (all_volumes_valid >= min_overlap) & (all_volumes_valid <= max_overlap)
solids_mask = (unique_volumes_solids >= min_overlap) & (unique_volumes_solids <= max_overlap)

# Interpolate precipitation rate to TDS volume points in overlap
precip_interp_func = interp1d(
    unique_volumes_solids[solids_mask],
    precip_rate_ft_per_yr[solids_mask],
    kind='linear',
    bounds_error=False,
    fill_value=precip_rate_ft_per_yr[solids_mask][0]
)
precip_rate_aligned = precip_interp_func(all_volumes_valid[tds_mask])
# Manually set right-side extrapolation to last value
right_val = precip_rate_ft_per_yr[solids_mask][-1]
right_mask = all_volumes_valid[tds_mask] > unique_volumes_solids[solids_mask][-1]
precip_rate_aligned[right_mask] = right_val
TDS_aligned = TDS[tds_mask]

# Fit quadratic: precip_rate = a1 * TDS**2 + a2 * TDS + intercept
coeffs = np.polyfit(TDS_aligned, precip_rate_aligned, 2)
a1, a2, intercept = coeffs

print("\nFitted coefficients for: precipitation_rate = a1 * TDS**2 + a2 * TDS + intercept")
print(f"a1 = {a1}")
print(f"a2 = {a2}")
print(f"intercept = {intercept}")
