import os
import numpy as np
import glob
import csv
from scipy.interpolate import interp1d
import math
import matplotlib.pyplot as plt

# Hardcoded initial concentrations for Salar de Uyuni #1 (g/kg)
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

# Initial volume (m^3)
initial_volume = 1000

# Calculate initial mass of each ion (kg) in the pond
initial_masses = {}
for ion, conc_g_per_kg in initial_concentrations_g_per_kg.items():
    initial_masses[ion] = conc_g_per_kg * initial_volume * brine_density / 1000  # kg

# SOLIDS PRECIPITATION RATE CALCULATION

# Constants for precipitation rate calculation
salt_density_kg_m3 = 2200  # kg/m^3 Use packing density (or think differently)
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
thickness_m = cumulative_solids_kg / (salt_density_kg_m3 * pond_area_m2)
precip_rate_m_per_yr = thickness_m / evaporation_time_years
precip_rate_ft_per_yr = precip_rate_m_per_yr * 3.28084

# Reverse arrays so volume decreases from ~1000 to ~50
unique_volumes_solids = unique_volumes_solids[::-1]
precip_rate_ft_per_yr = precip_rate_ft_per_yr[::-1]
cumulative_solids_kg = cumulative_solids_kg[::-1]

# TDS FROM SOLID PHASE FORMED DATA
# Calculate initial total dissolved mass (kg)
initial_total_mass_kg = sum(initial_masses.values())
# Remaining dissolved mass at each volume (kg)
remaining_mass_kg = initial_total_mass_kg - cumulative_solids_kg
# TDS (g/L) at each volume
TDS = (remaining_mass_kg * 1000) / (unique_volumes_solids * 1000)  # g/L

# Print preview
print("Volume (m^3):", unique_volumes_solids[:40])
print("TDS (g/L):", TDS[:40])

# Print precipitation rate preview
print("\nSolid Precipitation Rate (ft/yr) vs. Volume (m^3):")
print("Volume (m^3):", unique_volumes_solids[:40])
print("Precipitation Rate (ft/yr):", precip_rate_ft_per_yr[:40])

# FITTING PRECIPITATION RATE AS FUNCTION OF TDS

# Precipitation rate and TDS are now on the same volume grid
# Fit quadratic: precip_rate = a1 * TDS**2 + a2 * TDS + intercept
coeffs = np.polyfit(TDS, precip_rate_ft_per_yr, 2)
a1, a2, intercept = coeffs

print("\nFitted coefficients for: precipitation_rate = a1 * TDS**2 + a2 * TDS + intercept")
print(f"a1 = {a1}")
print(f"a2 = {a2}")
print(f"intercept = {intercept}")

# PLOTTING

fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))

# Plot 1: TDS as a function of water volume
ax1.plot(unique_volumes_solids, TDS, 'm-', linewidth=2, label='TDS (from solids)')
ax1.set_xlabel('Water Volume (m³)')
ax1.set_ylabel('Total Dissolved Solids (g/L)')
ax1.set_title('TDS vs Water Volume')
ax1.grid(True, alpha=0.3)
ax1.legend()

# Plot 2: Solid precipitation rate as a function of water volume
ax2.plot(unique_volumes_solids, precip_rate_ft_per_yr, 'r-', linewidth=2, label='Precipitation Rate')
ax2.set_xlabel('Water Volume (m³)')
ax2.set_ylabel('Solid Precipitation Rate (ft/yr)')
ax2.set_title('Solid Precipitation Rate vs Water Volume')
ax2.grid(True, alpha=0.3)
ax2.legend()

# Plot 3: Solid precipitation rate as a function of TDS
ax3.plot(TDS, precip_rate_ft_per_yr, 'g-', linewidth=2, label='Data')
# Plot fitted curve
TDS_fit = np.linspace(np.min(TDS), np.max(TDS), 100)
precip_fit = a1 * TDS_fit**2 + a2 * TDS_fit + intercept
ax3.plot(TDS_fit, precip_fit, 'k--', linewidth=2, label=f'Fitted: {a1:.2e}TDS² + {a2:.2e}TDS + {intercept:.2e}')
ax3.set_xlabel('Total Dissolved Solids (g/L)')
ax3.set_ylabel('Solid Precipitation Rate (ft/yr)')
ax3.set_title('Solid Precipitation Rate vs TDS')
ax3.grid(True, alpha=0.3)
ax3.legend()

plt.tight_layout()
plt.show()

# Save the plot
plt.savefig('precipitation_analysis_plots.png', dpi=300, bbox_inches='tight')
print("\nPlots saved as 'precipitation_analysis_plots.png'")
