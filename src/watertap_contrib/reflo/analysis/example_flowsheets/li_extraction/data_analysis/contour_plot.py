import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

def create_heat_map(csv_file_path, flow_volume):
    """
    Create a heat map from wide sensitivity analysis data.
    
    Parameters:
    -----------
    csv_file_path : str
        Path to the CSV file containing the data
    flow_volume : float
        Flow volume for converting concentrations to mass fractions
    """
    
    # Read the CSV file, skip the comment line and manually set column names
    df = pd.read_csv(csv_file_path, skiprows=1)
    
    # Set the correct column names manually
    expected_columns = [
        'Inlet Li+ concentration', 'Inlet TDS concentration', 'Final Li+ concentration', 
        'Final TDS concentration', 'LCOLi (USD/mt)', 'aggregate_capital_cost (USD)',
        'aggregate_fixed_operating_cost (USD/year)', 'aggregate_variable_operating_cost (USD/year)',
        'total_capital_cost (USD)', 'total_operating_cost (USD/year)', 'fraction_evaporated',
        'Resultant inlet Li+ concentration', 'Resultant inlet TDS concentration',
        'Resultant final Li+ concentration', 'Resultant final TDS concentration',
        'Li outflow (kg/s)', 'Concentrated brine outflow (kg/s)'
    ]
    
    df.columns = expected_columns
    print("Set column names:", df.columns.tolist())
    
    # Filter for only rows with final Li+ concentration = 2.0e-02 and final TDS concentration = 2.0e-01
    # df_filtered = df[
    #     (df['Final Li+ concentration'] == 2.0e-02) & 
    #     (df['Final TDS concentration'] == 2.0e-01)
    # ].copy()
    df_filtered = df.copy()
    # Remove rows with NaN values in LCOLi
    # df_filtered = df_filtered.dropna(subset=['LCOLi (USD/mt)'])
    
    # Calculate mass fraction percentages
    df_filtered['inlet_li_mass_fraction_pct'] = (df_filtered['Inlet Li+ concentration'] / (flow_volume * 10)).round(4)
    df_filtered['inlet_tds_mass_fraction_pct'] = (df_filtered['Inlet TDS concentration'] / (flow_volume * 10)).round(4)
    
    # Convert levelized cost to thousands per metric ton
    df_filtered['levelized_cost_thousands'] = df_filtered['LCOLi (USD/mt)'] / 1000
    
    # Create pivot table for heat map
    pivot_data = df_filtered.pivot_table(
        values='levelized_cost_thousands',
        index='inlet_li_mass_fraction_pct',
        columns='inlet_tds_mass_fraction_pct',
        aggfunc='mean'
    )
    
    # Sort the index and columns for better visualization
    pivot_data = pivot_data.sort_index()
    pivot_data = pivot_data.reindex(sorted(pivot_data.columns), axis=1)
    
    # Calculate baseline values for percentage calculations
    baseline_li = pivot_data.index[len(pivot_data.index)-1]  # Use highest value as baseline
    baseline_tds = pivot_data.columns[len(pivot_data.columns)-1]  # Use highest value as baseline
    baseline_cost = pivot_data.loc[baseline_li, baseline_tds]
    
    # Create percentage variation labels for x-axis (TDS concentrations)
    x_labels = []
    for col in pivot_data.columns:
        if col == baseline_tds:
            x_labels.append(f"{col:.2f}\n(0%)")
        else:
            pct_change = ((col - baseline_tds) / baseline_tds) * 100
            sign = "+" if pct_change > 0 else ""
            x_labels.append(f"{col:.2f}\n({sign}{pct_change:.0f}%)")
    
    # Create percentage variation labels for y-axis (Li+ concentrations)
    y_labels = []
    for idx in pivot_data.index:
        if idx == baseline_li:
            y_labels.append(f"{idx:.4f}\n(0%)")
        else:
            pct_change = ((idx - baseline_li) / baseline_li) * 100
            sign = "+" if pct_change > 0 else ""
            y_labels.append(f"{idx:.4f}\n({sign}{pct_change:.0f}%)")
    
    # Create custom annotation text with percentage variations
    annot_data = pivot_data.copy()
    for i, idx in enumerate(pivot_data.index):
        for j, col in enumerate(pivot_data.columns):
            cost_val = pivot_data.loc[idx, col]
            if pd.notna(cost_val):
                pct_change = ((cost_val - baseline_cost) / baseline_cost) * 100
                sign = "+" if pct_change > 0 else ""
                annot_data.loc[idx, col] = f"{cost_val:.1f}\n({sign}{pct_change:.0f}%)"
    
    # Create the contour plot
    plt.figure(figsize=(10, 8))
    
    # Prepare data for contour plot
    X, Y = np.meshgrid(pivot_data.columns, pivot_data.index)
    Z = pivot_data.values
    
    # Create contourf plot with the same colorscheme
    contour = plt.contourf(X, Y, Z, levels=12, cmap='viridis', extend='both')
    
    # Add contour lines
    contour_lines = plt.contour(X, Y, Z, levels=12, colors='black', alpha=0.3, linewidths=0.5)
    
    # Add colorbar with the same styling
    cbar = plt.colorbar(contour, label='Levelized cost (thousands $/t Li⁺)')
    cbar.ax.set_ylabel('Levelized cost (thousands $/t Li⁺)', fontsize=14)
    cbar.ax.tick_params(labelsize=12)
    
    # Add percentage variation labels to colorbar ticks
    cbar_ticks = cbar.get_ticks()
    cbar_labels = []
    for tick in cbar_ticks:
        if abs(tick - baseline_cost) < 0.01:  # Use small tolerance for float comparison
            cbar_labels.append(f"{tick:.1f}\n(0%)")
        else:
            pct_change = ((tick - baseline_cost) / baseline_cost) * 100
            sign = "+" if pct_change > 0 else ""
            cbar_labels.append(f"{tick:.1f}\n({sign}{pct_change:.0f}%)")
    
    cbar.set_ticks(cbar_ticks)
    cbar.set_ticklabels(cbar_labels)
    
    # Set custom x and y tick labels with percentage variations
    plt.xticks(pivot_data.columns, x_labels, rotation=45, ha='right', fontsize=12)
    plt.yticks(pivot_data.index, y_labels, fontsize=12)
    
    # Set labels and title
    plt.xlabel('Inlet TDS concentration (mass fraction %)', fontsize=14)
    plt.ylabel('Inlet Li$^+$ concentration (mass fraction %)', fontsize=14)
    plt.title('Li$^+$ brine levelized cost estimate and % change', fontsize=16, fontweight='bold')
    
    # Add grid for better readability
    plt.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    
    # Add Salar de Atacama label
    plt.text(31.0, 0.18, 'Salar de Atacama', 
             fontsize=16, fontweight='bold', color='white',
             ha='center', va='center')

    # Add Salar de Hombre Muerto label
    plt.text(28.0, 0.08, 'Salar de Hombre Muerto', 
             fontsize=16, fontweight='bold', color='white',
             ha='center', va='center')

    # Add Salar de Uyuni label
    plt.text(25.0, 0.065, 'Salar de Uyuni', 
             fontsize=16, fontweight='bold', color='white',
             ha='center', va='center')

    # Add Oil and Gas label
    plt.text(22.5, 0.05, 'Oil and Gas', 
             fontsize=16, fontweight='bold', color='black',
             ha='center', va='center')

    # Add Geothermal label
    plt.text(28.0, 0.046, 'Geothermal', 
             fontsize=16, fontweight='bold', color='black',
             ha='center', va='center')
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('wide_sensitivity_contour.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return pivot_data

if __name__ == "__main__":
    # Parameters - UPDATE THESE VALUES
    FLOW_VOLUME = 1.280  # Flow volume for mass fraction conversion
    CSV_FILE = "watertap-reflo/src/widerr_sensitivity.csv"
    
    # Create the heat map
    result_data = create_heat_map(CSV_FILE, FLOW_VOLUME)
    print("Heat map created successfully!")
    print(f"Data shape: {result_data.shape}")
    print(f"Number of valid data points: {len(result_data.dropna().values.flatten())}")
