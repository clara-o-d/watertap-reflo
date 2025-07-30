import pyomo.environ as pyo
from pyomo.environ import Param, Var, Constraint, Expression
from pyomo.environ import units as pyunits


def process_costing(m):
    # Initialize costing for units that have costing blocks
    if hasattr(m.fs, 'boron_removal') and hasattr(m.fs.boron_removal, 'costing'):
        try:
            m.fs.boron_removal.costing.initialize()
        except Exception as e:
            print(f"Warning: Could not initialize costing for boron_removal: {e}")
    
    if hasattr(m.fs, 'softening') and hasattr(m.fs.softening, 'costing'):
        try:
            m.fs.softening.costing.initialize()
        except Exception as e:
            print(f"Warning: Could not initialize costing for softening: {e}")
    
    # Process costing for both costing blocks
    for costing_name in ['treatment_costing', 'reflo_costing']:
        if hasattr(m.fs, costing_name):
            costing_block = getattr(m.fs, costing_name)
            try:
                costing_block.cost_process()
                costing_block.initialize()
            except Exception as e:
                print(f"Warning: Could not process costing for {costing_name}: {e}")

    # Create a simple aggregated costing summary
    # Calculate total capital and operating costs across both costing blocks
    m.fs.total_capital_cost = Expression(
        expr=sum(
            getattr(m.fs, costing_name).total_capital_cost
            for costing_name in ['treatment_costing', 'reflo_costing'] 
            if hasattr(m.fs, costing_name)
        ),
        doc="Total capital cost across all costing blocks"
    )
    
    m.fs.total_operating_cost = Expression(
        expr=sum(
            getattr(m.fs, costing_name).total_operating_cost
            for costing_name in ['treatment_costing', 'reflo_costing'] 
            if hasattr(m.fs, costing_name)
        ),
        doc="Total operating cost across all costing blocks"
    )
    
    # Add basic LCOW calculation to one of the costing blocks (using reflo_costing if available)
    costing_for_lcow = None
    if hasattr(m.fs, 'reflo_costing'):
        costing_for_lcow = m.fs.reflo_costing
    elif hasattr(m.fs, 'treatment_costing'):
        costing_for_lcow = m.fs.treatment_costing
        
    if costing_for_lcow is not None:
        try:
            # Use the product flow for LCOW calculation
            product_flow = m.fs.li2co3_product.properties[0].flow_vol_phase["Liq"]
            costing_for_lcow.add_LCOW(product_flow)
        except Exception as e:
            print(f"Warning: Could not add LCOW calculation: {e}") 