"""Results comparison visualization for lithium extraction flowsheet.

Creates cost comparison plots between industry reports and WaterTAP model results.
"""

import matplotlib.pyplot as plt
import numpy as np

# Sample data - you can replace these with your actual values
categories = ['Industry report\n(2020)', 'WaterTAP model\n(2022)']

# Cost breakdown ($/kg Li or whatever units you're using)
levelized_costs = np.array([2.0248e+03,  3.3767e+03])
capital_costs = np.array([941.7290, 1.0673e+03])
operating_costs = np.array([4.2312e+03, 4.9722e+03])
revenue = np.array([3.1482e+03, 2.6629e+03])

# Colors as specified
capex_color = '#4198b5'
opex_color = '#610059' 
revenue_color = '#165d54'
dot_color = '#279989'

# Set up the plot
fig, ax = plt.subplots(figsize=(4.25, 5))

# Width of bars
width = 0.25
# Bring bars closer together by further reducing spacing between category centers
x = np.arange(len(categories)) * 0.4

# Create stacked bars
bars1 = ax.bar(x, capital_costs, width, label='Capital cost', color=capex_color)
bars2 = ax.bar(x, operating_costs, width, bottom=capital_costs, label='Operating cost', color=opex_color)
# Plot revenue as negative bars below the x-axis
bars3 = ax.bar(x, -revenue, width, label='Solids revenue', color=revenue_color)

# Add dots for levelized cost (commented out per request)
ax.scatter(x, levelized_costs, color=dot_color, s=100, label='Levelized cost', zorder=5)
ax.set_frame_on(False)

# Customize the plot
ax.set_xlabel('Estimate source', fontsize=11)
ax.set_ylabel('Cost (USD_2020/Mt Li)', fontsize=11)
ax.set_title('Levelized cost of lithium: Model comparison', fontsize=11, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=11)
# Dynamic y-limits to include negative revenue and positive costs
total_costs = capital_costs + operating_costs
y_min = -np.max(revenue) * 1.2
y_max = max(np.max(total_costs), np.max(levelized_costs)) * 1.6
ax.set_ylim(y_min, y_max)
ax.axhline(0, color='black', linewidth=1)

# Add legend
ax.legend(loc='upper right', frameon=True, fancybox=True, shadow=True)

# Grid for better readability
ax.grid(axis='y', alpha=0.3, linestyle='--')

# Adjust layout
plt.tight_layout()

# Show the plot
plt.show()