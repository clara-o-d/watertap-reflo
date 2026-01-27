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

def psi_to_atm(psi):
    """Convert pressure from psi (lb/in²) to atmospheres.
    
    Args:
        psi: Pressure in lb/in² (psi)
        
    Returns:
        atm: Pressure in atmospheres
    """
    return psi * 0.068046

def parse_filename(filename):
    """Extract material type and pressure capacity from filename.
    
    Args:
        filename: Filename like 'Stainless_300.csv'
        
    Returns:
        tuple: (material_type, pressure_capacity_psi)
    """
    stem = Path(filename).stem
    parts = stem.split('_')
    material = parts[0]
    pressure_psi = float(parts[1])
    return material, pressure_psi

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
    """Fit power law model to reactor costing data using log-log linear regression.
    
    Power law model: Cost = b * V^n
    In log-log space: log(Cost) = log(b) + n * log(V)
    
    Uses linear regression in log-log space to fit all available data points.
    
    Args:
        volumes_gal: Reactor capacities in gallons (array)
        costs_usd: Purchased costs in USD (array)
        
    Returns:
        tuple: (b, n, r_squared, std_err_n, std_err_log_b, n_points)
            b: cost coefficient (USD/gal^n)
            n: scaling exponent (dimensionless)
            r_squared: coefficient of determination in log-log space
            std_err_n: standard error of the exponent n
            std_err_log_b: standard error of log(b)
            n_points: number of data points used in fit
    """
    log_V = np.log(volumes_gal)
    log_Cost = np.log(costs_usd)
    n_points = len(volumes_gal)
    
    if n_points < 2:
        raise ValueError("Need at least 2 data points to fit power law")
    
    # Linear regression in log-log space: log(Cost) = log(b) + n * log(V)
    # Using numpy polyfit (degree 1 polynomial)
    coeffs = np.polyfit(log_V, log_Cost, deg=1)
    n = coeffs[0]  # slope
    log_b = coeffs[1]  # intercept
    b = np.exp(log_b)
    
    # Calculate R² in log-log space
    log_Cost_pred = log_b + n * log_V
    ss_res = np.sum((log_Cost - log_Cost_pred) ** 2)
    ss_tot = np.sum((log_Cost - np.mean(log_Cost)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 1.0
    
    # Calculate standard errors
    if n_points > 2:
        # Residual standard error
        s = np.sqrt(ss_res / (n_points - 2))
        
        # Standard error of slope (n)
        x_mean = np.mean(log_V)
        sxx = np.sum((log_V - x_mean) ** 2)
        std_err_n = s / np.sqrt(sxx)
        
        # Standard error of intercept (log_b)
        std_err_log_b = s * np.sqrt(1/n_points + x_mean**2 / sxx)
    else:
        # Perfect fit with 2 points
        std_err_n = 0.0
        std_err_log_b = 0.0
    
    return b, n, r_squared, std_err_n, std_err_log_b, n_points

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
        material, pressure_psi = parse_filename(csv_file.name)
        data = read_reactor_data(csv_file)
        
        volumes_gal = data['capacity_gal'].values
        costs_usd = data['cost_usd'].values
        
        b_gal, n, r2, std_err_n, std_err_log_b, n_points = fit_power_law(volumes_gal, costs_usd)
        b_m3 = convert_units_to_m3(b_gal, n)
        
        # Calculate 95% confidence interval for n
        ci_95_n = 1.96 * std_err_n if n_points > 2 else 0.0
        
        # Convert pressure capacity to atmospheres
        pressure_atm = psi_to_atm(pressure_psi)
        
        results.append({
            'material': material,
            'pressure_capacity_psi': pressure_psi,
            'pressure_capacity_atm': pressure_atm,
            'b_gal': b_gal,
            'b_m3': b_m3,
            'n': n,
            'r_squared': r2,
            'std_err_n': std_err_n,
            'ci_95_n': ci_95_n,
            'n_points': n_points,
            'v_min_gal': volumes_gal.min(),
            'v_max_gal': volumes_gal.max(),
            'cost_min_usd': costs_usd.min(),
            'cost_max_usd': costs_usd.max(),
            'csv_file': csv_file.name
        })
    
    return pd.DataFrame(results)

def calculate_recommended_parameters(results_df, material='Stainless', method='median', pressure_capacity_psi=None):
    """Calculate recommended costing parameters from analysis results.
    
    Args:
        results_df: DataFrame from process_all_data
        material: Material type to use (default: 'Stainless')
        method: Aggregation method ('median', 'mean', 'conservative', 'specific')
        pressure_capacity_psi: If method='specific', the specific pressure capacity to use (psi)
        
    Returns:
        dict with recommended parameters
    """
    material_data = results_df[results_df['material'] == material]
    
    if len(material_data) == 0:
        print(f"Warning: No data for material '{material}', using all materials")
        material_data = results_df
    
    if method == 'specific' and pressure_capacity_psi is not None:
        specific_data = material_data[material_data['pressure_capacity_psi'] == pressure_capacity_psi]
        if len(specific_data) == 0:
            print(f"Warning: No data for {material} at {pressure_capacity_psi} psi ({psi_to_atm(pressure_capacity_psi):.1f} atm), using median instead")
            method = 'median'
        elif len(specific_data) > 1:
            print(f"Warning: Multiple datasets for {material} at {pressure_capacity_psi} psi ({psi_to_atm(pressure_capacity_psi):.1f} atm), using first")
            n_rec = specific_data['n'].iloc[0]
            b_rec = specific_data['b_m3'].iloc[0]
        else:
            n_rec = specific_data['n'].iloc[0]
            b_rec = specific_data['b_m3'].iloc[0]
    
    if method == 'median' or (method == 'specific' and pressure_capacity_psi is None):
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
    
    if pressure_capacity_psi is not None:
        param_dict['pressure_capacity_psi'] = pressure_capacity_psi
        param_dict['pressure_capacity_atm'] = psi_to_atm(pressure_capacity_psi)
    
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
        marker = markers.get(row['pressure_capacity_psi'], 'x')
        n_pts = int(row['n_points'])
        label = f"{row['material']} {row['pressure_capacity_psi']:.0f} psi ({row['pressure_capacity_atm']:.1f} atm, n={n_pts})"
        
        v_plot = np.logspace(np.log10(volumes_gal.min() * 0.8), 
                             np.log10(volumes_gal.max() * 1.2), 100)
        cost_plot = row['b_gal'] * v_plot ** row['n']
        
        ax1.loglog(volumes_gal, costs_usd, marker=marker, color=color, 
                   markersize=8, linestyle='', label=f'{label} (R²={row["r_squared"]:.3f})', 
                   alpha=0.7, markeredgewidth=1.5, markeredgecolor='black')
        ax1.loglog(v_plot, cost_plot, color=color, linestyle='--', alpha=0.5, linewidth=2)
    
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
        pressures_psi = mat_data['pressure_capacity_psi'].values
        
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
    pressure_capacities = sorted(results_df['pressure_capacity_psi'].unique())
    print(f"Pressure capacities: {pressure_capacities} psi ({[f'{psi_to_atm(p):.1f}' for p in pressure_capacities]} atm)")
    
    print("\n" + "-"*80)
    print("DETAILED RESULTS BY DATASET")
    print("-"*80)
    
    for idx, row in results_df.iterrows():
        print(f"\n{row['csv_file']}:")
        print(f"  Material: {row['material']}")
        print(f"  Pressure Capacity: {row['pressure_capacity_psi']:.0f} psi ({row['pressure_capacity_atm']:.1f} atm)")
        print(f"  Data points: {int(row['n_points'])}")
        print(f"  Cost = {row['b_gal']:.2e} * V^{row['n']:.4f}  (V in gallons)")
        print(f"  Cost = {row['b_m3']:.2e} * V^{row['n']:.4f}  (V in m³)")
        print(f"  Exponent n = {row['n']:.4f} ± {row['ci_95_n']:.4f} (95% CI)")
        print(f"  R² = {row['r_squared']:.6f}")
        print(f"  Capacity range: {row['v_min_gal']:.1f} - {row['v_max_gal']:.1f} gallons")
        print(f"  Cost range: ${row['cost_min_usd']:,.0f} - ${row['cost_max_usd']:,.0f}")
    
    print("\n" + "-"*80)
    print("STATISTICS BY MATERIAL")
    print("-"*80)
    
    for material in results_df['material'].unique():
        mat_data = results_df[results_df['material'] == material]
        total_points = mat_data['n_points'].sum()
        avg_r2 = mat_data['r_squared'].mean()
        print(f"\n{material}:")
        print(f"  Datasets: {len(mat_data)}")
        print(f"  Total data points: {int(total_points)} (avg: {total_points/len(mat_data):.1f} per dataset)")
        print(f"  Average R²: {avg_r2:.6f}")
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
        if 'pressure_capacity_psi' in recommended_params:
            material_info += f" ({recommended_params['pressure_capacity_psi']:.0f} psi / {recommended_params['pressure_capacity_atm']:.1f} atm)"
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
    
    if 'pressure_capacity_psi' in recommended_params:
        metadata['pressure_capacity_psi'] = recommended_params['pressure_capacity_psi']
        metadata['pressure_capacity_atm'] = recommended_params['pressure_capacity_atm']
    
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
    default_pressure_psi = 300.0
    rec_params = calculate_recommended_parameters(results_df, default_material, default_method, default_pressure_psi)
    
    print(f"\n" + "="*80)
    print(f"SELECTED FOR YAML UPDATE: {default_material} {default_pressure_psi:.0f} psi ({psi_to_atm(default_pressure_psi):.1f} atm) - {default_method}")
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
