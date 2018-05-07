import sys
import sys
import os
from math import atan
from math import degrees

from python_brlcad_tcl.brlcad_tcl import *

class elip_example(BrlCadModel):
	def __init__(self, brl_db):
		super(elip_example, self).__init__(brl_db)
		v = (0, 0, 0)
		a = (10, 0, 0)
		b = (0, 10, 0)
		c = (0, 0, 10)
		brl_db.Ellipsoid("ellipsoid", v, a, b, c)

def main(argv):
    #with wdb.WDB(argv[1], "My Database") as brl_db:
    with brlcad_tcl(argv[1], "My Database") as brl_db:
        new_ellipsoid = elip_example(brl_db)
        # All units in the database file are stored in millimeters. This constrains
        # the arguments to the mk_* routines to also be in millimeters.
    # process the tcl script into a g database by calling mged
    brl_db.save_g()
    # process the g database into an STL file with a list of regions
    #brl_db.save_stl(['room', 'mainroof', 'roof_window1', 'roof_window2'])  
    brl_db.save_stl(['elip_example'])

if __name__ == "__main__":
    main(sys.argv)