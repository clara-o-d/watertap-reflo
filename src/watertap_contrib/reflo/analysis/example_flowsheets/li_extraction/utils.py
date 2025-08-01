from pyomo.environ import value
from scipy.optimize import root_scalar

def compute_evaporation_fraction_for_target_li_conc(m, target_li_conc):
    prop_in = m.fs.feed.properties[0]
    li_inlet_flow = value(prop_in.flow_mass_phase_comp["Liq", "Li+"])
    water_inlet_flow = value(prop_in.flow_mass_phase_comp["Liq", "H2O"])
    rho_val = value(m.fs.rho)
    a = 88.1606
    b_ = -169.2358
    c = 81.4783

    def li_conc_at_evap(evap_frac):
        li_mass_frac = max(0, min(a * evap_frac**2 + b_ * evap_frac + c, 1))
        li_outflow = li_inlet_flow * li_mass_frac
        water_outflow = water_inlet_flow * (1 - evap_frac)
        if water_outflow < 1e-12:
            return 0
        return li_outflow / water_outflow * 1000#rho_val

    sol = root_scalar(
        lambda evap_frac: li_conc_at_evap(evap_frac) - target_li_conc,
        bracket=[0.01, 0.99],
        method='bisect'
    )
    if not sol.converged:
        raise RuntimeError("Could not find evaporation fraction for target Li+ concentration")
    return sol.root 