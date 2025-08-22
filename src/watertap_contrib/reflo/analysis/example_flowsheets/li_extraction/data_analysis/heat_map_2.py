import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap

def create_heat_map(csv_file_path, flow_volume, evaporation_rate):
    """
    Create a heat map from sensitivity analysis data.
    
    Parameters:
    -----------
    csv_file_path : str
        Path to the CSV file containing the data
    evaporation_rate : float
        Base evaporation rate to multiply by adjustment factor
    """
    
    # Read the CSV file
    df = pd.read_csv(csv_file_path)
    
    # Select only the first 3 columns and rename them
    df = df.iloc[:, :3]
    df.columns = ['inlet_lithium_concentration', 'evap_adjustment_factor', 'levelized_cost']
    
    # Calculate true inlet lithium concentration
    df['true_inlet_lithium_concentration'] = (df['inlet_lithium_concentration'] / flow_volume / 10).round(2)
    
    # Calculate true evaporation rate
    df['true_evaporation_rate'] = df['evap_adjustment_factor'] * evaporation_rate / 0.75
    
    # Convert levelized cost to thousands per metric ton
    df['levelized_cost_thousands'] = df['levelized_cost'] / 1000
    
    # Create pivot table for heat map
    pivot_data = df.pivot_table(
        values='levelized_cost_thousands',
        index='true_inlet_lithium_concentration',
        columns='true_evaporation_rate',
        aggfunc='mean'
    )
    
    # Round column labels (evaporation rates) to nearest integer
    pivot_data.columns = [round(col) for col in pivot_data.columns]
    
    # Calculate median values for base case
    baseline_inlet_li = 0.2  # Fixed baseline value
    baseline_evap_rate = 1753.0  # Fixed baseline value
    baseline_cost = 6.458613  # Fixed baseline cost value from the data
    
    # Create percentage variation labels for x-axis (evaporation rates)
    x_labels = []
    for col in pivot_data.columns:
        if col == baseline_evap_rate:
            x_labels.append(f"{col}\n(0%)")
        else:
            pct_change = ((col - baseline_evap_rate) / baseline_evap_rate) * 100
            sign = "+" if pct_change > 0 else ""
            x_labels.append(f"{col}\n({sign}{pct_change:.0f}%)")
    
    # Create percentage variation labels for y-axis (inlet lithium concentrations)
    y_labels = []
    for idx in pivot_data.index:
        if idx == baseline_inlet_li:
            y_labels.append(f"{idx}\n(0%)")
        else:
            pct_change = ((idx - baseline_inlet_li) / baseline_inlet_li) * 100
            sign = "+" if pct_change > 0 else ""
            y_labels.append(f"{idx}\n({sign}{pct_change:.0f}%)")
    
    # Create custom annotation text with percentage variations
    annot_data = pivot_data.copy()
    for i, idx in enumerate(pivot_data.index):
        for j, col in enumerate(pivot_data.columns):
            cost_val = pivot_data.loc[idx, col]
            if pd.notna(cost_val):
                pct_change = ((cost_val - baseline_cost) / baseline_cost) * 100
                sign = "+" if pct_change > 0 else ""
                annot_data.loc[idx, col] = f"{cost_val:.1f}\n({sign}{pct_change:.0f}%)"
    
    # Create the heat map
    plt.figure(figsize=(6, 6))
    
    # Create heat map with custom annotations showing percentage variations
    ax = sns.heatmap(
        pivot_data,
        annot=annot_data,
        fmt='',
        cmap='viridis',
        cbar_kws={'label': 'Levelized cost (thousands $/t Li$^+$)'},
        linewidths=0.5,
        annot_kws={'fontsize': 14, 'fontweight': 'bold'}
    )
    ax.invert_yaxis()
    
    # Set custom x and y tick labels with percentage variations
    ax.set_xticklabels(x_labels, rotation=45, ha='right', fontsize=14)
    ax.set_yticklabels(y_labels, fontsize=14)
    
    # Set colorbar label font size
    cbar = ax.collections[0].colorbar
    cbar.ax.set_ylabel('Levelized cost (thousands $/t Li⁺)', fontsize=16)
    cbar.ax.tick_params(labelsize=14)
    
    # Add percentage variation labels to colorbar ticks
    cbar_ticks = cbar.get_ticks()
    cbar_labels = []
    for tick in cbar_ticks:
        if tick == baseline_cost:
            cbar_labels.append(f"{tick:.1f}\n(0%)")
        else:
            pct_change = ((tick - baseline_cost) / baseline_cost) * 100
            sign = "+" if pct_change > 0 else ""
            cbar_labels.append(f"{tick:.1f}\n({sign}{pct_change:.0f}%)")
    
    cbar.set_ticks(cbar_ticks)
    cbar.set_ticklabels(cbar_labels)
    
    # Set labels and title
    plt.xlabel('Evaporation rate (mm/year)', fontsize=16)
    plt.ylabel('Inlet Li$^+$ concentration (%)', fontsize=16)
    plt.title('Li$^+$ brine levelized cost estimate and % change', fontsize=18, fontweight='bold')
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('lithium_cost_heat_map.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return pivot_data

if __name__ == "__main__":
    # Parameters - UPDATE THESE VALUES
    FLOW_VOLUME = 1.280
    EVAPORATION_RATE = 1315.0 / 0.75
    CSV_FILE = "watertap-reflo/src/inlet_evap_sensitivity_high.csv"
    
    # Create the heat map
    result_data = create_heat_map(CSV_FILE, FLOW_VOLUME, EVAPORATION_RATE)
    print("Heat map created successfully!")
    print(f"Data shape: {result_data.shape}")
