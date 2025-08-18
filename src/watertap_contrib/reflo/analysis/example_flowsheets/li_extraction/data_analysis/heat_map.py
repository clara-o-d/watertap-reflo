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
    
    # Create the heat map
    plt.figure(figsize=(6, 8))
    
    # Create custom colormap from purple to blue to teal
    colors = ['#7a1a6b', '#4198b5', '#279989']
    custom_cmap = LinearSegmentedColormap.from_list('purple_blue_teal', colors, N=256)
    
    # Create heat map with annotations
    ax = sns.heatmap(
        pivot_data,
        annot=True,
        fmt='.1f',
        cmap=custom_cmap,
        cbar_kws={'label': 'Levelized Cost (thousands $/mt Li)'},
        linewidths=0.5,
        annot_kws={'fontsize': 14}
    )
    
    # Set colorbar label font size
    cbar = ax.collections[0].colorbar
    cbar.ax.set_ylabel('Levelized Cost (thousands $/mt Li)', fontsize=14)
    cbar.ax.tick_params(labelsize=12)
    
    # Set labels and title
    plt.xlabel('Evaporation Rate (mm/year)', fontsize=14)
    plt.ylabel('Inlet Lithium Concentration (%)', fontsize=14)
    plt.title('Levelized Cost of Li+', fontsize=16, fontweight='bold')
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45, fontsize=12)
    plt.yticks(rotation=0, fontsize=12)
    
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
    CSV_FILE = "watertap-reflo/src/inlet_evap_sensitivity.csv"
    
    # Create the heat map
    result_data = create_heat_map(CSV_FILE, FLOW_VOLUME, EVAPORATION_RATE)
    print("Heat map created successfully!")
    print(f"Data shape: {result_data.shape}")
