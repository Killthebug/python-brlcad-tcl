import sys
import sys
import os
from math import atan
from math import degrees

from python_brlcad_tcl.brlcad_tcl import *

class polyhedron_example(BrlCadModel):
	def __init__(self, brl_db):
		super(polyhedron_example, self).__init__(brl_db)
		"""
		Dummy values, change when you run the example
		"""
		a = (0, 0, 0)
		b = (10, 0, 0)
		c = (0, 10, 0)
		d = (0, 0, 10)
		e = (0, 10, 10)
		f = (10, 10, 0)
		g = (10, 10, 10)

		def draw_arb4(name, v1, v2, v3, v4):
			brl_db.arb4(name, v1, v2, v3, v4)

		def draw_arb5(name, v1, v2, v3, v4, v5):
			brl_db.arb5(name, v1, v2, v3, v4, v5)

		def draw_arb6(name, v1, v2, v3, v4, v5, v6):
			brl_db.arb6(name, v1, v2, v3, v4, v5, v6)

		def draw_arb7(name, v1, v2, v3, v4, v5, v6, v7):
			brl_db.arb7(name, v1, v2, v3, v4, v5, v6, v7)
		
		first = draw_arb4("tetrahedra", a, b, c, d)
		second = draw_arb5("quadrahedra", a, b, c, d, e)
		third = draw_arb6("pentahedra", a, b, c, d, e, f)
		fourth = draw_arb7("hexahedra", a, b, c, d, e, f, g)

def main(argv):
	with brlcad_tcl(argv[1], "My Database") as brl_db:
		new_polyhedron = polyhedron_example(brl_db)
	brl_db.save_g()
	brl_db.save_stl(['new_polyhedron'])

if __name__ == "__main__":
	main(sys.argv)