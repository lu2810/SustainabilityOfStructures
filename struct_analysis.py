# File enthält Code für die Strukturanalyse (Bauteil- und Querschnittsanalyse)

# Abgebildete Materialien:
# - Beton
# - Betonstahl
# - Holz
#
# Abgebildete Querschnitte 1D:
# - Betonrechteck-QS
# - Holzrechteck-QS
#
# Abgebildete Statische Systeme 1D:
# - Einfacher Balken
#
# Weitere Klassen:
# - Bauteil 1D
# - Bodenaufbauschicht
# - Bodenaufbau
# - Rechteckquerschnitte

import sqlite3  # import modul for SQLite
import numpy as np

class Wood:
    def __init__(self, mech_prop, database):  # retrieve basic mechanical data from database
        self.fmd = None
        self.mech_prop = mech_prop
        connection = sqlite3.connect(database)
        cursor = connection.cursor()
        # get mechanical properties from database
        inquiry = ("SELECT strength_bend, strength_shea, E_modulus, density_load FROM material_prop WHERE"
                   " name="+mech_prop)
        cursor.execute(inquiry)
        result = cursor.fetchall()
        self.fmk, self.fvd, self.Emmean, self.weight = result[0]
        # get GWP properties from database
        inquiry = "SELECT density, GWP, cost FROM products WHERE mech_prop="+mech_prop
        cursor.execute(inquiry)
        result = cursor.fetchall()
        self.density, self.GWP, self.cost = result[0]

    def get_design_values(self, gamma_m=1.7, eta_m=1, eta_t=1, eta_w=1):  # calculate design values
        if self.mech_prop[1:3] == "GL":
            gamma_m = 1.5  # SIA 265, 2.2.5: reduzierter Sicherheitsbeiwert für BSH

        self.fmd = self.fmk * eta_m * eta_t * eta_w / gamma_m  # SIA 265, 2.2.2, Formel (3)


class ReadyMixedConcrete:
    def __init__(self, mech_prop, database):  # retrieve basic mechanical data from database (self, table,
        self.ec2d = None
        self.tcd = None
        self.fcd = None
        self.mech_prop = mech_prop
        connection = sqlite3.connect(database)
        cursor = connection.cursor()
        # get mechanical properties from database
        inquiry = ("SELECT strength_comp, strength_tens, E_modulus, density_load FROM material_prop WHERE name="
                   +mech_prop)
        cursor.execute(inquiry)
        result = cursor.fetchall()
        self.fck, self.fctm, self.Ecm, self.weight = result[0]
        # get GWP properties from database
        inquiry = "SELECT density, GWP, cost, cost2 FROM products WHERE mech_prop="+mech_prop
        cursor.execute(inquiry)
        result = cursor.fetchall()
        self.density, self.GWP, self.cost, self.cost2 = result[0]

    def get_design_values(self, gamma_c=1.5, eta_t=1):  # calculate design values
        eta_fc = min((30/self.fck) ** (1/3), 1)  # SIA 262, 4.2.1.2, Formel (26)
        self.fcd = self.fck * eta_fc * eta_t / gamma_c  # SIA 262, 2.3.2.3, Formel (2)
        self.tcd = 0.3 * eta_t * self.fck ** 0.5/gamma_c  # SIA 262, 2.3.2.4, Formel (3)
        self.ec2d = 0.003  # SIA 262, 4.2.4, Tabelle 8


class SteelReinforcingBar:
    def __init__(self, mech_prop, database):
        # retrieve basic mechanical data from database (self, table, database name)
        self.fsd = None
        self.mech_prop = mech_prop
        connection = sqlite3.connect(database)
        cursor = connection.cursor()
        # get mechanical properties from database
        inquiry = "SELECT strength_tens, E_modulus FROM material_prop WHERE name="+mech_prop
        cursor.execute(inquiry)
        result = cursor.fetchall()
        self.fsk, self.Es = result[0]
        # get GWP properties from database
        inquiry = "SELECT density, GWP, cost FROM products WHERE mech_prop="+mech_prop
        cursor.execute(inquiry)
        result = cursor.fetchall()
        self.density, self.GWP, self.cost = result[0]

    def get_design_values(self, gamma_s=1.15):  # calculate design values
        self.fsd = self.fsk/gamma_s  # SIA 262, 2.3.2.5, Formel (4)


class SupStrucRectangular:
    # defines cross section dimensions and has methods to calculate static properties of rectangular,
    # non-cracked sections
    def __init__(self, b, h, phi=0):  # create a rectangular timber object
        self.b = b  # width [m]
        self.h = h  # height [m]
        self.a_brutt = self.calc_area()
        self.iy = self.calc_moment_of_inertia()
        self.phi = phi

    def calc_area(self):
        #  in:
        #  out: area [m^2]
        a_brutt = self.b * self.h
        return a_brutt

    def calc_moment_of_inertia(self):
        #  in:
        #  out: Iy [m^4]
        iy = self.b * self.h ** 3 / 12
        return iy

    def calc_strength_elast(self, fy, ty):
        #  in: yielding strength fy [MPa], shear strength ty [MPa]
        #  out: elastic bending resistance [kNm], elastic shear resistance [kN]
        mu_el = self.iy * fy * 2 / self.h * 1e3
        vu_el = self.b * self.h * ty / 1.5 * 1e3
        return mu_el, vu_el

    def calc_strength_plast(self, fy, ty):
        #  in: yielding strength fy [MPa], shear strength ty [MPa]
        #  out: plastic bending resistance [kNm], plastic shear resistance [kN]
        mu_pl = self.b * self.h ** 2 * fy / 4 * 1e3
        vu_pl = self.b * self.h * ty * 1e3
        return mu_pl, vu_pl

    def calc_weight(self, spec_weight):
        #  in: specific weight [kN/m^3]
        #  out: weight of cross section per m length [kN/m]
        w = spec_weight * self.a_brutt
        return w


class RectangularWood(SupStrucRectangular):
    def __init__(self, wood_type, b, h, phi=0.6):  # create a rectangular timber object
        super().__init__(b, h, phi)
        self.wood_type = wood_type
        self.mu, self.vu = self.calc_strength_elast(wood_type.fmd, wood_type.fvd)
        self.qs_class_n, self.qs_class_p = [3, 3]
        self.g0k = self.calc_weight(wood_type.weight)
        self.mu_max = self.mu
        self.mu_min = self.mu
        self.co2 = self.a_brutt * self.wood_type.GWP * self.wood_type.density * 1e-3
        self.cost = self.a_brutt * self.wood_type.cost
        self.ei1 = self.wood_type.Emmean*self.iy*1000  # elastic stiffness concrete (uncracked behaviour) [kNm^2]

class RectangularConcrete(SupStrucRectangular):
    def __init__(self, concrete_type, rebar_type, b, h, di_xu, s_xu, di_xo, s_xo, phi=2.0, c_nom=0.03):  # create a rectangular timber object
        super().__init__(b, h, phi)
        self.concrete_type = concrete_type
        self.rebar_type = rebar_type
        self.c_nom = c_nom
        self.bw = [[di_xu, s_xu],[di_xo, s_xo]]
        [self.d, self.ds] = self.calc_d()
        [self.mu_max, self.x_p, self.as_p, self.qs_class_p] = self.calc_mu('pos')
        [self.mu_min, self.x_n, self.as_n, self.qs_class_n] = self.calc_mu('neg')
        # self.vu = self.calc_strength_elast(wood_type.fmd, wood_type.fvd)
        self.g0k = self.calc_weight(concrete_type.weight)
        a_s_tot = self.as_p + self.as_n
        co2_rebar = a_s_tot * self.rebar_type.GWP * self.rebar_type.density * 1e-3
        co2_concrete = (self.a_brutt-a_s_tot) * self.concrete_type.GWP * self.concrete_type.density * 1e-3
        self.co2 = co2_rebar + co2_concrete
        self.cost = a_s_tot * self.rebar_type.cost + (self.a_brutt-a_s_tot) * self.concrete_type.cost + self.concrete_type.cost2
        self.ei1 = self.concrete_type.Ecm*self.iy*1000 # elastic stiffness concrete (uncracked behaviour) [kNm^2]
    #   self.ei2 = # to be defined

    def calc_d(self):
        d = self.h - self.c_nom - self.bw[0][0]/2
        ds = self.h - self.c_nom - self.bw[1][0]/2
        return d, ds

    def calc_mu(self, sign='pos'):
        b = self.b
        fsd = self.rebar_type.fsd
        fcd = self.concrete_type.fcd
        if sign == 'pos':
            [mu, x, a_s, qs_klasse] = self.mu_unsigned(self.bw[0][0], self.bw[0][1], self.d, b, fsd, fcd)
        elif sign == 'neg':
            [mu, x, a_s, qs_klasse] = self.mu_unsigned(self.bw[1][0], self.bw[1][1], self.ds, b, fsd, fcd)
        else:
            print ("sigen of moment resistance must be 'neg' or 'pos'")
        return mu, x, a_s, qs_klasse

    def mu_unsigned(self, di, s, d, b, fsd, fcd):
        # units input: [m, m, m, m, N/mm^2, N/mm^2]
        a_s = np.pi * di ** 2 / (4 * s) * b  # [m^2]
        omega = a_s * fsd / (d * b * fcd)  # [-]
        mu = a_s * fsd * d * (1-omega/2)*1e3  # [kNm]
        x = omega * d / 0.85  # [m]
        if x/d <= 0.35:
            return mu, x, a_s, 1
        if x/d<=0.5:
            return mu, x, a_s, 2
        else:
            return 0, x, a_s, 99 #Querschnitt hat ungenügendes Verformungsvermögen


class MatLayer:  # create a material layer
    def __init__(self, mat_name, h_input, roh_input, database):  # get initial data from database
        self.name = mat_name
        connection = sqlite3.connect(database)
        cursor = connection.cursor()
        # get properties from database
        inquiry = "SELECT h_fix, density, weight, GWP FROM floor_struc_prop WHERE name=" + mat_name
        cursor.execute(inquiry)
        result = cursor.fetchall()
        h_fix, density, weight, self.GWP = result[0]
        if h_input is False:
            self.h = h_fix
        else:
            self.h = h_input
        if roh_input is False:
            self.density = density
            self.weight = weight
        else:
            self.density = roh_input
            self.weight = roh_input/100
        self.gk = self.weight * self.h  # weight per area in kN/m^2
        self.co2 = self.density * self.h * self. GWP/1000 # CO2-eq per area in kg-C02/m^2


class FloorStruc:  # create a floor structure
    def __init__(self, mat_layers, database_name):
        self.layers = []
        self.co2 = 0
        self.gk_area = 0
        self.h = 0
        for mat_name, h_input, roh_input in mat_layers:
            current_layer = MatLayer(mat_name, h_input, roh_input, database_name)
            self.layers.append(current_layer)
            self.co2 += current_layer.co2
            self.gk_area += current_layer.gk
            self.h += current_layer.h


class BeamSimpleSup:
    def __init__(self, length):
        self.l_tot = length
        self.li_max = self.l_tot # max span (used for calculation of admissible deflections)
        self.alpha_m = [0, 1/8]
        self.qs_cl_erf = [99, 99] # Querschnittsklasse: 1 == plast, 99 == keine Anforderung (elast)
        self.alpha_w = 5/384

class Member1D:
    def __init__(self, section, floorstruc, system, g2k=0.0, qk=2.0, psi0=0.7, psi1=0.5, psi2=0.3,
                 install="ductile", lw_install=350, lw_use=350, lw_app=300):
        self.section = section
        self.floorstruc = floorstruc
        self.system = system
        self.g0k = self.section.g0k
        self.g1k = self.floorstruc.gk_area
        self.g2k = g2k
        self.qk = qk
        self.psi = [psi0, psi1, psi2]
        self.gk = self.g0k + self.g1k + self.g2k
        self.mu_max = section.mu_max
        self.mu_min = section.mu_min
        self.qk_zul_gzt = []
        self.q_rare = self.gk + self.qk
        self.q_freq = self.gk + self.psi[1]*self.qk
        self.q_per = self.gk + self.psi[2]*self.qk
        self.w_install_adm = self.system.li_max/lw_install
        self.w_use_adm = self.system.li_max / lw_use
        self.w_app_adm = self.system.li_max / lw_app
        # calculation of deflections (uncracked cross-section, method for cracked cross-section is not implemented jet.
        if install == "ductile":
            self.w_install = self.system.alpha_w * (
                        self.q_freq + self.q_per * (self.section.phi - 1)) * self.system.l_tot ** 4 / self.section.ei1
        elif install == "brittle":
            self.w_install = self.system.alpha_w * (
                    self.q_rare + self.q_per * (self.section.phi - 1)) * self.system.l_tot ** 4 / self.section.ei1
        self.w_use = self.system.alpha_w * (
                    self.q_freq - self.gk) * self.system.l_tot ** 4 / self.section.ei1
        self.w_app = self.system.alpha_w * (
                self.q_per * (1 + self.section.phi)) * self.system.l_tot ** 4 / self.section.ei1
        self.co2 = system.l_tot * (floorstruc.co2 + section.co2)

    def calc_qu(self):
        # calculates maximal load qu in respect to bearing moment mu_max, mu_min and static system
        alpha_m = self.system.alpha_m
        qs_class_erf = self.system.qs_cl_erf # z.B. [0, 2]
        qs_class_vorh = [self.section.qs_class_n, self.section.qs_class_p]

        if min(alpha_m) == 0:
            if qs_class_vorh[1] <= qs_class_erf[1]:
                self.qu = self.mu_max/(max(alpha_m)*self.system.l_tot ** 2)
            else:
                self.qu = 0
        else:
            if qs_class_vorh[0] <= qs_class_erf[0] & qs_class_vorh[1] <= qs_class_erf[1]:
                self.qu = min(self.mu_max/(max(alpha_m)*self.system.l_tot ** 2),
                          self.mu_min/(min(alpha_m)*self.system.l_tot ** 2))
            else:
                self.qu = 0

    def calc_qk_zul_gzt(self, gamma_g=1.35, gamma_q=1.5):
        self.qk_zul_gzt = (self.qu - gamma_g * self.gk)/gamma_q

