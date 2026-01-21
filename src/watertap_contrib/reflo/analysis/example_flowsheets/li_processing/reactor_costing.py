"""Reactor costing parameter estimation from log-log data.

This script processes reactor costing data from the data directory to determine
robust capital costing parameters for reactor cost equations of the form:
    C_cap = a + b * V^n

where:
    - C_cap is the capital cost (USD)
    - a is a fixed cost parameter (USD)
    - b is a variable cost coefficient (USD/m³^n)
    - V is the reactor volume (m³)
    - n is the scaling exponent (dimensionless)

Data files contain two points from log-log plots where:
    - x-axis: reactor capacity (gallons, logarithmic)
    - y-axis: purchased cost (dollars, logarithmic)
"""

import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("Warning: PyYAML not available. YAML file updates will be skipped.")

try:
    from pyomo.environ import units as pyunits
    PYOMO_AVAILABLE = True
except ImportError:
    PYOMO_AVAILABLE = False
    print("Warning: Pyomo not available. Some unit conversion features may be limited.")

def parse_filename(filename):
    """Extract material type and surface density from filename.
    
    Args:
        filename: Filename like 'Stainless_300.csv'
        
    Returns:
        tuple: (material_type, surface_density_lb_in2)
    """
    stem = Path(filename).stem
    parts = stem.split('_')
    material = parts[0]
    density = float(parts[1])
    return material, density

def read_reactor_data(csv_path):
    """Read reactor costing data from CSV file.
    
    Args:
        csv_path: Path to CSV file with capacity (gal) and cost (USD) data
        
    Returns:
        DataFrame with columns: capacity_gal, cost_usd
    """
    data = pd.read_csv(csv_path, header=None, names=['capacity_gal', 'cost_usd'])
    return data

def fit_power_law(volumes_gal, costs_usd):
    """Fit power law model to reactor costing data from log-log plot.
    
    For two points from a log-log plot:
        Cost = b * V^n
        log(Cost) = log(b) + n * log(V)
    
    Args:
        volumes_gal: Reactor capacities in gallons
        costs_usd: Purchased costs in USD
        
    Returns:
        tuple: (b, n, r_squared)
            b: cost coefficient
            n: scaling exponent
            r_squared: goodness of fit
    """
    log_V = np.log(volumes_gal)
    log_Cost = np.log(costs_usd)
    
    n = (log_Cost[1] - log_Cost[0]) / (log_V[1] - log_V[0])
    log_b = log_Cost[0] - n * log_V[0]
    b = np.exp(log_b)
    
    Cost_pred = b * volumes_gal ** n
    ss_res = np.sum((costs_usd - Cost_pred) ** 2)
    ss_tot = np.sum((costs_usd - np.mean(costs_usd)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 1.0
    
    return b, n, r_squared

def convert_units_to_m3(b_gal, n):
    """Convert cost coefficient from gallons to cubic meters.
    
    Args:
        b_gal: Cost coefficient in USD/gal^n
        n: Scaling exponent
        
    Returns:
        b_m3: Cost coefficient in USD/m³^n
    """
    gal_to_m3 = 0.00378541
    b_m3 = b_gal * (1.0 / gal_to_m3) ** n
    return b_m3

def process_all_data(data_dir):
    """Process all reactor costing data files.
    
    Args:
        data_dir: Path to directory containing CSV data files
        
    Returns:
        DataFrame with analysis results for all materials
    """
    data_dir = Path(data_dir)
    results = []
    
    for csv_file in sorted(data_dir.glob('*.csv')):
        material, density = parse_filename(csv_file.name)
        data = read_reactor_data(csv_file)
        
        volumes_gal = data['capacity_gal'].values
        costs_usd = data['cost_usd'].values
        
        b_gal, n, r2 = fit_power_law(volumes_gal, costs_usd)
        b_m3 = convert_units_to_m3(b_gal, n)
        
        results.append({
            'material': material,
            'surface_density_lb_in2': density,
            'b_gal': b_gal,
            'b_m3': b_m3,
            'n': n,
            'r_squared': r2,
            'v_min_gal': volumes_gal.min(),
            'v_max_gal': volumes_gal.max(),
            'cost_min_usd': costs_usd.min(),
            'cost_max_usd': costs_usd.max(),
            'csv_file': csv_file.name
        })
    
    return pd.DataFrame(results)

def calculate_recommended_parameters(results_df, material='Stainless', method='median', surface_density=None):
    """Calculate recommended costing parameters from analysis results.
    
    Args:
        results_df: DataFrame from process_all_data
        material: Material type to use (default: 'Stainless')
        method: Aggregation method ('median', 'mean', 'conservative', 'specific')
        surface_density: If method='specific', the specific surface density to use (lb/in²)
        
    Returns:
        dict with recommended parameters
    """
    material_data = results_df[results_df['material'] == material]
    
    if len(material_data) == 0:
        print(f"Warning: No data for material '{material}', using all materials")
        material_data = results_df
    
    if method == 'specific' and surface_density is not None:
        specific_data = material_data[material_data['surface_density_lb_in2'] == surface_density]
        if len(specific_data) == 0:
            print(f"Warning: No data for {material} at {surface_density} lb/in², using median instead")
            method = 'median'
        elif len(specific_data) > 1:
            print(f"Warning: Multiple datasets for {material} at {surface_density} lb/in², using first")
            n_rec = specific_data['n'].iloc[0]
            b_rec = specific_data['b_m3'].iloc[0]
        else:
            n_rec = specific_data['n'].iloc[0]
            b_rec = specific_data['b_m3'].iloc[0]
    
    if method == 'median' or (method == 'specific' and surface_density is None):
        n_rec = material_data['n'].median()
        b_rec = material_data['b_m3'].median()
    elif method == 'mean':
        n_rec = material_data['n'].mean()
        b_rec = material_data['b_m3'].mean()
    elif method == 'conservative':
        n_rec = material_data['n'].max()
        b_rec = material_data['b_m3'].max()
    elif method != 'specific':
        raise ValueError(f"Unknown method: {method}")
    
    a_rec = 0.0
    
    param_dict = {
        'capital_a_parameter': float(a_rec),
        'capital_b_parameter': float(b_rec),
        'capital_n_exponent': float(n_rec),
        'material': material,
        'method': method,
        'n_datasets': len(material_data)
    }
    
    if surface_density is not None:
        param_dict['surface_density'] = surface_density
    
    return param_dict

def plot_all_fits(results_df, data_dir, output_path=None):
    """Create visualization of all reactor costing fits.
    
    Args:
        results_df: DataFrame from process_all_data
        data_dir: Path to directory containing CSV data files
        output_path: Optional path to save plot
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    data_dir = Path(data_dir)
    colors = {'Stainless': 'blue', 'Carbon': 'red', 'Glass-lined': 'green'}
    markers = {50: 'o', 100: 's', 300: '^', 1500: 'D'}
    
    for idx, row in results_df.iterrows():
        csv_file = data_dir / row['csv_file']
        data = read_reactor_data(csv_file)
        volumes_gal = data['capacity_gal'].values
        costs_usd = data['cost_usd'].values
        
        color = colors.get(row['material'], 'gray')
        marker = markers.get(row['surface_density_lb_in2'], 'x')
        label = f"{row['material']} {row['surface_density_lb_in2']} lb/in²"
        
        v_plot = np.logspace(np.log10(volumes_gal.min() * 0.8), 
                             np.log10(volumes_gal.max() * 1.2), 100)
        cost_plot = row['b_gal'] * v_plot ** row['n']
        
        ax1.loglog(volumes_gal, costs_usd, marker=marker, color=color, 
                   markersize=8, linestyle='', label=f'{label} (data)')
        ax1.loglog(v_plot, cost_plot, color=color, linestyle='--', alpha=0.6, linewidth=1)
    
    ax1.set_xlabel('Reactor Capacity (gallons)', fontsize=12)
    ax1.set_ylabel('Purchased Cost (USD)', fontsize=12)
    ax1.set_title('Reactor Capital Cost vs. Capacity (Log-Log)', fontsize=14, fontweight='bold')
    ax1.grid(True, which='both', alpha=0.3)
    ax1.legend(fontsize=8, loc='lower right')
    
    materials = results_df['material'].unique()
    x_pos = np.arange(len(materials))
    width = 0.35
    
    for i, material in enumerate(materials):
        mat_data = results_df[results_df['material'] == material]
        n_values = mat_data['n'].values
        densities = mat_data['surface_density_lb_in2'].values
        
        color = colors.get(material, 'gray')
        ax2.bar(x_pos[i], mat_data['n'].mean(), width, 
                color=color, alpha=0.7, label=f'{material} (mean)')
        ax2.errorbar(x_pos[i], mat_data['n'].mean(), 
                     yerr=mat_data['n'].std(), 
                     color=color, capsize=5, linewidth=2)
    
    ax2.set_xlabel('Material Type', fontsize=12)
    ax2.set_ylabel('Scaling Exponent (n)', fontsize=12)
    ax2.set_title('Scaling Exponent by Material', fontsize=14, fontweight='bold')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(materials)
    ax2.grid(True, axis='y', alpha=0.3)
    ax2.axhline(y=0.6, color='black', linestyle=':', linewidth=2, label='Rule of thumb (0.6)')
    ax2.legend(fontsize=9)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to: {output_path}")
    else:
        plt.show()

def print_summary(results_df):
    """Print summary statistics of reactor costing analysis."""
    print("\n" + "="*80)
    print("REACTOR COSTING ANALYSIS SUMMARY")
    print("="*80)
    
    print(f"\nTotal datasets processed: {len(results_df)}")
    print(f"Materials: {', '.join(results_df['material'].unique())}")
    print(f"Surface densities: {sorted(results_df['surface_density_lb_in2'].unique())} lb/in²")
    
    print("\n" + "-"*80)
    print("DETAILED RESULTS BY DATASET")
    print("-"*80)
    
    for idx, row in results_df.iterrows():
        print(f"\n{row['csv_file']}:")
        print(f"  Material: {row['material']}")
        print(f"  Surface Density: {row['surface_density_lb_in2']} lb/in²")
        print(f"  Cost = {row['b_gal']:.2e} * V^{row['n']:.4f}  (V in gallons)")
        print(f"  Cost = {row['b_m3']:.2e} * V^{row['n']:.4f}  (V in m³)")
        print(f"  R² = {row['r_squared']:.6f}")
        print(f"  Capacity range: {row['v_min_gal']:.1f} - {row['v_max_gal']:.1f} gallons")
        print(f"  Cost range: ${row['cost_min_usd']:,.0f} - ${row['cost_max_usd']:,.0f}")
    
    print("\n" + "-"*80)
    print("STATISTICS BY MATERIAL")
    print("-"*80)
    
    for material in results_df['material'].unique():
        mat_data = results_df[results_df['material'] == material]
        print(f"\n{material}:")
        print(f"  Datasets: {len(mat_data)}")
        print(f"  Scaling exponent (n):")
        print(f"    Mean ± Std: {mat_data['n'].mean():.4f} ± {mat_data['n'].std():.4f}")
        print(f"    Median: {mat_data['n'].median():.4f}")
        print(f"    Range: [{mat_data['n'].min():.4f}, {mat_data['n'].max():.4f}]")
        print(f"  Cost coefficient (b) in USD/m³^n:")
        print(f"    Mean: {mat_data['b_m3'].mean():.2e}")
        print(f"    Median: {mat_data['b_m3'].median():.2e}")
        print(f"    Range: [{mat_data['b_m3'].min():.2e}, {mat_data['b_m3'].max():.2e}]")

def update_yaml_parameters(yaml_path, recommended_params):
    """Update costing_parameters.yaml with recommended reactor cost parameters.
    
    Args:
        yaml_path: Path to costing_parameters.yaml
        recommended_params: Dict from calculate_recommended_parameters
    """
    if not YAML_AVAILABLE:
        print("\nWarning: PyYAML not available. Cannot update YAML file.")
        print("Recommended parameters to manually add to costing_parameters.yaml:")
        print("\nreactor_cost:")
        print(f"  capital_a_parameter: {recommended_params['capital_a_parameter']:.6e}")
        print(f"  capital_b_parameter: {recommended_params['capital_b_parameter']:.6e}")
        print(f"  capital_n_exponent: {recommended_params['capital_n_exponent']:.6f}")
        material_info = f"Material: {recommended_params['material']}"
        if 'surface_density' in recommended_params:
            material_info += f" ({recommended_params['surface_density']} lb/in²)"
        print(f"  # {material_info}, Method: {recommended_params['method']}")
        print(f"  # Based on {recommended_params['n_datasets']} datasets")
        return
    
    yaml_path = Path(yaml_path)
    
    if yaml_path.exists():
        with open(yaml_path, 'r') as f:
            params = yaml.safe_load(f)
    else:
        params = {}
    
    if 'reactor_cost' not in params:
        params['reactor_cost'] = {}
    
    params['reactor_cost']['capital_a_parameter'] = recommended_params['capital_a_parameter']
    params['reactor_cost']['capital_b_parameter'] = recommended_params['capital_b_parameter']
    params['reactor_cost']['capital_n_exponent'] = recommended_params['capital_n_exponent']
    
    metadata = {
        'material': recommended_params['material'],
        'method': recommended_params['method'],
        'n_datasets': recommended_params['n_datasets'],
        'description': 'Capital cost correlation: C_cap = a + b*V^n where V is in m³',
        'generated_by': 'reactor_costing.py'
    }
    
    if 'surface_density' in recommended_params:
        metadata['surface_density_lb_in2'] = recommended_params['surface_density']
    
    params['reactor_cost']['_metadata'] = metadata
    
    with open(yaml_path, 'w') as f:
        yaml.dump(params, f, default_flow_style=False, sort_keys=False)
    
    print(f"\nYAML parameters updated: {yaml_path}")

def main():
    """Main function to run reactor costing analysis."""
    script_dir = Path(__file__).parent
    data_dir = script_dir / 'data'
    yaml_path = script_dir / 'costing_parameters.yaml'
    plot_path = script_dir / 'reactor_costing_analysis.png'
    
    print("="*80)
    print("REACTOR CAPITAL COSTING PARAMETER ESTIMATION")
    print("="*80)
    print(f"\nData directory: {data_dir}")
    print(f"Output plot: {plot_path}")
    print(f"YAML config: {yaml_path}")
    
    results_df = process_all_data(data_dir)
    
    print_summary(results_df)
    
    print("\n" + "="*80)
    print("RECOMMENDED PARAMETERS")
    print("="*80)
    
    for material in results_df['material'].unique():
        for method in ['median', 'mean', 'conservative']:
            rec_params = calculate_recommended_parameters(results_df, material, method)
            print(f"\n{material} ({method}):")
            print(f"  a = {rec_params['capital_a_parameter']:.2e} USD")
            print(f"  b = {rec_params['capital_b_parameter']:.2e} USD/m³^{rec_params['capital_n_exponent']:.4f}")
            print(f"  n = {rec_params['capital_n_exponent']:.4f}")
            print(f"  Based on {rec_params['n_datasets']} datasets")
    
    default_material = 'Stainless'
    default_method = 'specific'
    default_surface_density = 300.0
    rec_params = calculate_recommended_parameters(results_df, default_material, default_method, default_surface_density)
    
    print(f"\n" + "="*80)
    print(f"SELECTED FOR YAML UPDATE: {default_material} {default_surface_density} lb/in² ({default_method})")
    print("="*80)
    print(f"  capital_a_parameter: {rec_params['capital_a_parameter']:.2e} USD")
    print(f"  capital_b_parameter: {rec_params['capital_b_parameter']:.2e} USD/m³^n")
    print(f"  capital_n_exponent: {rec_params['capital_n_exponent']:.4f}")
    
    update_yaml_parameters(yaml_path, rec_params)
    
    plot_all_fits(results_df, data_dir, plot_path)
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("  1. Review the generated plot: reactor_costing_analysis.png")
    print("  2. Verify the updated parameters in: costing_parameters.yaml")
    print("  3. Run your flowsheet with the new reactor costing parameters")

if __name__ == '__main__':
    main()
