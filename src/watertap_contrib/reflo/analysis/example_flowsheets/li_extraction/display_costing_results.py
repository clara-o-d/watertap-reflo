from pyomo.environ import value

def display_costing_results(m):
    print("\n" + "="*50)
    print("COSTING RESULTS")
    print("="*50)
    try:
        if hasattr(m.fs.pond.costing, 'capital_cost'):
            print(f"Pond capital cost: ${value(m.fs.pond.costing.capital_cost):,.0f}")
        if hasattr(m.fs.pump.costing, 'capital_cost'):
            print(f"Pump capital cost: ${value(m.fs.pump.costing.capital_cost):,.0f}")
        if hasattr(m.fs.costing, 'total_capital_cost'):
            print(f"Total capital cost: ${value(m.fs.costing.total_capital_cost):,.0f}")
        if hasattr(m.fs.costing, 'LCOLi'):
            lcoli_vol = value(m.fs.costing.LCOLi)
            lcoli_mass = value(m.fs.costing.LCOLi_mass)
            print(f"Levelized Cost of Lithium (LCOLi): ${lcoli_vol:.2f} per m³ Li, ${lcoli_mass:.2f} per mt Li")
    except Exception as e:
        print(f"Error displaying costing results: {e}")
    print("="*50) 