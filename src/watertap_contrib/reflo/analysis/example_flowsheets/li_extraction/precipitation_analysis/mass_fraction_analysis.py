# Computes fraction of mass remaining of each ion as a function of water evaporated
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import os
import glob

def load_ion_data(data_dir):
    ion_data = {}
    
    # Get all CSV files in the data directory
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    
    for file_path in csv_files:
        # Extract ion name from filename (remove .csv and clean up)
        ion_name = os.path.basename(file_path).replace('.csv', '').replace('_', '')
        
        # Load data
        data = pd.read_csv(file_path, header=None, names=['volume_m3', 'mass_fraction_percent'])
        
        # Convert mass fraction from percentage to decimal
        data['mass_fraction'] = data['mass_fraction_percent'] / 100.0
        
        ion_data[ion_name] = data
    
    return ion_data

def calculate_evaporation_ratio(volume_data, initial_volume=None):
    if initial_volume is None:
        initial_volume = np.max(volume_data)
    
    # Calculate evaporated volume
    evaporated_volume = initial_volume - volume_data
    
    # Calculate evaporation ratio
    evaporation_ratio = evaporated_volume / initial_volume
    
    return evaporation_ratio

def fit_linear_model(x, y):
    coeffs = np.polyfit(x, y, 1)
    return coeffs[0], coeffs[1]

def fit_polynomial_model(x, y, degree=2):
    coeffs = np.polyfit(x, y, degree)
    return coeffs

def fit_exponential_model(x, y):
    # Initial guess for parameters
    p0 = [1.0, -1.0, 0.0]
    
    def exponential_func(x, a, b, c):
        return a * np.exp(b * x) + c
    
    try:
        popt, _ = curve_fit(exponential_func, x, y, p0=p0, maxfev=10000)
        return popt
    except Exception:
        # If exponential fit fails, return None
        return None

def fit_sigmoid_model(x, y):
    """
    Fit a sigmoid model: y = 1.0 / (1 + exp(k * (x - x0)))
    This can capture the sharp transition behavior
    """
    # Initial guess: steep transition around middle
    p0 = [10.0, 0.8, 0.0, 1.0]  # k, x0, y_min, y_max
    
    def sigmoid_func(x, k, x0, y_min, y_max):
        return y_min + (y_max - y_min) / (1 + np.exp(k * (x - x0)))
    
    try:
        popt, _ = curve_fit(sigmoid_func, x, y, p0=p0, maxfev=10000)
        return popt
    except:
        return None

def calculate_r2_score(y_true, y_pred):
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1 - (ss_res / ss_tot)
    return r2

def evaluate_model_fit(x, y, model_func, params):
    y_pred = model_func(x, *params)
    return calculate_r2_score(y, y_pred)

def mean_absolute_error(y_true, y_pred):
    return np.mean(np.abs(y_true - y_pred))

def mean_squared_error(y_true, y_pred):
    return np.mean((y_true - y_pred) ** 2)

def max_absolute_error(y_true, y_pred):
    return np.max(np.abs(y_true - y_pred))

def find_dropoff_region(evaporation_ratio, mass_fraction, threshold=-0.01):
    # Compute the discrete derivative
    dmf = np.diff(mass_fraction) / np.diff(evaporation_ratio)
    # Find the first index where the derivative drops below the threshold
    drop_idx = np.argmax(dmf < threshold)
    if dmf[drop_idx] >= threshold:
        # If no drop found, use halfway point as fallback
        drop_idx = len(mass_fraction) // 2
    # Return mask for region after drop-off
    mask = np.zeros_like(mass_fraction, dtype=bool)
    mask[drop_idx+1:] = True
    return mask

def analyze_ion_behavior(ion_data):
    results = {}
    for ion_name, data in ion_data.items():
        print(f"\nAnalyzing {ion_name}...")
        initial_volume = np.max(data['volume_m3'])
        evaporation_ratio = calculate_evaporation_ratio(data['volume_m3'], initial_volume)
        mass_fraction = data['mass_fraction'].values
        # Fit only to the last 5 points
        x_fit = evaporation_ratio[-5:]
        y_fit = mass_fraction[-5:]
        # Linear fit
        a_linear, b_linear = fit_linear_model(x_fit, y_fit)
        y_pred_linear = a_linear * x_fit + b_linear
        linear_r2 = calculate_r2_score(y_fit, y_pred_linear)
        linear_mae = mean_absolute_error(y_fit, y_pred_linear)
        linear_mse = mean_squared_error(y_fit, y_pred_linear)
        linear_max_err = max_absolute_error(y_fit, y_pred_linear)
        # Quadratic fit
        quad_coeffs = fit_polynomial_model(x_fit, y_fit, degree=2)
        y_pred_quad = np.polyval(quad_coeffs, x_fit)
        quad_r2 = calculate_r2_score(y_fit, y_pred_quad)
        quad_mae = mean_absolute_error(y_fit, y_pred_quad)
        quad_mse = mean_squared_error(y_fit, y_pred_quad)
        quad_max_err = max_absolute_error(y_fit, y_pred_quad)
        # Exponential fit
        exp_params = fit_exponential_model(x_fit, y_fit)
        if exp_params is not None:
            y_pred_exp = exp_params[0] * np.exp(exp_params[1] * x_fit) + exp_params[2]
            exp_r2 = calculate_r2_score(y_fit, y_pred_exp)
            exp_mae = mean_absolute_error(y_fit, y_pred_exp)
            exp_mse = mean_squared_error(y_fit, y_pred_exp)
            exp_max_err = max_absolute_error(y_fit, y_pred_exp)
            exp_equation = f"mass_fraction = {exp_params[0]:.4f} * exp({exp_params[1]:.4f} * evaporation_ratio) + {exp_params[2]:.4f}"
        else:
            y_pred_exp = None
            exp_r2 = exp_mae = exp_mse = exp_max_err = float('nan')
            exp_equation = "Fit failed"
        models = {
            'linear': {
                'params': (a_linear, b_linear),
                'r2': linear_r2,
                'mae': linear_mae,
                'mse': linear_mse,
                'max_error': linear_max_err,
                'equation': f"mass_fraction = {a_linear:.4f} * evaporation_ratio + {b_linear:.4f}"
            },
            'quadratic': {
                'params': quad_coeffs,
                'r2': quad_r2,
                'mae': quad_mae,
                'mse': quad_mse,
                'max_error': quad_max_err,
                'equation': f"mass_fraction = {quad_coeffs[0]:.4f} * x² + {quad_coeffs[1]:.4f} * x + {quad_coeffs[2]:.4f}"
            },
            'exponential': {
                'params': exp_params,
                'r2': exp_r2,
                'mae': exp_mae,
                'mse': exp_mse,
                'max_error': exp_max_err,
                'equation': exp_equation
            }
        }
        results[ion_name] = {
            'initial_volume': initial_volume,
            'evaporation_ratio': x_fit,
            'mass_fraction': y_fit,
            'models': models,
        }
        print(f"  Linear fit (last 5 points): R² = {linear_r2:.4f}, MAE = {linear_mae:.4e}, MSE = {linear_mse:.4e}, Max Error = {linear_max_err:.4e}")
        print(f"    Equation: {models['linear']['equation']}")
        print(f"  Quadratic fit (last 5 points): R² = {quad_r2:.4f}, MAE = {quad_mae:.4e}, MSE = {quad_mse:.4e}, Max Error = {quad_max_err:.4e}")
        print(f"    Equation: {models['quadratic']['equation']}")
        print(f"  Exponential fit (last 5 points): R² = {exp_r2:.4f}, MAE = {exp_mae:.4e}, MSE = {exp_mse:.4e}, Max Error = {exp_max_err:.4e}")
        print(f"    Equation: {models['exponential']['equation']}")
    return results

def plot_results(results, save_plots=True):
    n_ions = len(results)
    fig, axes = plt.subplots(1, n_ions, figsize=(11, 6))
    if n_ions == 1:
        axes = [axes]
    for i, (ion_name, result) in enumerate(results.items()):
        ax = axes[i]
        x = result['evaporation_ratio']
        y = result['mass_fraction']
        ax.scatter(x, y, alpha=0.7, label='Data', color='blue')
        x_fit = np.linspace(np.min(x), np.max(x), 100)
        # Linear fit
        a, b = result['models']['linear']['params']
        y_fit_linear = a * x_fit + b
        ax.plot(x_fit, y_fit_linear, 'r-', label=f'Linear fit (R²={result["models"]["linear"]["r2"]:.3f})')
        # Quadratic fit
        quad_coeffs = result['models']['quadratic']['params']
        y_fit_quad = np.polyval(quad_coeffs, x_fit)
        ax.plot(x_fit, y_fit_quad, 'g--', label=f'Quadratic fit (R²={result["models"]["quadratic"]["r2"]:.3f})')
        # Exponential fit
        exp_params = result['models']['exponential']['params']
        if exp_params is not None:
            y_fit_exp = exp_params[0] * np.exp(exp_params[1] * x_fit) + exp_params[2]
            ax.plot(x_fit, y_fit_exp, 'm-.', label=f'Exponential fit (R²={result["models"]["exponential"]["r2"]:.3f})')
        ax.set_xlabel('Water Evaporation Ratio')
        ax.set_ylabel('Mass Fraction Remaining')
        ax.set_title(f'{ion_name}')
        ax.legend()
        ax.grid(True, alpha=0.3)
        # Add textbox with equations and error metrics
        eqn_text = ""
        for model_name, model in result['models'].items():
            eqn_text += f"{model_name.capitalize()}\n"
            eqn_text += f"    Eqn: {model['equation']}\n"
            eqn_text += f"    R²     : {model['r2']:<8.4f}\n"
            eqn_text += f"    MAE    : {model['mae']:<8.2e}\n"
            eqn_text += f"    MSE    : {model['mse']:<8.2e}\n"
            eqn_text += f"    MaxErr : {model['max_error']:<8.2e}\n"
            eqn_text += "\n"
        # Place the textbox a little more to the left
        ax.annotate(
            eqn_text,
            xy=(0.6, 0.97), xycoords='axes fraction',
            fontsize=8, va='top', ha='left',
            bbox=dict(boxstyle='round,pad=0.1,rounding_size=0.2', facecolor='wheat', alpha=1.0),
            family='monospace'
        )
    plt.subplots_adjust(right=0.62, left=0.13, top=0.92, bottom=0.12)
    if save_plots:
        plt.savefig('ion_evaporation_behavior.png', dpi=300, bbox_inches='tight')
    plt.show()

def generate_summary_report(results):
    print("\n" + "="*80)
    print("MASS FRACTION ANALYSIS SUMMARY REPORT")
    print("="*80)
    print(f"\nAnalyzed {len(results)} ions:")
    for ion_name in results.keys():
        print(f"  - {ion_name}")
    print("\nBest-fit equations and error metrics for each ion:")
    print("-" * 50)
    for ion_name, result in results.items():
        print(f"\n{ion_name}:")
        for model_name, model_info in result['models'].items():
            print(f"  {model_name.capitalize()} fit:")
            print(f"    R² Score: {model_info['r2']:.4f}")
            print(f"    MAE: {model_info['mae']:.4e}")
            print(f"    MSE: {model_info['mse']:.4e}")
            print(f"    Max Error: {model_info['max_error']:.4e}")
            print(f"    Equation: {model_info['equation']}")
        
        # Find ions with different behaviors
    print("\n" + "="*50)
    print("BEHAVIOR ANALYSIS")
    print("="*50)
    
    # Group ions by best model
    model_groups = {}
    for ion_name, result in results.items():
        best_model = result['best_model']
        if best_model not in model_groups:
            model_groups[best_model] = []
        model_groups[best_model].append(ion_name)
    
    for model, ions in model_groups.items():
        print(f"\nIons best described by {model} model:")
        for ion in ions:
            r2 = results[ion]['best_r2']
            print(f"  - {ion} (R² = {r2:.4f})")

def main():
    # Define data directory
    data_dir = "mass_fraction_data"
    
    # Check if data directory exists
    if not os.path.exists(data_dir):
        print(f"Error: Data directory '{data_dir}' not found!")
        print("Please ensure the mass_fraction_data directory is in the same location as this script.")
        return
    
    print("Loading ion data...")
    ion_data = load_ion_data(data_dir)
    
    # Focus only on lithium (Li_+1_)
    lithium_key = None
    for key in ion_data.keys():
        if key.lower() in ["li+1", "li+1_", "li_+1_", "li1"]:
            lithium_key = key
            break
    if not lithium_key:
        print("Lithium data not found!")
        return

    lithium_data = ion_data[lithium_key]
    
    # Calculate evaporation ratio
    initial_volume = np.max(lithium_data['volume_m3'])
    evaporation_ratio = calculate_evaporation_ratio(lithium_data['volume_m3'], initial_volume)
    lithium_data = lithium_data.copy()
    lithium_data['evaporation_ratio'] = evaporation_ratio
    # Do not filter by evaporation_ratio >= 0.5, let drop-off detection handle it
    ion_data = {lithium_key: lithium_data}

    print(f"Loaded lithium data: {lithium_key}")
    print(f"  Data points: {len(lithium_data)}")

    # Analyze ion behavior
    print("\nAnalyzing lithium behavior during late-stage evaporation...")
    results = analyze_ion_behavior(ion_data)
    
    # Generate plots
    print("\nGenerating plots...")
    plot_results(results)
    
    # Generate summary report
    generate_summary_report(results)
    
    print("\nAnalysis complete! Plots saved as 'ion_evaporation_behavior.png'")

if __name__ == "__main__":
    main()