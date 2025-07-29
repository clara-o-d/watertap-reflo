from pyomo.environ import units as pyunits, value


def calculate_lithium_recovery(m):
    """Calculate lithium recovery across the flowsheet"""
    li_in = value(m.fs.feed.properties[0].flow_mol_phase_comp["Liq", "li+"])
    li_out_li2co3 = value(m.fs.li2co3_product.properties[0].flow_mol_phase_comp["Liq", "li+"])
    li_out_lioh = value(m.fs.lioh_product.properties[0].flow_mol_phase_comp["Liq", "li+"])
    
    total_li_out = li_out_li2co3 + li_out_lioh
    recovery = (total_li_out / li_in) * 100
    
    print(f"Lithium recovery: {recovery:.2f}%")
    return recovery


def calculate_water_balance(m):
    """Calculate water balance across the flowsheet"""
    water_in = value(m.fs.feed.properties[0].flow_mol_phase_comp["Liq", "H2O"])
    
    # Sum all water outputs
    water_out_li2co3 = value(m.fs.li2co3_product.properties[0].flow_mol_phase_comp["Liq", "H2O"])
    water_out_lioh = value(m.fs.lioh_product.properties[0].flow_mol_phase_comp["Liq", "H2O"])
    water_out_li2co3_waste = value(m.fs.li2co3_waste.properties[0].flow_mol_phase_comp["Liq", "H2O"])
    water_out_lioh_waste = value(m.fs.lioh_liquidwaste.properties[0].flow_mol_phase_comp["Liq", "H2O"])
    
    total_water_out = water_out_li2co3 + water_out_lioh + water_out_li2co3_waste + water_out_lioh_waste
    balance = ((water_in - total_water_out) / water_in) * 100
    
    print(f"Water balance error: {balance:.2f}%")
    return balance


def calculate_product_purity(m):
    """Calculate product purity for Li2CO3 and LiOH"""
    # Li2CO3 product purity
    li2co3_li_flow = value(m.fs.li2co3_product.properties[0].flow_mol_phase_comp["Liq", "li+"])
    
    li2co3_total_solutes = 0
    for component in m.fs.properties.component_list:
        if component != "H2O":
            li2co3_total_solutes += value(m.fs.li2co3_product.properties[0].flow_mol_phase_comp["Liq", component])
    
    li2co3_purity = (li2co3_li_flow / li2co3_total_solutes) * 100 if li2co3_total_solutes > 0 else 0
    
    # LiOH product purity
    lioh_li_flow = value(m.fs.lioh_product.properties[0].flow_mol_phase_comp["Liq", "li+"])
    
    lioh_total_solutes = 0
    for component in m.fs.properties.component_list:
        if component != "H2O":
            lioh_total_solutes += value(m.fs.lioh_product.properties[0].flow_mol_phase_comp["Liq", component])
    
    lioh_purity = (lioh_li_flow / lioh_total_solutes) * 100 if lioh_total_solutes > 0 else 0
    
    print(f"Li2CO3 product purity: {li2co3_purity:.2f}%")
    print(f"LiOH product purity: {lioh_purity:.2f}%")
    
    return li2co3_purity, lioh_purity 