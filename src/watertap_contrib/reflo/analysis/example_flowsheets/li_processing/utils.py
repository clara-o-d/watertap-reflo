from pyomo.environ import units as pyunits, value


def compute_lithium_recovery_efficiency(m):
    """Compute overall lithium recovery efficiency"""
    li_in = value(m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "li+"])
    li_out_li2co3 = value(m.fs.li2co3_product.properties[0].flow_mass_phase_comp["Liq", "li+"])
    li_out_lioh = value(m.fs.lioh_product.properties[0].flow_mass_phase_comp["Liq", "li+"])
    
    total_li_recovered = li_out_li2co3 + li_out_lioh
    recovery_efficiency = total_li_recovered / li_in if li_in > 0 else 0
    
    return recovery_efficiency


def compute_water_balance(m):
    """Compute water balance across the system"""
    water_in = value(m.fs.feed.properties[0].flow_mass_phase_comp["Liq", "H2O"])
    
    # Calculate water in all outlet streams
    water_out_li2co3 = value(m.fs.li2co3_product.properties[0].flow_mass_phase_comp["Liq", "H2O"])
    water_out_lioh = value(m.fs.lioh_product.properties[0].flow_mass_phase_comp["Liq", "H2O"])
    water_out_solid_waste = value(m.fs.solid_waste.properties[0].flow_mass_phase_comp["Liq", "H2O"])
    water_out_liquid_waste = value(m.fs.liquid_waste.properties[0].flow_mass_phase_comp["Liq", "H2O"])
    water_out_lioh_waste = value(m.fs.lioh_liquidwaste.properties[0].flow_mass_phase_comp["Liq", "H2O"])
    
    total_water_out = (water_out_li2co3 + water_out_lioh + water_out_solid_waste + 
                      water_out_liquid_waste + water_out_lioh_waste)
    
    water_loss = water_in - total_water_out
    
    return {
        'water_in': water_in,
        'total_water_out': total_water_out,
        'water_loss': water_loss,
        'water_balance_closure': water_loss / water_in if water_in > 0 else 0
    }


def compute_product_purities(m):
    """Compute product purities for Li2CO3 and LiOH"""
    # Li2CO3 purity calculation
    li2co3_li_flow = value(m.fs.li2co3_product.properties[0].flow_mass_phase_comp["Liq", "li+"])
    li2co3_total_solutes = 0
    for component in ["li+", "boron", "borate", "Ca_2+", "Mg_2+", "Na+", "Cl-", "CO3-2", "HCO3-", "tss", "tds", "Alkalinity_2-"]:
        li2co3_total_solutes += value(m.fs.li2co3_product.properties[0].flow_mass_phase_comp["Liq", component])
    
    li2co3_purity = li2co3_li_flow / li2co3_total_solutes if li2co3_total_solutes > 0 else 0
    
    # LiOH purity calculation  
    lioh_li_flow = value(m.fs.lioh_product.properties[0].flow_mass_phase_comp["Liq", "li+"])
    lioh_total_solutes = 0
    for component in ["li+", "boron", "borate", "Ca_2+", "Mg_2+", "Na+", "Cl-", "CO3-2", "HCO3-", "tss", "tds", "Alkalinity_2-"]:
        lioh_total_solutes += value(m.fs.lioh_product.properties[0].flow_mass_phase_comp["Liq", component])
    
    lioh_purity = lioh_li_flow / lioh_total_solutes if lioh_total_solutes > 0 else 0
    
    return {
        'li2co3_purity': li2co3_purity,
        'lioh_purity': lioh_purity
    } 