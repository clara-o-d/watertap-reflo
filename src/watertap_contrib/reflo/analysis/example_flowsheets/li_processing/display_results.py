from pyomo.environ import value


def display_results(m):
    # Print main product and waste flows
    print("\n=== PQC Lithium Flowsheet Results ===")
    print(f"Li2CO3 product flow: {value(m.fs.li2co3_product.properties[0].flow_mass_phase_comp['Liq', 'li+']):.3f} kg/s")
    print(f"Solid waste flow: {value(m.fs.solid_waste.properties[0].flow_mass_phase_comp['Liq', 'tss']):.3f} kg/s")
    print(f"Liquid waste flow: {value(m.fs.liquid_waste.properties[0].flow_mass_phase_comp['Liq', 'tds']):.3f} kg/s")
    print("(Add more detailed reporting as needed)")
    
    # Print costing summary
    if hasattr(m.fs, "costing"):
        print("\n--- Costing ---")
        if hasattr(m.fs.costing, "aggregate_capital_cost"):
            print(f"Aggregate capital cost: {value(m.fs.costing.aggregate_capital_cost):.2f}")
        if hasattr(m.fs.costing, "aggregate_fixed_operating_cost"):
            print(f"Aggregate fixed OPEX: {value(m.fs.costing.aggregate_fixed_operating_cost):.2f}/year")
        if hasattr(m.fs.costing, "LCOLi2CO3"):
            print(f"Levelized cost of Li2CO3: {value(m.fs.costing.LCOLi2CO3):.2f} $/t")
        if hasattr(m.fs.costing, "LCOLiOH_H2O"):
            print(f"Levelized cost of LiOH·H2O: {value(m.fs.costing.LCOLiOH_H2O):.2f} $/t")
        if hasattr(m.fs.costing, "LCOLi"):
            print(f"Levelized cost of Li (volumetric): {value(m.fs.costing.LCOLi):.2f} $/m³") 