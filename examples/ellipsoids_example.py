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
		v1 = (3, 2, 8)
		a1 = (3, -1, 8)
		radius = 4

		def draw_elliptical_hyperboloid(name, v, height, avector, bscalar, apex_to_asymptote):
			brl_db.elliptical_hyperboloid(name, v, height, avector, bscalar, apex_to_asymptote)

		def draw_elliptical_paraboloid(name, v, height, avector, bscalar):
			brl_db.elliptical_paraboloid(name, v, height, avector, bscalar)

		def draw_ell1(name, v, avector, radius):
			brl_db.radius_ellipsoid(name, v, avector, radius)

		draw_elliptical_hyperboloid("ehy_ellipsoid", v, height_vector, a, bscalar, apex_to_asymptote)
		draw_elliptical_paraboloid("epa_ellipsoid", v, height_vector, a, bscalar)
		draw_ell1("radius_ellipsoid", v, a1, radius)

def main(argv):
	with brlcad_tcl(argv[1], "My Database") as brl_db:
		new_ellipsoid_example = ellipsoid_example(brl_db)
	brl_db.save_g()
	brl_db.save_stl(['new_ellipsoid_example'])

if __name__ == "__main__":
	main(sys.argv)