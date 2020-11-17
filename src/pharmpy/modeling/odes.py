import sympy

import pharmpy.symbols
from pharmpy.parameter import Parameter
from pharmpy.statements import Assignment, Bolus, CompartmentalSystem, ExplicitODESystem, Infusion


def add_parameter(model, name):
    """Add an individual or pk parameter to a model"""
    _add_parameter(model, name)
    return model


def _add_parameter(model, name):
    pops = model.create_symbol(f'POP_{name}')
    pop_param = Parameter(pops.name, init=0.1, lower=0)
    model.parameters.add(pop_param)
    symb = model.create_symbol(name)
    ass = Assignment(symb, pop_param.symbol)
    model.statements.insert(0, ass)
    return symb


def explicit_odes(model):
    """Convert model from compartmental system to explicit ODE system
    or do nothing if it already has an explicit ODE system
    """
    statements = model.statements
    odes = statements.ode_system
    if isinstance(odes, CompartmentalSystem):
        eqs, ics = odes.to_explicit_odes()
        new = ExplicitODESystem(eqs, ics)
        statements[model.statements.index(odes)] = new
        model.statements = statements
    return model


def first_order_elimination(model):
    return model


def zero_order_elimination(model):
    _do_michaelis_menten_elimination(model)
    obs = model.dataset.pharmpy.observations
    init = obs.min() / 100  # 1% of smallest observation
    model.parameters['POP_KM'].init = init
    model.parameters['POP_KM'].fix = True
    return model


def michaelis_menten_elimination(model):
    _do_michaelis_menten_elimination(model)
    return model


def combined_mm_fo_elimination(model):
    _do_michaelis_menten_elimination(model, combined=True)
    return model


def _do_michaelis_menten_elimination(model, combined=False):
    km = _add_parameter(model, 'KM')
    clmm = _add_parameter(model, 'CLMM')
    odes = model.statements.ode_system
    central = odes.find_central()
    output = odes.find_output()
    old_rate = odes.get_flow(central, output)
    numer, denom = old_rate.as_numer_denom()
    if denom != 1:
        if combined:
            cl = numer
        vc = denom
    else:
        if combined:
            cl = _add_parameter(model, 'CL')
        vc = _add_parameter(model, 'VC')
    if not combined:
        cl = 0

    amount = sympy.Function(central.amount.name)(pharmpy.symbols.symbol('t'))
    rate = (clmm * km / (km + amount / vc) + cl) / vc
    odes.add_flow(central, output, rate)
    model.statements.remove_symbol_definitions(numer.free_symbols, odes)
    model.remove_unused_parameters_and_rvs()
    return model


def set_transit_compartments(model, n):
    """Set the number of transit compartments of model"""
    statements = model.statements
    odes = statements.ode_system
    transits = odes.find_transit_compartments(statements)
    if len(transits) == n:
        pass
    elif len(transits) == 0:
        mdt_symb = _add_parameter(model, 'MDT')
        rate = n / mdt_symb
        comp = odes.find_dosing()
        dose = comp.dose
        comp.dose = None
        while n > 0:
            new_comp = odes.add_compartment(f'TRANSIT{n}')
            n -= 1
            odes.add_flow(new_comp, comp, rate)
            comp = new_comp
        comp.dose = dose
    elif len(transits) > n:
        nremove = len(transits) - n
        comp = odes.find_dosing()
        dose = comp.dose
        removed_symbols = set()
        while nremove > 0:
            to_comp, to_flow = odes.get_compartment_outflows(comp)[0]
            odes.remove_compartment(comp)
            removed_symbols |= to_flow.free_symbols
            comp = to_comp
            nremove -= 1
        comp.dose = dose
        statements.remove_symbol_definitions(removed_symbols, odes)
        model.remove_unused_parameters_and_rvs()
    else:
        nadd = n - len(transits)
        comp = odes.find_dosing()
        dose = comp.dose
        _, rate = odes.get_compartment_outflows(comp)[0]
        comp.dose = None
        while nadd > 0:
            new_comp = odes.add_compartment(f'TRANSIT{len(transits) + nadd}')
            nadd -= 1
            odes.add_flow(new_comp, comp, rate)
            comp = new_comp
        comp.dose = dose
    return model


def add_lag_time(model):
    """Add lag time to the dose compartment of model"""
    odes = model.statements.ode_system
    dosing_comp = odes.find_dosing()
    old_lag_time = dosing_comp.lag_time
    mdt_symb = _add_parameter(model, 'MDT')
    dosing_comp.lag_time = mdt_symb
    if old_lag_time:
        model.statements.remove_symbol_definitions(old_lag_time.free_symbols, odes)
        model.remove_unused_parameters_and_rvs()
    return model


def remove_lag_time(model):
    """Remove lag time from the dose compartment of model"""
    odes = model.statements.ode_system
    dosing_comp = odes.find_dosing()
    lag_time = dosing_comp.lag_time
    if lag_time:
        symbols = lag_time.free_symbols
        dosing_comp.lag_time = 0
        model.statements.remove_symbol_definitions(symbols, odes)
        model.remove_unused_parameters_and_rvs()
    return model


def zero_order_absorption(model):
    """Set or change to zero order absorption rate

    Parameters
    ----------
    model
        Model to set or change to first order absorption rate
    """
    statements = model.statements
    odes = statements.ode_system
    if not isinstance(odes, CompartmentalSystem):
        raise ValueError("Setting absorption is not supported for ExplicitODESystem")
    depot = odes.find_depot(statements)

    dose_comp = odes.find_dosing()
    symbols = dose_comp.free_symbols
    dose = dose_comp.dose
    if depot:
        to_comp, _ = odes.get_compartment_outflows(depot)[0]
        ka = odes.get_flow(depot, odes.find_central())
        odes.remove_compartment(depot)
        symbols |= ka.free_symbols
        to_comp.dose = dose
    else:
        to_comp = dose_comp
    statements.remove_symbol_definitions(symbols, odes)
    model.remove_unused_parameters_and_rvs()
    if not have_zero_order_absorption(model):
        add_zero_order_absorption(model, dose.amount, to_comp, 'MAT')
    return model


def first_order_absorption(model):
    """Set or change to first order absorption rate

    Parameters
    ----------
    model
        Model to set or change to bolus absorption rate
    """
    statements = model.statements
    odes = statements.ode_system
    if not isinstance(odes, CompartmentalSystem):
        raise ValueError("Setting absorption is not supported for ExplicitODESystem")
    depot = odes.find_depot(statements)

    dose_comp = odes.find_dosing()
    amount = dose_comp.dose.amount
    symbols = dose_comp.free_symbols
    if depot:
        dose_comp.dose = Bolus(depot.dose.amount)
    else:
        dose_comp.dose = None
    statements.remove_symbol_definitions(symbols, odes)
    model.remove_unused_parameters_and_rvs()
    if not depot:
        add_first_order_absorption(model, Bolus(amount), dose_comp)
    return model


def bolus_absorption(model):
    """Set or change to bolus absorption rate

    Parameters
    ----------
    model
        Model to set or change absorption rate
    """
    statements = model.statements
    odes = statements.ode_system
    if not isinstance(odes, CompartmentalSystem):
        raise ValueError("Setting absorption is not supported for ExplicitODESystem")
    depot = odes.find_depot(statements)
    if depot:
        to_comp, _ = odes.get_compartment_outflows(depot)[0]
        to_comp.dose = depot.dose
        ka = odes.get_flow(depot, odes.find_central())
        odes.remove_compartment(depot)
        symbols = ka.free_symbols
        statements.remove_symbol_definitions(symbols, odes)
        model.remove_unused_parameters_and_rvs()
    if have_zero_order_absorption(model):
        dose_comp = odes.find_dosing()
        old_symbols = dose_comp.free_symbols
        dose_comp.dose = Bolus(dose_comp.dose.amount)
        unneeded_symbols = old_symbols - dose_comp.dose.free_symbols
        statements.remove_symbol_definitions(unneeded_symbols, odes)
        model.remove_unused_parameters_and_rvs()
    return model


def seq_zo_fo_absorption(model):
    """Set or change to sequential zero order first order absorption rate

    Parameters
    ----------
    model
        Model to set or change absorption rate
    """
    statements = model.statements
    odes = statements.ode_system
    if not isinstance(odes, CompartmentalSystem):
        raise ValueError("Setting absorption is not supported for ExplicitODESystem")
    depot = odes.find_depot(statements)

    dose_comp = odes.find_dosing()
    have_ZO = have_zero_order_absorption(model)
    if depot and not have_ZO:
        add_zero_order_absorption(model, dose_comp.amount, depot, 'MDT')
    elif not depot and have_ZO:
        add_first_order_absorption(model, dose_comp.dose, dose_comp)
        dose_comp.dose = None
    elif not depot and not have_ZO:
        amount = dose_comp.dose.amount
        dose_comp.dose = None
        depot = add_first_order_absorption(model, amount, dose_comp)
        add_zero_order_absorption(model, amount, depot, 'MDT')
    return model


def have_zero_order_absorption(model):
    """Check if ode system describes a zero order absorption

    currently defined as having Infusion dose with rate not in dataset
    """
    odes = model.statements.ode_system
    dosing = odes.find_dosing()
    dose = dosing.dose
    if isinstance(dose, Infusion):
        if dose.rate is None:
            value = dose.duration
        else:
            value = dose.rate
        if isinstance(value, sympy.Symbol) or isinstance(value, str):
            name = str(value)
            if name not in model.dataset.columns:
                return True
    return False


def add_zero_order_absorption(model, amount, to_comp, parameter_name):
    """Add zero order absorption to a compartment.
    Disregards what is currently in the model.
    """
    mat_symb = _add_parameter(model, parameter_name)
    new_dose = Infusion(amount, duration=mat_symb * 2)
    to_comp.dose = new_dose


def add_first_order_absorption(model, dose, to_comp):
    """Add first order absorption
    Disregards what is currently in the model.
    """
    odes = model.statements.ode_system
    depot = odes.add_compartment('DEPOT')
    depot.dose = dose
    mat_symb = _add_parameter(model, 'MAT')
    odes.add_flow(depot, to_comp, 1 / mat_symb)
    return depot
