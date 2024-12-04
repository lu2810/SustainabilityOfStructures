#  from scipy.optimize import direct
import struct_analysis
from scipy.optimize import basinhopping  # import Minimierungsfunktion aus dem SyiPy-Paket
from scipy.optimize import minimize  # import Minimierungsfunktion aus dem SyiPy-Paket

# outer function for finding optimal geometry of rectangular reinforced concrete cross-section
def opt_rc_rec(m, to_opt="GWP", criterion="ULS", max_iter=100):
    # definition of initial values for variables, which are going to be optimized
    h0 = m.section.h  # start value for height corresponds to 1/20 of system length
    di_xu0 = m.section.bw[0][0]  # start value for rebar diameter 40 mm
    var0 = [h0, di_xu0]

    # define bounds of variables
    bnds = [(0.06, 1.0), (0.006, 0.04)]  # height between 10 cm and 2.0 m, diameter of rebars between 6 mm and 40 mm

    # definition of fixed values of cross-section
    b = m.section.b
    s_xu, di_xo, s_xo = m.section.bw[0][1], m.section.bw[1][0], m.section.bw[1][1]
    co, st = m.section.concrete_type, m.section.rebar_type
    add_arg = [m.system, co, st, b, s_xu, di_xo, s_xo, m.floorstruc, m.requirements, to_opt, criterion, m.gk, m.qk]
    # # optimize with direct algorithm (weakness: not perfect optimization):
    # opt = direct(rc_rqs_co2, bnds, args=(add_arg,), eps=0.0005, maxfun=None)
    # optimize with basinghopping algorithm (weakness: bounds are not jet implementet in outer level,
    # what can lead to warnings):
    opt = basinhopping(rc_rqs, var0, niter=max_iter, T=1, minimizer_kwargs={"args": (add_arg,), "bounds": bnds,
                                                                            "method": "Powell"})
    h, di_xu = opt.x
    optimized_section = struct_analysis.RectangularConcrete(co, st, b, h, di_xu, s_xu, di_xo, s_xo)
    return optimized_section

# inner function for optimizing reinforced concrete section for criteria ULS or SLS1 in terms of GWP or height
def rc_rqs(var, add_arg):
    # input: variables, which have to be optimized, additional info about cross-section and system, optimizing option
    # output: if criterion == GWP -> co2 of cross-section, punished by delta 10*(qk_zul-qk)
    # output: if criterion == h -> height of cross-section, punished by delta 1*(qk_zul-qk)
    h, di_xu = var
    system = add_arg[0]
    concrete = add_arg[1]
    reinfsteel = add_arg[2]
    b = add_arg[3]
    s_xu, di_xo, s_xo = add_arg[4:7]
    floorstruc = add_arg[7]
    criteria = add_arg[8]
    to_opt = add_arg[9]
    criterion = add_arg[10]
    gk = add_arg[11]
    qk = add_arg[12]

    # create section
    section = struct_analysis.RectangularConcrete(concrete, reinfsteel, b, h, di_xu, s_xu, di_xo, s_xo)

    # create member
    member = struct_analysis.Member1D(section, system, floorstruc, criteria, gk, qk)
    if criterion == "ULS":  # optimize ultimate limit state
        # calculate admissible live load on member
        member.calc_qk_zul_gzt()  # calculate admissible live load
        # return co2 rsp. h of cross-section with penalty if q_adm =! q_k
        penalty = member.qk - member.qk_zul_gzt
        print(penalty)
        if to_opt == "GWP":
            return member.section.co2*(1+0.01*abs(penalty)) + abs(penalty)
        elif to_opt == "h":
            return h + 1e-4*abs(penalty)

    elif criterion == "SLS1":  # optimize service limit state (deflections)
        d1, d2, d3 = [member.w_install_adm - member.w_install, member.w_use_adm - member.w_use,
                      member.w_app_adm - member.w_app]
        # return co2 rsp. h of cross-section with penalty if w_adm =! w
        penalty = min(d1, d2, d3)
        if to_opt == "GWP":
            return member.section.co2 + 1e4*abs(penalty)
        elif to_opt == "h":
            return h + 1e1*abs(penalty)


# outer function for finding optimal wooden rectangular cross-section
def opt_gzt_wd_rqs(member, criterion="ULS"):
    h_0 = member.section.h
    bnds = [(0.04, 1.0)]
    minimal_h_gzt = minimize(wd_rqs_h, h_0, args=[member, criterion], bounds=bnds, method='Powell')
    h_opt_gzt = minimal_h_gzt.x[0]
    section = struct_analysis.RectangularWood(member.section.wood_type, member.section.b, h_opt_gzt)
    return section

# inner function used for optimizing wooden section in terms of height (equals co2)
def wd_rqs_h(h, args):
    m, criterion = args
    querschnitt = struct_analysis.RectangularWood(m.section.wood_type, m.section.b, h, m.section.phi)
    member = struct_analysis.Member1D(querschnitt, m.system, m.floorstruc, m.requirements, m.g2k, m.qk)
    member.calc_qk_zul_gzt()
    if criterion == "ULS":
        to_minimize = abs(member.qk - member.qk_zul_gzt)
    elif criterion == "SLS1":
        d1, d2, d3 = [member.w_install_adm - member.w_install, member.w_use_adm - member.w_use,
                      member.w_app_adm - member.w_app]
        # return penalty if w_adm =! w
        penalty = min(d1, d2, d3)
        to_minimize = abs(penalty)
    else:
        to_minimize = 99
        print("criterion has to  be 'ULS' or 'SLS1'")
    return to_minimize


# function for returning optimal section for defined QS-type, system, requirements, loads, criterion and type of optimum
def get_optimized_section(member, criterion, to_opt):

    if member.section.section_type == "rc_rec":
        # available to_opt arguments: "GWP", h
        # available criterion arguments: "ULS", "SLS1"
        return opt_rc_rec(member, to_opt, criterion, 100)
    elif member.section.section_type == "wd_rec":
        return opt_gzt_wd_rqs(member, criterion=criterion)
    else:
        print("There is no optimization for the section type " + member.section.section_type + " available!")
        return member.section

