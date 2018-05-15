import sys
import sys
import os
from math import atan
from math import degrees

from python_brlcad_tcl.brlcad_tcl import *

class cone_elliptical_example(BrlCadModel):
	def __init__(self, brl_db):
		super(cone_elliptical_example, self).__init__(brl_db)
		v = (0, 0, 0)
		a = (0, 0, 10)
		b = (5, 0 , 0)
		c = (0, 3, 0)
		ratio = 0.6
		brl_db.cone_elliptical("cone_elliptical", v, a, b, c, ratio)

def main(argv):
	with brlcad_tcl(argv[1], "My Database") as brl_db:
		new_cone_elliptical = cone_elliptical_example(brl_db)
		# All units in the database file are stored in millimeters. This constrains
		# the arguments to the mk_* routines to also be in millimeters.
	# process the tcl script into a g database by calling mged
	brl_db.save_g()
	# process the g database into an STL file with a list of regions
	brl_db.save_stl(['new_cone_elliptical'])

if __name__ == "__main__":
	main(sys.argv)