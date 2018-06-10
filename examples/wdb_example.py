'''
This is the python version of wdb_example.c using python-brlcad-tcl.

usgae :
    python -m example.wdb_example <<output_name>>.tcl

'''


import sys
import sys
import os
from math import atan
from math import degrees

from python_brlcad_tcl.brlcad_tcl import *

class wdb_example(BrlCadModel):
	def __init__(self, brl_db):
		super(wdb_example, self).__init__(brl_db)
		v = (1, 2, 3)
		radius = 0.75

		pmin = (0, 0, 0)
		pmax = (2, 4, 2.5)

		hole_start = (0, 0, 0)
		hole_depth = (2, 4, 2.5)
		hole_radius = 0.75

		sphere = brl_db.Sphere("ball.s", v, radius)
		box = brl_db.rpp("box.s", pmin, pmax)
		brl_db.region("combined.s",
					  'u {} u {}'.format(box,
										sphere)
					  )
		hole = brl_db.rcc("hole.s", hole_start, hole_depth, hole_radius)

def main(argv):
	with brlcad_tcl(argv[1], "My Database") as brl_db:
		example = wdb_example(brl_db)
	brl_db.save_g()
	brl_db.save_stl(['example'])

if __name__ == "__main__":
	main(sys.argv)