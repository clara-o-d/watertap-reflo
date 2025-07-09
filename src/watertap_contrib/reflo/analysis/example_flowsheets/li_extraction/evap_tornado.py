import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os


def load_and_process_data(filename):
    """Load and process the parameter sweep results"""
    df = pd.read_csv(filename)
    df.columns = df.columns.str.strip()
    
    # Print available columns for debugging
    print(f"Available columns: {list(df.columns)}")
    
    return df

def oat_sensitivity(df, target_col='pond capital cost (USD_2023)'):
    """
    One-at-a-time sensitivity analysis
    
    Args:
        df: DataFrame with parameter sweep results
        target_col: Column name for the target variable to analyze
    """
    # Get parameter columns (exclude output columns)
    output_cols = [target_col]
    param_cols = [col for col in df.columns if col not in output_cols]
    
    print(f"Analyzing sensitivity of '{target_col}' to {len(param_cols)} parameters:")
    for col in param_cols:
        print(f"  - {col}")
    
    sensitivity_data = []
    for var in param_cols:
        x_vals = df[var].values
        y_vals = df[target_col].values
        
        # Skip if we don't have the target column
        if target_col not in df.columns:
            print(f"Warning: Target column '{target_col}' not found in data")
            continue
            
        # Find median, min, max x
        x_median = np.median(x_vals)
        x_min = np.min(x_vals)
        x_max = np.max(x_vals)
        
        # Find y at closest to median, min, max x
        y_med = y_vals[np.argmin(np.abs(x_vals - x_median))]
        y_min = y_vals[np.argmin(np.abs(x_vals - x_min))]
        y_max = y_vals[np.argmin(np.abs(x_vals - x_max))]
        
        # Calculate percentage changes
        # Increase: median -> max
        x_range_pct_inc = (x_max - x_median) / x_median * 100 if x_median != 0 else np.nan
        y_range_pct_inc = (y_max - y_med) / y_med * 100 if y_med != 0 else np.nan
        pct_per_pct_inc = y_range_pct_inc / x_range_pct_inc if x_range_pct_inc and not np.isnan(x_range_pct_inc) else np.nan
        
        # Decrease: median -> min
        x_range_pct_dec = (x_min - x_median) / x_median * 100 if x_median != 0 else np.nan
        y_range_pct_dec = (y_min - y_med) / y_med * 100 if y_med != 0 else np.nan
        pct_per_pct_dec = y_range_pct_dec / x_range_pct_dec if x_range_pct_dec and not np.isnan(x_range_pct_dec) else np.nan
        
        sensitivity_data.append({
            'variable': var,
            'pct_per_pct_increase': pct_per_pct_inc,
            'pct_per_pct_decrease': pct_per_pct_dec,
            'x_median': x_median,
            'x_min': x_min,
            'x_max': x_max,
            'y_median': y_med,
            'y_min': y_min,
            'y_max': y_max
        })
    
    return pd.DataFrame(sensitivity_data)

def create_tornado_plot(sensitivity_df, target_col, title=None):
    """Create a tornado plot showing parameter sensitivity"""
    if title is None:
        title = f"Sensitivity Analysis: {target_col}"
    
    # Sort by the largest absolute effect (either direction)
    sensitivity_df = sensitivity_df.sort_values(
        by=['pct_per_pct_increase', 'pct_per_pct_decrease'],
        key=lambda x: np.abs(x),
        ascending=True
    )
    
    fig, ax = plt.subplots(figsize=(12, 8))
    y_pos = np.arange(len(sensitivity_df))

    # Plot both bars at the same y position
    bars_increase = ax.barh(
        y_pos, 
        sensitivity_df['pct_per_pct_increase'], 
        height=0.5, 
        color='#3b82f6', 
        alpha=0.7, 
        label='Increase (median→max)'
    )
    bars_decrease = ax.barh(
        y_pos, 
        -sensitivity_df['pct_per_pct_decrease'], 
        height=0.5, 
        color='#ef4444', 
        alpha=0.7, 
        label='Decrease (median→min)'
    )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(sensitivity_df['variable'], fontsize=10)
    ax.set_xlabel(f'Percent change in {target_col} per percent change in parameter', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
    ax.grid(True, alpha=0.3, axis='x')
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='lower right')
    plt.tight_layout()
    return fig, ax

def create_multiple_tornado_plots(df, output_cols):
    """Create tornado plots for multiple output variables"""
    sensitivity_results = {}
    
    for target_col in output_cols:
        if target_col in df.columns:
            print(f"\nAnalyzing sensitivity for: {target_col}")
            sensitivity_df = oat_sensitivity(df, target_col)
            
            if not sensitivity_df.empty:
                # Create tornado plot
                fig, ax = create_tornado_plot(sensitivity_df, target_col)
                
                # Save plot
                filename = f"tornado_plot_{target_col.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')}.png"
                plt.savefig(filename, dpi=300, bbox_inches='tight')
                print(f"Plot saved as '{filename}'")
                plt.close()  # Close to free memory
                
                # Save sensitivity data
                csv_filename = f"sensitivity_analysis_{target_col.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')}.csv"
                sensitivity_df.to_csv(csv_filename, index=False)
                print(f"Sensitivity data saved to '{csv_filename}'")
                
                sensitivity_results[target_col] = sensitivity_df
            else:
                print(f"No sensitivity data calculated for {target_col}")
        else:
            print(f"Target column '{target_col}' not found in data")
    
    return sensitivity_results

def main():
    target_col = 'pond capital cost (USD_2023)'
    possible_files = ['pond_sensitivity.csv', 'test_pond_sensitivity.csv']
    df = None
    for filename in possible_files:
        if os.path.exists(filename):
            print(f"Loading data from '{filename}'...")
            try:
                df = load_and_process_data(filename)
                print(f"Successfully loaded {len(df)} data points with {len(df.columns)} variables.")
                break
            except Exception as e:
                print(f"Error loading {filename}: {e}")
                continue
    if df is None:
        print("Error: No parameter sweep results found. Please run the parameter sweep first.")
        print("Expected files: pond_sensitivity.csv or test_pond_sensitivity.csv")
        return
    print(f"\nCreating tornado plot for: {target_col}")
    sensitivity_df = oat_sensitivity(df, target_col)
    if not sensitivity_df.empty:
        fig, ax = create_tornado_plot(sensitivity_df, target_col, title=f"Evaporation Pond Sensitivity Analysis: {target_col}")
        plt.savefig('tornado_plot_pond_capital_cost.png', dpi=300, bbox_inches='tight')
        print("Plot saved as 'tornado_plot_pond_capital_cost.png'")
        plt.show()
        sensitivity_df.to_csv('sensitivity_analysis_pond_capital_cost.csv', index=False)
        print("Sensitivity analysis results saved to 'sensitivity_analysis_pond_capital_cost.csv'")
    else:
        print("No valid sensitivity data calculated.")
    print("\nTornado plot analysis completed!")

if __name__ == "__main__":
    main()