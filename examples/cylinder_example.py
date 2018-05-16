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
		major_axis = (10, 0, 0)
		minor_axis = (0, 3, 0)
		ratio = 0.6
		base_radius = 1
		top_radius = 5
		cscalar = 2
		dscalar = 9

		def draw_cylinder_elliptical(name, v, height, major_axis, minor_axis):
			brl_db.cylinder_elliptical(name, v, height, major_axis, minor_axis)

		draw_cylinder_elliptical("rec_cylinder", v, height_vector, major_axis, minor_axis)

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