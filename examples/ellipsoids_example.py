import sys
import sys
import os
from math import atan
from math import degrees

from python_brlcad_tcl.brlcad_tcl import *

class ellipsoid_example(BrlCadModel):
	def __init__(self, brl_db):
		super(ellipsoid_example, self).__init__(brl_db)
		v = (0, 0, 0)
		height_vector = (0, 10, 10)
		a = (10, 0, 0)
		bscalar = 10
		apex_to_asymptote = 3

		def draw_elliptical_hyperboloid(name, v, height, avector, bscalar, apex_to_asymptote):
			brl_db.elliptical_hyperboloid(name, v, height, avector, bscalar, apex_to_asymptote)

		draw_elliptical_hyperboloid("ehy_ellipsoid", v, height_vector, a, bscalar, apex_to_asymptote)

def main(argv):
	with brlcad_tcl(argv[1], "My Database") as brl_db:
		new_ellipsoid_example = ellipsoid_example(brl_db)
	brl_db.save_g()
	brl_db.save_stl(['new_ellipsoid_example'])

if __name__ == "__main__":
	main(sys.argv)