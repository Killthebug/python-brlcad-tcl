import sys
import sys
import os
from math import atan
from math import degrees

from python_brlcad_tcl.brlcad_tcl import *

class cone_example(BrlCadModel):
	def __init__(self, brl_db):
		super(cone_example, self).__init__(brl_db)
		v = (0, 0, 0)
		a = (0, 0, 10)
		b = (5, 0 , 0)
		c = (0, 3, 0)
		height_vector = (0, 0, 10)
		ratio = 0.6
		base_radius = 1
		top_radius = 5
		cscalar = 2
		dscalar = 9

		def draw_cone_elleptical(name, v, a, b, c, ratio):
			brl_db.cone_elliptical("cone_elliptical", v, a, b, c, ratio)

		def draw_cone_trc(name, v, a, base_radius, top_radius):
			brl_db.cone(name, v, a, base_radius, top_radius)

		def draw_cone_general(name, v, height_vector, a, b, cscalar, dscalar):
			brl_db.cone_general(name, v, height_vector, b, c, cscalar, dscalar)

		draw_cone_elleptical("tec_cone", v, a, b, c, ratio)
		draw_cone_trc("trc_cone", v, a, base_radius, top_radius)
		draw_cone_general("gen_cone", v, height_vector, a, b, cscalar, dscalar)

def main(argv):
	with brlcad_tcl(argv[1], "My Database") as brl_db:
		new_cone_example = cone_example(brl_db)
		# All units in the database file are stored in millimeters. This constrains
		# the arguments to the mk_* routines to also be in millimeters.
	# process the tcl script into a g database by calling mged
	brl_db.save_g()
	# process the g database into an STL file with a list of regions
	brl_db.save_stl(['new_cone_example'])

if __name__ == "__main__":
	main(sys.argv)