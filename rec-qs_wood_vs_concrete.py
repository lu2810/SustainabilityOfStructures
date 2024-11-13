# file contains code for generating plots for "Austausch Nr. 1 mit erweitertem Projektteam"
# parts of the code will to be integrated in a file, which contains general code for automated plot generation

import create_dummy_database  # file for creating a "dummy database", as long as no real database is available
import struct_analysis  # file with code for structural analysis
from scipy.optimize import direct
from scipy.optimize import basinhopping
from scipy.optimize import minimize  # importiere Minimierungsfunktion aus dem SyiPy paket
import matplotlib.pyplot as plt

# max. number of iterations per optimization. Fast results: max_iterations = 100, good results: max iterations = 1000
max_iterations = 100

# create dummy-database
database_name = "dummy_sustainability.db"  # define database name
create_dummy_database.create_database(database_name)  # create database

# create material for wooden cross-section, derive corresponding design values
timber1 = struct_analysis.Wood("'GL24h'", database_name)  # create a Wood material object
timber1.get_design_values()

# create floor structure for solid wooden cross-section
bodenaufbau_brettstappeldecke = [["'Parkett 2-Schicht werkversiegelt, 11 mm'", False, False], ["'Unterlagsboden Zement, 85 mm'", False, False],
                ["'Glaswolle'", 0.03, False], ["'Kies gebrochen'", 0.12, False]]
bodenaufbau_bs = struct_analysis.FloorStruc(bodenaufbau_brettstappeldecke, database_name)

# create materials for reinforced concrete cross-section, derive corresponding design values
concrete1 = struct_analysis.ReadyMixedConcrete("'C25/30'", database_name)
concrete1.get_design_values()
reinfsteel1 = struct_analysis.SteelReinforcingBar("'B500B'", database_name)
reinfsteel1.get_design_values()

# create floor structure for solid reinforced concrete cross-section
bodenaufbau_rcdecke = [["'Parkett 2-Schicht werkversiegelt, 11 mm'", False, False], ["'Unterlagsboden Zement, 85 mm'", False, False],
                ["'Glaswolle'", 0.03, False]]
bodenaufbau_rc = struct_analysis.FloorStruc(bodenaufbau_rcdecke, database_name)

# function for optimizing reinforced concrete section in terms of GWP or height
def rc_rqs(var, add_arg):
    # input: variables, which have to be optimized, additional info about cross-section and system, optimizing option
    # output: if criterion == GWP -> co2 of cross-section, punished by delta 10*(qk_zul-qk)
    # output: if criterion == h -> height of cross-section, punished by delta 1*(qk_zul-qk)
    h, di_xu = var
    system = add_arg[0]
    concrete = add_arg[1]
    reinfsteel = add_arg[2]
    b = add_arg[3]
    s_xu, di_xo, s_xo  = add_arg[4:7]
    fooorstruc = add_arg[7]
    to_opt = add_arg[8]
    criterion = add_arg[9]

    # create section
    section = struct_analysis.RectangularConcrete(concrete, reinfsteel, b, h, di_xu, s_xu, di_xo, s_xo)

    # create member
    member = struct_analysis.Member1D(section, fooorstruc, system, 0.75, 2.0)
    if criterion == "ULS": # optimize ultimate limit state
        # calculate admissible live load on member
        member.calc_qu()  # calculate ultimate resistance
        member.calc_qk_zul_gzt()  # calculate admissible live load with g2k = 0.75
        # return co2 rsp. h of cross-section with penalty if q_adm =! q_k
        penalty = member.qk_zul_gzt - member.qk
        if to_opt == "GWP":
            return member.co2*(1+10*abs(penalty))
        elif to_opt == "h":
            return h * (1+1*abs(penalty))

    elif criterion == "SLS1": # optimize service limit state (deflections)
        d1, d2, d3 = [member.w_install_adm - member.w_install, member.w_use_adm - member.w_use,
                      member.w_app_adm - member.w_app]
        # return co2 rsp. h of cross-section with penalty if w_adm =! w
        penalty = min(d1, d2, d3)
        if to_opt == "GWP":
            return member.co2*(1+100*abs(penalty))
        elif to_opt == "h":
            return h * (1+10*abs(penalty))

# function for finding optimal geometry (criterion GZT) of rectangular reinforced concrete cross-section
def opt_gzt_rc_rqs(system, to_opt="GWP", criterion="ULS"):
    # definition of initial values for variables, which are going to be optimized
    h0 = system.l_tot/20  # start value for height corresponds to 1/20 of system length
    di_xu0 = 0.01  # start value for rebar diameter 40 mm
    var0 = [h0, di_xu0]

    # define bounds of variables
    bnds = [(0.08, 1.0), (0.006, 0.04)]  # height between 10 cm and 2.0 m, diameter of rebars between 6 mm and 40 mm

    # definition of fixed values of crosssection
    b = 1.0  # width of crosssection 1 m
    s_xu, di_xo, s_xo = 0.15, 0.01, 0.15  # spacing of rebars 0.15 m, diameter of top rebars 10 mm
    add_arg = [system, concrete1, reinfsteel1, b, s_xu, di_xo, s_xo, bodenaufbau_rc, to_opt, criterion]
    # # optimize with direct algorithm (weakness: not perfect optimization):
    # opt = direct(rc_rqs_co2, bnds, args=(add_arg,), eps=0.0005, maxfun=None)
    # optimize with basinghopping algorithm (weakness: bounds are not jet implementet in outer level, what can lead to warnings.):
    opt = basinhopping(rc_rqs, var0, niter=max_iterations, T=1, minimizer_kwargs={"args": (add_arg,), "bounds": bnds, "method": "Powell"})
    h, di_xu = opt.x
    optimized_section = struct_analysis.RectangularConcrete(concrete1, reinfsteel1, b, h, di_xu, s_xu, di_xo, s_xo)
    return optimized_section


# function used for optimizing wooden section in terms of height (equals co2)
def wd_rqs_h(h, args):
    querschnitt = struct_analysis.RectangularWood(timber1, 1, h)
    system, criterion = args
    member = struct_analysis.Member1D(querschnitt, bodenaufbau_bs, system, 0.75, 2.0)
    member.calc_qu()
    member.calc_qk_zul_gzt()
    if criterion == "ULS":
        to_minimize = abs(member.qk - member.qk_zul_gzt)
    elif criterion == "SLS1":
        d1, d2, d3 = [member.w_install_adm - member.w_install, member.w_use_adm - member.w_use,
                      member.w_app_adm - member.w_app]
        # return penalty if w_adm =! w
        penalty = min(d1, d2, d3)
        to_minimize = abs(penalty)
    return to_minimize

# function for finding optimal (criterion GZT) wooden rectangular cross-section
def opt_gzt_wd_rqs(system, criterion="ULS"):
    h_0 = 0.02
    bnds = [(0.01, 2.0)]
    minimal_h_gzt = minimize(wd_rqs_h, h_0, args=[system, criterion], bounds=bnds, method='Powell')
    h_opt_gzt = minimal_h_gzt.x[0]
    section = struct_analysis.RectangularWood(timber1, 1, h_opt_gzt)
    return section

# define system lengths for plot
l = [4, 5, 6, 7, 8, 9, 10, 12, 14, 16]

# create rectangular wood sections in function of length with optimized height
section_list_wd_h_uls = []
section_list_wd_h_sls1 = []
section_list_rc_co2_uls = []
section_list_rc_co2_sls1 = []
section_list_rc_h_uls = []
for i in l:
    system = struct_analysis.BeamSimpleSup(i)
    section_wd_h_uls = opt_gzt_wd_rqs(system, "ULS")
    section_list_wd_h_uls.append(section_wd_h_uls)
    section_wd_h_sls1 = opt_gzt_wd_rqs(system, "SLS1")
    section_list_wd_h_sls1.append(section_wd_h_sls1)
    section_rc_co2_uls = opt_gzt_rc_rqs(system,"GWP", "ULS")
    section_list_rc_co2_uls.append(section_rc_co2_uls)
    section_rc_co2_sls1 = opt_gzt_rc_rqs(system,"GWP", "SLS1")
    section_list_rc_co2_sls1.append(section_rc_co2_sls1)
    section_rc_h_uls = opt_gzt_rc_rqs(system, "h")
    section_list_rc_h_uls.append(section_rc_h_uls)

# create plot data: height of wooden sections, criterion ULS, optimized for minimal height(equals minimal GWP)
h_wd_h = []
htot_wd_h = []
co2_wd_h = []
co2tot_wd_h = []
cost_wd_h = []
for section in section_list_wd_h_uls:
    h_wd_h.append(section.h)
    htot_wd_h.append(section.h+bodenaufbau_bs.h)
    co2_wd_h.append(section.co2)
    co2tot_wd_h.append(section.co2+bodenaufbau_bs.co2)
    cost_wd_h.append(section.cost)

# create plot data: height of wooden sections, criterion SLS, optimized for minimal height(equals minimal GWP)
h_wd_h_sls1 = []
htot_wd_h_sls1 = []
co2_wd_h_sls1 = []
co2tot_wd_h_sls1 = []
cost_wd_h_sls1 = []
for section in section_list_wd_h_sls1:
    h_wd_h_sls1.append(section.h)
    htot_wd_h_sls1.append(section.h+bodenaufbau_bs.h)
    co2_wd_h_sls1.append(section.co2)
    co2tot_wd_h_sls1.append(section.co2+bodenaufbau_bs.co2)
    cost_wd_h_sls1.append(section.cost)

# create plot data: height of reinforced concrete sections, criterion ULS, optimized for minimal GWP
h_rc_co2 = []
htot_rc_co2 = []
co2_rc_co2 = []
co2tot_rc_co2 = []
cost_rc_co2 = []
for section in section_list_rc_co2_uls:
    h_rc_co2.append(section.h)
    htot_rc_co2.append(section.h+bodenaufbau_rc.h)
    co2_rc_co2.append(section.co2)
    co2tot_rc_co2.append(section.co2+bodenaufbau_rc.co2)
    cost_rc_co2.append(section.cost)

# create plot data: height of reinforced concrete sections, criterion ULS, optimized for minimal GWP
h_rc_co2_sls1 = []
htot_rc_co2_sls1 = []
co2_rc_co2_sls1 = []
co2tot_rc_co2_sls1 = []
cost_rc_co2_sls1 = []
for section in section_list_rc_co2_sls1:
    h_rc_co2_sls1.append(section.h)
    htot_rc_co2_sls1.append(section.h+bodenaufbau_rc.h)
    co2_rc_co2_sls1.append(section.co2)
    co2tot_rc_co2_sls1.append(section.co2+bodenaufbau_rc.co2)
    cost_rc_co2_sls1.append(section.cost)

# create plot data: height of reinforced concrete sections, criterion ULS, optimized for minimal height
h_rc_h = []
htot_rc_h = []
co2_rc_h = []
co2tot_rc_h = []
cost_rc_h = []
for section in section_list_rc_h_uls:
    h_rc_h.append(section.h)
    htot_rc_h.append(section.h+bodenaufbau_rc.h)
    co2_rc_h.append(section.co2)
    co2tot_rc_h.append(section.co2+bodenaufbau_rc.co2)
    cost_rc_h.append(section.cost)

plt.figure(1)
plt.subplot(321)
plt.plot(l, h_wd_h, 'b-', label = "h, rectangular wood, criterion ULS, optimized for minimal h and minimal GWP")
plt.plot(l, h_wd_h_sls1, 'b--', label = "h, rectangular wood, criterion SLS, optimized for minimal h and minimal GWP")
plt.plot(l, h_rc_h, 'c-', label = "h, rectangular reinforced concrete, criterion ULS, optimized for minimal h")
plt.plot(l, h_rc_co2, 'g-', label = "h, rectangular reinforced concrete, criterion ULS, optimized for minimal GWP")
plt.plot(l, h_rc_co2_sls1, 'g--', label = "h, rectangular reinforced concrete, criterion SLS, optimized for minimal GWP")
plt.xlabel('l [m]')
plt.ylabel('h [m]')
plt.title('Height of Load Bearing Structure of Optimized Cross-section')
plt.axis([4, 16, 0, 1.0])
plt.legend()

plt.subplot(322)
plt.plot(l, htot_wd_h, 'b-', label = "h_tot, rectangular wood, ULS, optimized for minimal h and minimal GWP")
plt.plot(l, htot_wd_h_sls1, 'b--', label = "h_tot, rectangular wood, SLS, optimized for minimal h and minimal GWP")
plt.plot(l, htot_rc_h, 'c-', label = "h_tot, rectangular reinforced concrete, ULS, optimized for minimal h")
plt.plot(l, htot_rc_co2, 'g-', label = "h_tot, rectangular reinforced concrete, ULS, optimized for minimal GWP")
plt.plot(l, htot_rc_co2_sls1, 'g--', label = "h_tot, rectangular reinforced concrete, SLS, optimized for minimal GWP")
plt.xlabel('l [m]')
plt.ylabel('h [m]')
plt.title('Height of Floor System with Optimized Cross-section')
plt.axis([4, 16, 0, 1.0])
plt.legend()

plt.subplot(323)
plt.plot(l, co2_wd_h, 'b-', label = "rectangular wood, ULS, optimized for minimal h and minimal GWP")
plt.plot(l, co2_wd_h_sls1, 'b--', label = "rectangular wood, SLS, optimized for minimal h and minimal GWP")
plt.plot(l, co2_rc_h, 'c-', label = "rectangular reinforced concrete, ULS, optimized for minimal h")
plt.plot(l, co2_rc_co2, 'g-', label = "rectangular reinforced concrete, ULS, optimized for minimal GWP")
plt.plot(l, co2_rc_co2_sls1, 'g--', label = "rectangular reinforced concrete, SLS, optimized for minimal GWP")
plt.xlabel('l [m]')
plt.ylabel('GWP [kg-CO2-eq / m2]')
plt.title('Global Warming Potential of Load Bearing Structure with Optimized Cross-section')
plt.axis([4, 16, 0, 200])
plt.legend()

plt.subplot(324)
plt.plot(l, co2tot_wd_h, 'b-', label = "rectangular wood,  ULS, optimized for minimal h and minimal GWP")
plt.plot(l, co2tot_wd_h_sls1, 'b--', label = "rectangular wood, criterion SLS, optimized for minimal h and minimal GWP")
plt.plot(l, co2tot_rc_h, 'c-', label = "rectangular reinforced concrete, ULS, optimized for minimal h")
plt.plot(l, co2tot_rc_co2, 'g-', label = "rectangular reinforced concrete, ULS, optimized for minimal GWP")
plt.plot(l, co2tot_rc_co2_sls1, 'g--', label = "rectangular reinforced concrete, SLS, optimized for minimal GWP")
plt.xlabel('l [m]')
plt.ylabel('GWP [kg-CO2-eq / m2]')
plt.title('Global Warming Potential of Floor System with Optimized Cross-section')
plt.axis([4, 16, 0, 200])
plt.legend()


plt.subplot(325)
plt.plot(l, cost_wd_h, 'b-', label = "rectangular wood,  ULS, optimized for minimal h and minimal GWP")
plt.plot(l, cost_wd_h_sls1, 'b--', label = "rectangular wood, criterion SLS, optimized for minimal h and minimal GWP")
plt.plot(l, cost_rc_h, 'c-', label = "rectangular reinforced concrete, ULS, optimized for minimal h")
plt.plot(l, cost_rc_co2, 'g-', label = "rectangular reinforced concrete, ULS, optimized for minimal GWP")
plt.plot(l, cost_rc_co2_sls1, 'g--', label = "rectangular reinforced concrete, SLS, optimized for minimal GWP")
plt.xlabel('l [m]')
plt.ylabel('Cost [CHF / m2]')
plt.title('Cost of Floor System with Optimized Cross-section')
plt.axis([4, 16, 0, 800])
plt.legend()
plt.show()