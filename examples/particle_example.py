import sys
import sys
import os
from math import atan
from math import degrees

from python_brlcad_tcl.brlcad_tcl import *

class particle_example(BrlCadModel):
	def __init__(self, brl_db):
		super(particle_example, self).__init__(brl_db)
		vertex = (0, 0, 0)
		height = (0, 0, 16)
		height_at_v_end = 4
		height_at_h_end = 2

		def draw_particle(name, v, height, h1, h2):
			brl_db.particle(name, v, height, h1, h2)

		draw_particle("My_Particle", vertex, height, height_at_v_end, height_at_h_end)

def main(argv):
	with brlcad_tcl(argv[1], "My Database") as brl_db:
		new_particle_example = particle_example(brl_db)
	brl_db.save_g()
	brl_db.save_stl(['new_particle_example'])

if __name__ == "__main__":
	main(sys.argv)