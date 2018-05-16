import sys
import sys
import os
from math import atan
from math import degrees

from python_brlcad_tcl.brlcad_tcl import *

class cylinder_example(BrlCadModel):
	def __init__(self, brl_db):
		super(cylinder_example, self).__init__(brl_db)
		v = (0, 0, 0)
		height_vector = (3, 3, 10)
		height_alt = (0, 0, 10)
		b = (0, 1, 0)
		major_axis = (10, 0, 0)
		minor_axis = (0, 3, 0)
		half_width = 1
		apex_to_asymptote = 3

		def draw_cylinder_elliptical(name, v, height, major_axis, minor_axis):
			brl_db.cylinder_elliptical(name, v, height, major_axis, minor_axis)

		def draw_cylinder_hyperbolic(name, v, height, bvector, half_width, apex_to_asymptote):
			brl_db.cylinder_hyperbolic(name, v, height, bvector, half_width, apex_to_asymptote)

		def draw_cylinder_parabolic(name, v, height, bvector, half_width):
			brl_db.cylinder_parabolic(name, v, height, bvector, half_width)

		draw_cylinder_elliptical("rec_cylinder", v, height_vector, major_axis, minor_axis)
		draw_cylinder_hyperbolic("rhc_cylinder", v, height_alt, b, half_width, apex_to_asymptote)
		draw_cylinder_parabolic("rpc_cylinder", v, height_alt, b, half_width )

def main(argv):
	with brlcad_tcl(argv[1], "My Database") as brl_db:
		new_cylinder_example = cylinder_example(brl_db)
		# All units in the database file are stored in millimeters. This constrains
		# the arguments to the mk_* routines to also be in millimeters.
	# process the tcl script into a g database by calling mged
	brl_db.save_g()
	# process the g database into an STL file with a list of regions
	brl_db.save_stl(['new_cylinder_example'])

if __name__ == "__main__":
	main(sys.argv)