import sys
import sys
import os
from math import atan
from math import degrees

from python_brlcad_tcl.brlcad_tcl import *

class tor_example(BrlCadModel):
	def __init__(self, brl_db):
		super(tor_example, self).__init__(brl_db)
		vertex = (0, 0, 0)
		normal = (0, 1, 1)
		radius_1 = 5
		radius_2 = 2

		def draw_tor(name, v, normal, r1, r2):
			brl_db.torus(name, v, normal, r1, r2)

		draw_tor("Tor_Example", vertex, normal, radius_1, radius_2)

def main(argv):
	with brlcad_tcl(argv[1], "My Database") as brl_db:
		new_tor_example = tor_example(brl_db)
	brl_db.save_g()
	brl_db.save_stl(['new_tor_example'])

if __name__ == "__main__":
	main(sys.argv)