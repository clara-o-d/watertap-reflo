import matplotlib.pyplot as plt
import numpy as np

# Sample data - you can replace these with your actual values
categories = ['WaterTAP model', 'Industry reports']

# Cost breakdown ($/kg Li or whatever units you're using)
capital_costs = [3217.42497515, 3230.20138367]  # Example values
operating_costs = [4743.20309904, 4388.86057562]  # Example values
levelized_costs = [7960.62807419, 7619.06195929]  # Total levelized cost (should equal capex + opex)

# Colors as specified
capex_color = '#4198b5'
opex_color = '#279989' 
dot_color = '#610059'

# Set up the plot
fig, ax = plt.subplots(figsize=(4.25, 6))

# Width of bars
width = 0.3
# Bring bars closer together by further reducing spacing between category centers
x = np.arange(len(categories)) * 0.5

# Create stacked bars
bars1 = ax.bar(x, capital_costs, width, label='Capital Cost', color=capex_color)
bars2 = ax.bar(x, operating_costs, width, bottom=capital_costs, label='Operating Cost', color=opex_color)

# Add dots for levelized cost (commented out per request)
# ax.scatter(x, levelized_costs, color=dot_color, s=100, label='Levelized Cost', zorder=5)

# Customize the plot
ax.set_xlabel('Estimate source', fontsize=10)
ax.set_ylabel('Cost ($/Mt Li)', fontsize=10)
ax.set_title('Levelized cost of lithium: Model comparison', fontsize=12, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=10)
ax.set_ylim(0, 10000)

# Add legend
ax.legend(loc='upper right', frameon=True, fancybox=True, shadow=True)

# Removed direct value labels on bars and dots per request

# Grid for better readability
ax.grid(axis='y', alpha=0.3, linestyle='--')

# Adjust layout
# plt.tight_layout()

# Show the plot
plt.show()