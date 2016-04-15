########################################################################
#
# Free-fall example script
#
#
# Copyright (c) 2013-2016, Grackle Development Team.
#
# Distributed under the terms of the Enzo Public Licence.
#
# The full license is in the file LICENSE, distributed with this
# software.
########################################################################

from matplotlib import pyplot
import numpy as np
import sys
import yt

from pygrackle.grackle_wrapper import *
from pygrackle.fluid_container import FluidContainer

from utilities.api import \
     get_temperature_units, \
     evolve_constant_density, \
     evolve_freefall

from utilities.physical_constants import \
     boltzmann_constant_cgs, \
     mass_hydrogen_cgs, \
     mass_electron_cgs, \
     sec_per_Myr, \
     cm_per_mpc

tiny_number = 1e-60

if __name__=="__main__":
    current_redshift = 0.

    # Set solver parameters
    my_chemistry = chemistry_data()
    my_chemistry.use_grackle = 1
    my_chemistry.with_radiative_cooling = 1
    my_chemistry.primordial_chemistry = 3
    my_chemistry.metal_cooling = 0
    my_chemistry.UVbackground = 0
    my_chemistry.Gamma = 5. / 3.
    my_chemistry.CaseBRecombination = 0

    # Set units
    my_chemistry.comoving_coordinates = 0 # proper units
    my_chemistry.a_units = 1.0
    a_value = 1. / (1. + current_redshift) / my_chemistry.a_units
    my_chemistry.density_units  = mass_hydrogen_cgs # rho = 1.0 is 1.67e-24 g
    my_chemistry.length_units   = cm_per_mpc         # 1 Mpc in cm
    my_chemistry.time_units     = sec_per_Myr          # 1 Myr in s
    my_chemistry.velocity_units = my_chemistry.a_units * \
      (my_chemistry.length_units / a_value) / my_chemistry.time_units;
    temperature_units = get_temperature_units(my_chemistry)

    # set initial density and temperature
    initial_temperature = 50000. # start the gas at this temperature
    # then begin collapse
    initial_density     = 1.0e-1 * mass_hydrogen_cgs # g / cm^3
    # stopping condition
    final_density       = 1.e12 * mass_hydrogen_cgs

    rval = my_chemistry.initialize(a_value)
    if not rval:
        print "Error initializing chemistry."
        sys.exit(0)

    fc = FluidContainer(my_chemistry, 1)
    fc["density"][:] = initial_density / my_chemistry.density_units
    fc["HI"][:] = 0.76 * fc["density"]
    fc["HII"][:] = tiny_number * 0.76 * fc["density"]
    fc["HeI"][:] = (1.0 - 0.76) * fc["density"]
    fc["HeII"][:] = tiny_number * fc["density"]
    fc["HeIII"][:] = tiny_number * fc["density"]
    fc["de"][:] = 2e-4 * mass_electron_cgs / mass_hydrogen_cgs * fc["density"]
    if my_chemistry.primordial_chemistry > 1:
        fc["H2I"][:] = tiny_number * fc["density"]
        fc["H2II"][:] = tiny_number * fc["density"]
        fc["HM"][:] = tiny_number * fc["density"]
    if my_chemistry.primordial_chemistry > 2:
        fc["DI"][:] = 2.0 * 3.4e-5 * fc["density"]
        fc["DII"][:] = tiny_number * fc["density"]
        fc["HDI"][:] = tiny_number * fc["density"]
    if my_chemistry.metal_cooling == 1:
        fc["metal"][:] = 0.0 * fc["density"]
    fc["energy"][:] = initial_temperature / temperature_units
    fc["x-velocity"][:] = 0.0
    fc["y-velocity"][:] = 0.0
    fc["z-velocity"][:] = 0.0

    # timestepping safety factor
    safety_factor = 0.01

    # let the gas cool at constant density from the starting temperature
    # down to a lower temperature to get the species fractions in a
    # reasonable state.
    cooling_temperature = 100.
    data0 = evolve_constant_density(fc, cooling_temperature,
                                    safety_factor=safety_factor)

    # evolve density and temperature according to free-fall collapse
    data = evolve_freefall(fc, final_density,
                           safety_factor=safety_factor)

    # save data arrays as a yt dataset
    yt.save_as_dataset({}, "freefall.h5", data)

    # make a plot of rho/f_H2 vs. T
    p1, = pyplot.loglog(data["density"], data["temperature"], color="black")
    pyplot.xlabel("$\\rho$ [g/cm$^{3}$]")
    pyplot.ylabel("T [K]")

    pyplot.twinx()
    p2, = pyplot.loglog(data["density"], data["H2I"] / data["density"], color="red")
    pyplot.ylabel("H$_{2}$ fraction")

    pyplot.legend([p1, p2], ["T", "f$_{H2}$"], loc="upper left")
    pyplot.savefig("freefall.pdf")
