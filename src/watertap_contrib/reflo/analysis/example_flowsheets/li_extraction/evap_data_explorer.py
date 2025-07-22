import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.patches import Patch

# Load data
df = pd.read_csv('evap_sensitivity.csv')

xvals = np.sort(df['target_li_concentration (g/kg)'].unique())
yvals = np.sort(df['conc_li_inlet (kg/m3)'].unique())
rho_vals = np.sort(df['rho (kg/m3)'].unique())

n_rho = len(rho_vals)
fig = plt.figure(figsize=(4.5*n_rho, 5))
bar_width = (xvals[1] - xvals[0]) * 0.6 if len(xvals) > 1 else 0.02
bar_depth = (yvals[1] - yvals[0]) * 0.6 if len(yvals) > 1 else 0.02

for i, rho in enumerate(rho_vals):
    subdf = df[df['rho (kg/m3)'] == rho]
    xpos, ypos = np.meshgrid(xvals, yvals, indexing='ij')
    xpos = xpos.ravel()
    ypos = ypos.ravel()
    zvals = []
    colors = []
    lcoli_vals = []
    for x, y in zip(xpos, ypos):
        mask = (subdf['target_li_concentration (g/kg)'] == x) & (subdf['conc_li_inlet (kg/m3)'] == y)
        lcoli = subdf.loc[mask, 'levelized cost of lithium (USD_2023/m^3)']
        if not lcoli.empty and not np.isnan(lcoli.values[0]):
            zvals.append(lcoli.values[0])
            colors.append('#3b82f6')  # blue for valid
            lcoli_vals.append(lcoli.values[0])
        else:
            zvals.append(0.1)
            colors.append('#ef4444')  # red for NaN
            lcoli_vals.append(np.nan)
    zvals = np.array(zvals)
    lcoli_vals_arr = np.array([v for v in lcoli_vals if not np.isnan(v)])
    median_label = ''
    median_x = median_y = median_z = None
    if len(lcoli_vals_arr) > 0:
        median_val = np.median(lcoli_vals_arr)
        # Find the index of the bar closest to the median (first occurrence)
        median_idx = None
        min_diff = np.inf
        for idx, v in enumerate(zvals):
            if not np.isnan(v) and colors[idx] == '#3b82f6':
                diff = abs(v - median_val)
                if diff < min_diff:
                    min_diff = diff
                    median_idx = idx
        if median_idx is not None:
            colors[median_idx] = 'orange'
            median_x = xpos[median_idx]
            median_y = ypos[median_idx]
            median_z = zvals[median_idx]
            median_label = f"Median LCOLi = {median_z:.2f} (x={median_x}, y={median_y}) [USD_2023/mt Li]"
    ax = fig.add_subplot(1, n_rho, i+1, projection='3d')
    ax.bar3d(xpos, ypos, np.zeros_like(zvals), bar_width, bar_depth, zvals, color=colors, alpha=0.8, shade=True)
    ax.set_xlabel('Target Li Concentration (g/kg)')
    ax.set_ylabel('Inlet Li Concentration (kg/m3)')
    ax.set_zlabel('LCOLi (USD_2023/m^3)')
    ax.set_title(f'rho = {rho} kg/m3')
    if median_label:
        # Place label well below the plot (z negative)
        xmid = np.mean(xvals)
        ymid = np.mean(yvals)
        zmin = -1 * max(zvals)
        ax.text(xmid, ymid, zmin, median_label, color='black', fontsize=10, ha='center', va='top', weight='bold', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.2'))

legend_elements = [
    Patch(facecolor='#3b82f6', label='Valid LCOLi'),
    Patch(facecolor='#ef4444', label='Missing (NaN)'),
    Patch(facecolor='orange', label='Median LCOLi')
]
fig.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.98, 0.98))
plt.tight_layout()
plt.show() 