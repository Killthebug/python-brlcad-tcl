import sys
import sys
import os
from math import atan
from math import degrees

from python_brlcad_tcl.brlcad_tcl import *

class grip_example(BrlCadModel):
	def __init__(self, brl_db):
		super(grip_example, self).__init__(brl_db)

		center = (0, 0, 0)
		normal = (3, 0, 0)
		magnitude = 6

		def draw_grip(name, center, normal, magnitude):
			brl_db.grip(name, center, normal, magnitude)


		draw_grip("Grip_Example", center, normal, magnitude)

def main(argv):
	with brlcad_tcl(argv[1], "My Database") as brl_db:
		new_grip_example = grip_example(brl_db)
	brl_db.save_g()
	brl_db.save_stl(['new_grip_example'])

if __name__ == "__main__":
	main(sys.argv)