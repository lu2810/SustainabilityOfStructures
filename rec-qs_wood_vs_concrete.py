# file contains code for generating plots for "Austausch Nr. 1 mit erweitertem Projektteam"
# parts of the code will to be integrated in a file, which contains general code for automated plot generation

import create_dummy_database  # file for creating a "dummy database", as long as no real database is available
import struct_analysis  # file with code for structural analysis
import struct_optimization  # file with code for structural optimization
import matplotlib.pyplot as plt

# max. number of iterations per optimization. Fast results: max_iterations = 50, good results: max iterations = 1000
max_iter = 1000

# create dummy-database
database_name = "dummy_sustainability.db"  # define database name
create_dummy_database.create_database(database_name)  # create database

# create material for wooden cross-section, derive corresponding design values
timber1 = struct_analysis.Wood("'GL24h'", database_name)  # create a Wood material object
timber1.get_design_values()
# create materials for reinforced concrete cross-section, derive corresponding design values
concrete1 = struct_analysis.ReadyMixedConcrete("'C25/30'", database_name)
concrete1.get_design_values()
reinfsteel1 = struct_analysis.SteelReinforcingBar("'B500B'", database_name)
reinfsteel1.get_design_values()

# create initial wooden rectangular cross-section
section_wd0 = struct_analysis.RectangularWood(timber1, 1.0, 0.1)
# create initial reinforced concrete rectangular cross-section
section_rc0 = struct_analysis.RectangularConcrete(concrete1, reinfsteel1, 1.0, 0.1, 0.012, 0.15, 0.01, 0.15)

# create floor structure for solid wooden cross-section
bodenaufbau_brettstappeldecke = [["'Parkett 2-Schicht werkversiegelt, 11 mm'", False, False],
                                 ["'Unterlagsboden Zement, 85 mm'", False, False], ["'Glaswolle'", 0.03, False],
                                 ["'Kies gebrochen'", 0.12, False]]
bodenaufbau_bs = struct_analysis.FloorStruc(bodenaufbau_brettstappeldecke, database_name)
# create floor structure for solid reinforced concrete cross-section
bodenaufbau_rcdecke = [["'Parkett 2-Schicht werkversiegelt, 11 mm'", False, False],
                       ["'Unterlagsboden Zement, 85 mm'", False, False],
                       ["'Glaswolle'", 0.03, False]]
bodenaufbau_rc = struct_analysis.FloorStruc(bodenaufbau_rcdecke, database_name)

# define loads on member
g2k = 0.75  # n.t. Einbauten
qk = 2.0  # Nutzlast

# define service limit state criteria
requirements = struct_analysis.Requirements()

# define system lengths for plot
lengths = [4, 5, 6, 7, 8, 9, 10, 12]

#define content of plot
to_plot = [["rc_rec", bodenaufbau_rc], ["wd_rec", bodenaufbau_bs ]]
sectionlist = []
#  XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# for i in to_plot:
#      sectionlist.append(get_optimized_sections(i,XXXXXX))
#  XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# create rectangular wood sections in function of length with optimized height
section_list_wd_h_uls = []
section_list_wd_h_sls1 = []
section_list_rc_co2_uls = []
section_list_rc_co2_sls1 = []
section_list_rc_h_uls = []
for i in lengths:
    system = struct_analysis.BeamSimpleSup(i)

    member_wd0 = struct_analysis.Member1D(section_wd0, system, bodenaufbau_bs, requirements, g2k, qk)
    section_wd_h_uls = struct_optimization.opt_gzt_wd_rqs(member_wd0, "ULS")
    section_list_wd_h_uls.append(section_wd_h_uls)
    section_wd_h_sls1 = struct_optimization.opt_gzt_wd_rqs(member_wd0, "SLS1")
    section_list_wd_h_sls1.append(section_wd_h_sls1)

    member_rc0 = struct_analysis.Member1D(section_rc0, system, bodenaufbau_rc, requirements, g2k, qk)
    section_rc_co2_uls = struct_optimization.opt_gzt_rc_rqs(member_rc0, "GWP", "ULS", max_iter)
    section_list_rc_co2_uls.append(section_rc_co2_uls)

    section_rc_co2_sls1 = struct_optimization.opt_gzt_rc_rqs(member_rc0, "GWP", "SLS1", max_iter)
    section_list_rc_co2_sls1.append(section_rc_co2_sls1)

    section_rc_h_uls = struct_optimization.opt_gzt_rc_rqs(member_rc0, "h", "ULS", max_iter)
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
plt.plot(lengths, h_wd_h, 'b-', label="h, rectangular wood, criterion ULS, optimized for minimal h and minimal GWP")
plt.plot(lengths, h_wd_h_sls1, 'b--', label="h, rectangular wood, criterion SLS, optimized for minimal h and "
                                           "minimal GWP")
plt.plot(lengths, h_rc_h, 'c-', label="h, rectangular reinforced concrete, criterion ULS, optimized for minimal h")
plt.plot(lengths, h_rc_co2, 'g-', label="h, rectangular reinforced concrete, criterion ULS, optimized for minimal "
                                       "GWP")
plt.plot(lengths, h_rc_co2_sls1, 'g--', label="h, rectangular reinforced concrete, criterion SLS, optimized for "
                                             "minimal GWP")
plt.xlabel('l [m]')
plt.ylabel('h [m]')
plt.title('Height of Load Bearing Structure of Optimized Cross-section')
plt.axis((4.0, 16.0, 0.0, 1.0))
plt.legend()

plt.subplot(322)
plt.plot(lengths, htot_wd_h, 'b-', label="h_tot, rectangular wood, ULS, optimized for minimal h and minimal GWP")
plt.plot(lengths, htot_wd_h_sls1, 'b--', label="h_tot, rectangular wood, SLS, optimized for minimal h and minimal "
                                              "GWP")
plt.plot(lengths, htot_rc_h, 'c-', label="h_tot, rectangular reinforced concrete, ULS, optimized for minimal h")
plt.plot(lengths, htot_rc_co2, 'g-', label="h_tot, rectangular reinforced concrete, ULS, optimized for minimal "
                                          "GWP")
plt.plot(lengths, htot_rc_co2_sls1, 'g--', label="h_tot, rectangular reinforced concrete, SLS, optimized for "
                                                "minimal GWP")
plt.xlabel('l [m]')
plt.ylabel('h [m]')
plt.title('Height of Floor System with Optimized Cross-section')
plt.axis((4, 16, 0, 1.0))
plt.legend()

plt.subplot(323)
plt.plot(lengths, co2_wd_h, 'b-', label="rectangular wood, ULS, optimized for minimal h and minimal GWP")
plt.plot(lengths, co2_wd_h_sls1, 'b--', label="rectangular wood, SLS, optimized for minimal h and minimal GWP")
plt.plot(lengths, co2_rc_h, 'c-', label="rectangular reinforced concrete, ULS, optimized for minimal h")
plt.plot(lengths, co2_rc_co2, 'g-', label="rectangular reinforced concrete, ULS, optimized for minimal GWP")
plt.plot(lengths, co2_rc_co2_sls1, 'g--', label="rectangular reinforced concrete, SLS, optimized for minimal GWP")
plt.xlabel('l [m]')
plt.ylabel('GWP [kg-CO2-eq / m2]')
plt.title('Global Warming Potential of Load Bearing Structure with Optimized Cross-section')
plt.axis((4, 16, 0, 200))
plt.legend()

plt.subplot(324)
plt.plot(lengths, co2tot_wd_h, 'b-', label="rectangular wood,  ULS, optimized for minimal h and minimal GWP")
plt.plot(lengths, co2tot_wd_h_sls1, 'b--', label="rectangular wood, criterion SLS, optimized for minimal h and "
                                                "minimal GWP")
plt.plot(lengths, co2tot_rc_h, 'c-', label="rectangular reinforced concrete, ULS, optimized for minimal h")
plt.plot(lengths, co2tot_rc_co2, 'g-', label="rectangular reinforced concrete, ULS, optimized for minimal GWP")
plt.plot(lengths, co2tot_rc_co2_sls1, 'g--', label="rectangular reinforced concrete, SLS, optimized for minimal GWP")
plt.xlabel('l [m]')
plt.ylabel('GWP [kg-CO2-eq / m2]')
plt.title('Global Warming Potential of Floor System with Optimized Cross-section')
plt.axis((4, 16, 0, 200))
plt.legend()


plt.subplot(325)
plt.plot(lengths, cost_wd_h, 'b-', label="rectangular wood,  ULS, optimized for minimal h and minimal GWP")
plt.plot(lengths, cost_wd_h_sls1, 'b--', label="rectangular wood, criterion SLS, optimized for minimal h and "
                                              "minimal GWP")
plt.plot(lengths, cost_rc_h, 'c-', label="rectangular reinforced concrete, ULS, optimized for minimal h")
plt.plot(lengths, cost_rc_co2, 'g-', label="rectangular reinforced concrete, ULS, optimized for minimal GWP")
plt.plot(lengths, cost_rc_co2_sls1, 'g--', label="rectangular reinforced concrete, SLS, optimized for minimal GWP")
plt.xlabel('l [m]')
plt.ylabel('Cost [CHF / m2]')
plt.title('Cost of Floor System with Optimized Cross-section')
plt.axis((4, 16, 0, 800))
plt.legend()
plt.show()
