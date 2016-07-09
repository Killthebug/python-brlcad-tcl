import os
import numbers
import datetime
import subprocess
from itertools import chain
from abc import ABCMeta
from abc import abstractmethod
from collections import OrderedDict, deque

import vmath


def coord_avg(c1, c2):
    return (c1+c2)/2.

def get_box_face_center_coord(corner1, corner2, xyz_desired):
    # each 'bit' can be -1, 0, or 1
    x_bit, y_bit, z_bit =  [int(b) for b in xyz_desired]
    # only one non-zero value can be provided
    assert([x_bit!=0, y_bit!=0, z_bit!=0].count(True) == 1)
    out_xyz = [0,0,0]
    away_vect = [0,0,0]
    for i, bit in enumerate([x_bit, y_bit, z_bit]):
        if bit<0:
            out_xyz[i] = min(corner1[i], corner2[i])
            away_vect[i] = -1
        elif bit>0:
            out_xyz[i] = max(corner1[i], corner2[i])
            away_vect[i] = 1
        else:
            out_xyz[i] = min(corner1[i], corner2[i]) + (abs(corner1[i] - corner2[i]) / 2.)
    return out_xyz, away_vect


def is_truple(arg):
    is_numeric_truple = (isinstance(arg, tuple) or isinstance(arg, list)) and all([isinstance(x, numbers.Number) for x in arg])
    assert(is_numeric_truple)


def is_number(arg):
    assert(isinstance(arg, numbers.Number))


def two_plus_strings(*args):
    assert(len(args)>2)
    assert(all([isinstance(x, str) for x in args]))


def is_string(name):
    assert(isinstance(name, str))


def union(*args):
    return ' u {}'.format(' u '.join(args))


def subtract(*args):
    return ' u {}'.format(' - '.join(args))


def intersect(*args):
    return ' u {}'.format(' + '.join(args))


class brlcad_tcl():
    def __init__(self, tcl_filepath, title, make_g=False, make_stl=False, stl_quality=None, units = 'mm'):
        #if not os.path.isfile(self.output_filepath):
        #    abs_path = os.path.abspath(self.output_filepath)
        #    if not
        self.make_stl = make_stl
        self.make_g = make_g
        self.g_path = None
        self.tcl_filepath = tcl_filepath
        self.stl_quality = stl_quality
        self.now_path = os.path.splitext(self.tcl_filepath)[0]

        self.script_string = 'title {}\nunits {}\n'.format(title, units)
        self.units = units

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.save_tcl()

        if self.make_g or self.make_stl:
            self.save_g()
        if self.make_stl:
            self.save_stl()
            
    def add_script_string(self, to_add):
        # In case the user does some adding on their own
        self.script_string += '\n' + str(to_add) + '\n'

    def save_tcl(self):
        with open(self.tcl_filepath, 'w') as f:
            f.write(self.script_string)

    def save_g(self):
        self.g_path = self.now_path + '.g'
        # try to remove a databse file of the same name if it exists
        try:
            os.remove(self.g_path)
        except:
            pass

        proc = subprocess.Popen('mged {} < {}'.format(self.g_path, self.tcl_filepath), shell=True)
        proc.communicate()
        
    def run_and_save_stl(self, objects_to_render):
        # Do all of them in one go
        self.save_tcl()
        self.save_g()
        self.save_stl(objects_to_render)

    def save_stl(self, objects_to_render):
        stl_path = self.now_path + '.stl'
        obj_str = ' '.join(objects_to_render)
        cmd = 'g-stl -o {}'.format(stl_path)

        # Add the quality
        """   from http://sourceforge.net/p/brlcad/support-requests/14/#0ced
        The "-a" option specifies an absolute tessellation tolerance
        - the maximum allowed distance (mm) between the real surface
        and the facets
        The "-r" option specifies a relative tessellation tolerance
        - an absolute tolerance is calculated as the relative
        tolerance times the "size" of the object being tessellated
        (for a sphere, the "size" is the radius).
        The "-n" option specifies the maximum surface normal error
        (in radians).
        By default, tessellations are performed using a relative
        tolerance of 0.01. Try using the -r option with values other
        than 0.01.
        """
        """  from http://permalink.gmane.org/gmane.comp.cad.brlcad.devel/4600
        For example, setting g-stl -n 1.0 should create a polygon for every 1-degree difference in curvature. 
        Since your model has a lot of circular edges, this should me a considerable visual improvement.  Setting
        the absolute tolerance to some sub-zero value should have a similar effect, but be careful to not specify a
        number too small or you may inadvertently create many GB of polygons (or worse).
        """

        if self.stl_quality and self.stl_quality > 0:
            cmd = '{} -a {}'.format(cmd, self.stl_quality)

        # Add the paths
        cmd = '{} {} {}'.format(cmd, self.g_path, obj_str)

        print cmd
        proc = subprocess.Popen(cmd, shell=True)
        proc.communicate()

    def export_slices(self, slice_thickness, max_slice_x, max_slice_y, output_format=''):
        tl_names = self.get_top_level_object_names()
        xyz1, xyz2 = self.get_opposing_corners_bounding_box(self.get_bounding_box_coords_for_entire_db(tl_names))
        print 'bb of all items {} to {}'.format(xyz1, xyz2)

        if abs(xyz1[0] - xyz2[0]) > max_slice_x:
            raise Exception('x dimension exceeds buildable bounds')
        if abs(xyz1[1] - xyz2[1]) > max_slice_y:
            raise Exception('y dimension exceeds buildable bounds')

        slice_coords = list(self.get_object_slice_coords(slice_thickness, xyz1, xyz2))

        for i, object_slice_bb_coords in enumerate(slice_coords):
            print 'slice_bb{}.s'.format(i)
            self.cuboid('slice_bb{}.s'.format(i), object_slice_bb_coords[0], object_slice_bb_coords[1])
            # finally create a region (a special combination that means it's going to be rendered)
            # by unioning together the main combinations we just created
            tl_name_plussed = ' + '.join(tl_names)
            slice_reg_name = 'slice{}.r'.format(i)
            self.region(slice_reg_name,
                          'u slice_bb{}.s + {}'.format(i, tl_name_plussed)
                          )
        return slice_coords
            # save_object_image_from_z_projection(object_slice, output_format)

    def get_object_slice_coords(self, slice_thickness, xyz1, xyz2):
        # num_slices = abs(xy1[2] - xy2[2]) / slice_thickeness
        lz = min(xyz1[2], xyz2[2])
        mz = max(xyz1[2], xyz2[2])
        iz = lz
        while iz < mz:
            c1 = [c for c in xyz1]
            c1[2] = iz
            c2 = [c for c in xyz2]
            iz += slice_thickness
            if iz>mz:
                iz=mz
            c2[2] = iz
            for i in range(3):
                if c1[i]>c2[i]:
                    g = c1[i]
                    c1[i] = c2[i]
                    c2[i] = g
            yield (c1, c2)
        #direction
        #for  in range():

    def get_top_level_object_names(self):
        """
        The "tops" command displays a list of all the top-level objects in the current database.
        The top-level objects are all those objects that are not referenced by some other combination.
        The hierarchical structure of BRL-CAD databases usually means that there will be a top-level 
        object that includes all (or at least most) of the objects in the database.
        The -g option shows only geometry objects. The -n option specifies that no "decoration" 
        (e.g., "/" and "/R") be shown at the end of each object name. 
        The -u option will not show hidden objects. See also the hide command.
        """
        proc = subprocess.Popen('mged {} "tops"'.format(self.g_path),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                shell=True)
        (stdoutdata, stderrdata) = proc.communicate()
        print stdoutdata
        print stderrdata
        flattened = [segment.strip().rstrip('/R') for segment in stderrdata.strip().split()]
        print 'tops found: {}'.format(flattened)
        return flattened

    def get_bounding_box_coords_for_entire_db(self, name_list):
        part_names = ' '.join(name_list)
        return self.get_bounding_box_coords(part_names)

    def get_bounding_box_coords(self, obj_name):
        """
        The "l" command displays a verbose description about the specified list of objects.
        If a specified object is a path, then any transformation matrices along that path are applied.
        If the final path component is a combination, the command will list the Boolean formula for the 
        combination and will indicate any accumulated transformations (including any in that combination).
        If a shader and/or color has been assigned to the combination, the details will be listed.
        For a region, its ident, air code, material code, and LOS will also be listed.
        For primitive shapes, detailed shape parameters will be displayed with the accumulated transformation 
        applied. If the -r (recursive) option is used, then each object on the command line will be treated 
        as a path. If the path does not end at a primitive shape, then all possible paths from that point 
        down to individual shapes will be considered. The shape at the end of each possible path will be 
        listed with its parameters adjusted by the accumulated transformation.
        """
        proc = subprocess.Popen('mged {} "make_bb temp_box {}; l temp_box"'.format(self.g_path, obj_name),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                shell=True)
        
        (stdoutdata, stderrdata) = proc.communicate()
        # print (stdoutdata, stderrdata)
        subprocess.Popen('mged {} "kill temp_box"'.format(self.g_path), shell=True).communicate()

        bb_coords = []
        print 'stderrdata.split {}'.format(stderrdata.split('\n')[1:])
        for segment in stderrdata.split('\n')[1:]:
            if '(' not in segment:
                continue
            first_paren = segment.index('(')
            second_paren = segment.index(')')
            x,y,z = segment[first_paren+1:second_paren].split(',')
            
            x=float(x)
            y=float(y)
            z=float(z)
            bb_coords.append((x, y, z))
            print '(x, y, z) {}'.format((x, y, z))
        print bb_coords
        return bb_coords

    def get_opposing_corners_bounding_box(self, bb_coords):
        _bb_coords = sorted(list(bb_coords))
        # take any of corners
        first = _bb_coords.pop()
        # now find one that opposes it
        for axis in {0: 'x', 1: 'y', 2: 'z'}:
            for coord in list(_bb_coords):
                if coord[axis] == first[axis]:
                    _bb_coords.remove(coord)
        second = _bb_coords[0]
        return (first, second)

    def set_combination_color(self, obj_name, R, G, B):
        is_string(obj_name)
        self.script_string += 'comb_color {} {} {} {}'.format(obj_name, R, G, B)

    def combination(self, name, operation):
        is_string(name)
        self.script_string += 'comb {} {}\n'.format(name, operation)

    def group(self, name, operation):
        is_string(name)
        self.script_string += 'g {} {}\n'.format(name, operation)

    def region(self, name, operation):
        is_string(name)
        self.script_string += 'r {} {}\n'.format(name, operation)

    def begin_combination_edit(self, combination_to_select, path_to_center):
        self.script_string += 'Z\n'
        self.script_string += 'draw {}\n'.format(combination_to_select)
        self.script_string += 'oed / {0}/{1}\n'.format(combination_to_select, path_to_center)

    def begin_primitive_edit(self, name):
        #self.script_string += 'Z\n'
        #self.script_string += 'draw {}\n'.format(name)
        self.script_string += 'sed {0}\n'.format(name)

    def end_combination_edit(self):
        self.script_string += 'accept\n'

    def translate(self, x, y, z, relative=False):
        cmd = 'translate'
        if relative:
            cmd = 'tra'
        self.script_string += '{} {} {} {}\n'.format(cmd, x, y, z)

    def translate_relative(self, dx, dy, dz):
        self.translate(dx, dy, dz, relative=True)

    def rotate_combination(self, x, y, z):
        self.script_string += 'orot {} {} {}\n'.format(x,y,z)

    def rotate_primitive(self, name, x, y, z, angle=None):
        is_string(name)
        self.begin_primitive_edit(name)
        self.script_string += 'keypoint {} {} {}\n'.format(x,y,z)
        if angle:
            self.script_string += 'arot {} {} {} {}\n'.format(x,y,z, angle)
        else:
            self.script_string += 'rot {} {} {}\n'.format(x,y,z)
        self.end_combination_edit()

    def kill(self, name):
        if isinstance(name, list):
            for _name in name:
                self.script_string += 'kill {}\n'.format(_name)
        else:
            self.script_string += 'kill {}\n'.format(name)

    def rcc(self, name, base, height, radius):
        is_string(name)
        is_truple(base)
        is_truple(height)
        is_number(radius)
        bx, by,bz=base
        hx,hy,hz=height
        self.script_string += 'in {} rcc {} {} {} {} {} {} {}\n'.format(name,
                                                                     bx,by,bz,
                                                                     hx,hy,hz,
                                                                     radius)

    def rpc(self, name, vertex, height_vector, base_vector, half_width):
        is_string(name)
        is_truple(vertex)
        is_truple(height_vector)
        is_truple(base_vector)
        is_number(half_width)
        vx, vy, vz = vertex
        hx, hy, hz = height_vector
        bx, by, bz = base_vector
        self.script_string += 'in {} rpc {} {} {} {} {} {} {} {} {} {}\n'.format(name,
                                                                                 vx,vy,vz,
                                                                                 hx,hy,hz,
                                                                                 bx,by,bz,
                                                                                 half_width)

    def box_by_opposite_corners(self, name, pmin, pmax):
        self.rpp(self, name, pmin, pmax)

    def circular_cylinder(self, name, base_center_point, top_center_point, radius):
        self.rcc(name, base_center_point, top_center_point, radius)

    def rpp(self, name, pmin, pmax):
        is_string(name)
        is_truple(pmin)
        is_truple(pmax)
        minx,miny,minz = pmin
        maxx,maxy,maxz = pmax
        self.script_string += 'in {} rpp {} {} {} {} {} {}\n'.format(name,
                                                                     minx,maxx,
                                                                     miny,maxy,
                                                                     minz,maxz)

    def cuboid(self, name, corner_point, opposing_corner_point):
        self.rpp(name, corner_point, opposing_corner_point)

    def arb4(self, name, v1, v2, v3, v4):
        is_string(name)

    def arb5(self, name, v1, v2, v3, v4, v5):
        is_string(name)

    def arb6(self, name, v1, v2, v3, v4, v5, v6):
        is_string(name)

    def arb7(self, name, v1, v2, v3, v4, v5, v6, v7):
        is_string(name)

    def arb8(self, name, points):
        is_string(name)
        check_args = [is_truple(x) for x in points]
        assert(len(points)==8)
        points_list =  ' '.join([str(c) for c in chain.from_iterable(points)])
        
        #print 'arb8 points list: {}\n\n{}'.format(points, points_list)
        
        self.script_string += 'in {} arb8 {} \n'.format(name,
                                                        points_list
                                                        )

                                                        
    def arbX(self, name, vList):
        #Detect which function to use, and feed in the parameters
        if len(vList) in range(4, 9):
            arbFunction = getattr(self, "arb" + str(len(vList)))
            
            #Execute it
            arbFunction(name, *vList)
        
        
    def Cone(self, name, trc, vertex, height_vector, base_radius, top_radius):
        is_string(name)


    def Cone_elliptical(self, name, tec, vertex, height_vector, major_axis, minor_axis, ratio):
        is_string(name)


    def Cone_general(self, name, tgc, vertex, height_vector, avector, bvector, cscalar, dscalar):
        is_string(name)


    def Cylinder(self, name, vertex, height_vector, radius):
        self.rcc(name, vertex, height_vector, radius)

    def Cylinder_elliptical(self, name, rec, vertex, height_vector, major_axis, minor_axis):
        is_string(name)

    def Cylinder_hyperbolic(self, name, rhc,vertex, height_vector, bvector, half_width, apex_to_asymptote):
        is_string(name)

    def Cylinder_parabolic(self, name, rpc, vertex, height_vector, bvector, half_width):
        is_string(name)

    def Ellipsoid(self, name, ell, vertex, avector, bvector, cvector):
        is_string(name)

    def Hyperboloid_elliptical(self, name, ehy, vertex, height_vector, avector, bscalar, apex_to_asymptote):
        is_string(name)

    def Paraboloid_elliptical(self, name, epa, vertex, height_vector, avector, bscalar):
        is_string(name)


    def Ellipsoid_radius(self, name, ell1, vertex, radius):
        is_string(name)


    def Particle(self, name, part, vertex, height_vector, radius_at_v_end, radius_at_h_end):
        is_string(name)


    def Sphere(self, name, sph, vertex, radius):
        is_string(name)


    def Torus(self, name, tor, vertex, normal, radius_1, radius_2):
        is_string(name)


    def Torus_elliptical(self, name, eto, vertex, normal_vector, radius, cvector, axis):
        is_string(name)


    def pipe_point(self, x, y, z, inner_diameter, outer_diameter, bend_radius):
        return OrderedDict(
                           [('x', x),
                            ('y', y),
                            ('z', z),
                            ('inner_diameter', inner_diameter),
                            ('outer_diameter', outer_diameter),
                            ('bend_radius', bend_radius)
                           ]
                          )

    def pipe(self, name, pipe_points):
        is_string(name)
        num_points = len(pipe_points)
        assert(num_points>1)

        if isinstance(pipe_points[0], dict):
            points_str_list = ['{} {} {} {} {} {}'.format(*points.values()) for points in pipe_points]
        # handle the way the hilbert_3d example from python-brlcad was using the Vector class
        elif isinstance(pipe_points[0][0], vmath.vector.Vector):
            def rotate_tuple(x): d = deque(list(x)); d.rotate(2); return d
            points_str_list = ['{} {} {} {} {} {}'.format(*(list(points[0]) + list(rotate_tuple(points[1:]))) ) for points in pipe_points]
        self.script_string += 'in {} pipe {} {}\n'.format(name, num_points, ' '.join(points_str_list) )
        """ # this worked for me as a spring
        in spring.s pipe 10 -500 -500 250 10 200 500 -500 500 350 100 200 500 500 500 450 100 200 500 500 -500 550 100 200 500 -500 -500 650 100 200 500 -500 500 750 100 200 500 500 500 850 100 200 500 500 -500 950 100 200 500 -500 -500 1050 100 200 500 -500 500 1150 100 200 500 0 500 1200 100 200 500
        r s.r u spring.s
        """


class BrlCadModel(object):
    __metaclass__ = ABCMeta
    def __init__(self, brl_db, name_tracker):
        self.brl_db = brl_db
        self.name_tracker = name_tracker
        self.get_next_name = self.name_tracker.get_next_name
        self.final_name = None
        self.connection_points = []

    def register_new_connection_point(self, name, coord, away_vector):
        self.connection_points.append((name, coord, away_vector))

    def get_connection(self, name):
        for item in self.connection_points:
            if item[0] == name:
                return item
        return None

    @property
    def connections_available(self):
        return [item[0] for item in self.connection_points]
