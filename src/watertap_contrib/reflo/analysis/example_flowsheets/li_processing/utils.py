from pyomo.environ import units as pyunits, value


def calculate_lithium_recovery(m):
    """Calculate lithium recovery across the flowsheet"""
    li_in = value(m.fs.feed.properties[0].flow_mol_phase_comp["Liq", "li+"])
    li_out_li2co3 = value(m.fs.li2co3_product.properties[0].flow_mol_phase_comp["Liq", "li+"])
    
    # Only Li2CO3 recovery since LiOH section is not implemented
    recovery = (li_out_li2co3 / li_in) * 100
    
    print(f"Lithium recovery: {recovery:.2f}%")
    return recovery


def calculate_water_balance(m):
    """Calculate water balance across the flowsheet"""
    water_in = value(m.fs.feed.properties[0].flow_mol_phase_comp["Liq", "H2O"])
    
    # Sum all water outputs (only existing streams)
    water_out_li2co3 = value(m.fs.li2co3_product.properties[0].flow_mol_phase_comp["Liq", "H2O"])
    water_out_softening_waste = value(m.fs.li2co3_softening_waste.properties[0].flow_mol_phase_comp["Liq", "H2O"])
    water_out_separation_waste = value(m.fs.li2co3_separation_waste.properties[0].flow_mol_phase_comp["Liq", "H2O"])
    
    total_water_out = water_out_li2co3 + water_out_softening_waste + water_out_separation_waste
    water_recovery = (water_out_li2co3 / water_in) * 100
    balance_error = ((water_in - total_water_out) / water_in) * 100
    
    print(f"Water recovery to product: {water_recovery:.2f}%")
    print(f"Water balance error: {balance_error:.2f}%")
    return water_recovery


def calculate_product_purity(m):
    """Calculate product purity for Li2CO3"""
    # Li2CO3 product purity
    li2co3_li_flow = value(m.fs.li2co3_product.properties[0].flow_mol_phase_comp["Liq", "li+"])
    
    li2co3_total_solutes = 0
    for component in m.fs.properties.component_list:
        if component != "H2O":
            li2co3_total_solutes += value(m.fs.li2co3_product.properties[0].flow_mol_phase_comp["Liq", component])
    
    li2co3_purity = (li2co3_li_flow / li2co3_total_solutes) * 100 if li2co3_total_solutes > 0 else 0
    
    print(f"Li2CO3 product lithium purity: {li2co3_purity:.2f}%")
    return li2co3_purity 