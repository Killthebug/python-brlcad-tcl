# standard libs
import os
import re
import sys
import math
import inspect
import numbers
import datetime
import subprocess
from itertools import chain
from abc import ABCMeta
from abc import abstractmethod
from collections import OrderedDict, deque

# external libs
import numpy
from PIL import Image

# internal
from . import vmath
from .brlcad_name_tracker import BrlcadNameTracker


def check_cmdline_args(file_path):
    if not len(sys.argv)==2:
        print('usage:\n'\
              '      {} file_name_for_output'.format(file_path))
        sys.exit(1)
    return sys.argv[1]


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
    assert(is_numeric_truple), arg


def is_number(arg):
    assert(isinstance(arg, numbers.Number))

def is_ratio(arg):
    assert(isinstance(arg, numbers.Number) and arg > 0)


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
    def __init__(self, tcl_filepath, title, make_g=False, make_stl=False, stl_quality=None, units='mm', verbose=False):
        #if not os.path.isfile(self.output_filepath):
        #    abs_path = os.path.abspath(self.output_filepath)
        #    if not
        self.make_stl = make_stl
        self.make_g = make_g
        self.g_path = None
        self.tcl_filepath = tcl_filepath
        self.stl_quality = stl_quality
        self._input_file_path_no_ext = self._remove_file_extension(self.tcl_filepath)

        self.script_string_list = ['title {}\nunits {}\n'.format(title, units)]
        self.units = units
        self.name_tracker = BrlcadNameTracker()
        self.verbose = verbose

    def _remove_file_extension(self, file_path):
        return os.path.splitext(file_path)[0]
    

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
        self.script_string_list.append( '\n' + str(to_add) + '\n')

    def save_tcl(self):
        for line in self.script_string_list:
            if not line.endswith('\n'):
                raise Exception("line ({}) didn't end with a \\n".format(line))
        with open(self.tcl_filepath, 'w') as f:
            f.write(''.join(self.script_string_list))

    def _which(self, program):
        def is_exe(fpath):
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

        fpath, fname = os.path.split(program)
        if fpath:
            if is_exe(program):
                return program
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                path = path.strip('"')
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file

    def save_g(self):
        self.g_path = self._input_file_path_no_ext + '.g'
        # try to remove a database file of the same name if it exists
        try:
            os.remove(self.g_path)
            print('removed {}?: {}'.format(self.g_path, os.path.isfile(self.g_path)))
        except Exception as e:
            if not e.errno == 2:
                print('WARNING: could not remove: {}\nuse different file name, or delete the file manually first!'.format(self.g_path))
                raise (e)
        
        cmd = 'mged {} < {}'.format(self.g_path, self.tcl_filepath)
        cmd = [self._which('mged'), self.g_path]
        print('running mged with command: {}'.format(cmd))
        #proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

        if self.verbose:
            proc = subprocess.Popen(cmd, shell=False, stdin=subprocess.PIPE)
        else:
            proc = subprocess.Popen(cmd, shell=False, stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.communicate(''.join(self.script_string_list))
        #proc.communicate(['opendb {}\n'.format(self.g_path)] + self.script_string_list)
        #proc.communicate()
        
    def run_and_save_stl(self, objects_to_render):
        # Do all of them in one go
        self.save_tcl()
        self.save_g()
        self.save_stl(objects_to_render)

    def save_stl(self, objects_to_render, output_path=None):
        if output_path is None:
            stl_path = self._input_file_path_no_ext + '.stl'
        else:
            stl_path = output_path if output_path.endswith('.stl') else '{}.stl'.format(output_path)
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
            cmd = '{} -n {}'.format(cmd, self.stl_quality)

        # Add the paths
        cmd = '{} {} {}'.format(cmd, self.g_path, obj_str)

        print('running: {}'.format(cmd))
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc.communicate()

    def export_image_from_Z(self, item_name, width, height, output_path=None, azimuth=None, elevation=None):
        if output_path is None:
            output_path = '{}.png'.format(self._input_file_path_no_ext)
        if azimuth is None:
            azimuth = -90
        if elevation is None:
            elevation = -90

        try:
            os.remove(output_path)
        except:
            pass
        # on Linux, use 'man rt' on the command-line to get all the info... 
        # (it is still not terribly straight-forward)
        cmd = 'rt -a {} -l3 -e {} -w {} -n {} -o {} {} {}'\
              .format(azimuth, elevation, width, height, output_path, self.g_path, item_name)
        print('\nrunning: {}'.format(cmd))
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        proc.communicate()
        return output_path

    def create_slice_regions(self, slice_thickness, max_slice_x, max_slice_y, output_format=''):
        tl_names = self.get_top_level_object_names()
        xyz1, xyz2 = self.get_opposing_corners_bounding_box(self.get_bounding_box_coords_for_entire_db(tl_names))
        #print 'bb of all items {} to {}'.format(xyz1, xyz2)

        if abs(xyz1[0] - xyz2[0]) > max_slice_x:
            raise Exception('x dimension exceeds buildable bounds {} {} {}'.format(xyz1[0], xyz2[0], max_slice_x))
        if abs(xyz1[1] - xyz2[1]) > max_slice_y:
            raise Exception('y dimension exceeds buildable bounds')

        slice_coords = list(self.get_object_slice_coords(slice_thickness, xyz1, xyz2))
        self.slice_coords = []
        temps_to_kill = []

        for i, object_slice_bb_coords in enumerate(slice_coords):
            # = self.name_tracker.get_next_name(self, 'slice_bb{}_num.s'.format(i))
            slice_bb_temp = self.cuboid(object_slice_bb_coords[0], object_slice_bb_coords[1])
            temps_to_kill.append(slice_bb_temp)
            # finally create a region (a special combination that means it's going to be rendered)
            # by unioning together the main combinations we just created
            tl_name_plussed = ' + '.join(tl_names)
            # slice_reg_name = self.name_tracker.get_next_name(self, 'slice{}_num.c'.format(i))
            
            slice_reg_name = self.region('slice{}_num.r'.format(i),
                                              'u {} + {}'.format(slice_bb_temp, tl_name_plussed)
                                              )
            temps_to_kill.append(slice_reg_name)
            self.slice_coords.append((slice_reg_name, object_slice_bb_coords))
        self.save_tcl()
        self.save_g()
        # [self.kill(temp_bb) for temp_bb in temps_to_kill]
        # self.save_tcl()
        # self.save_g()
        return self.slice_coords, temps_to_kill

    def get_object_raster_from_z_projection(self,
                                            slice_region_name,
                                            model_min,
                                            model_max,
                                            slice_thickness,
                                            ray_destination_dir_xyz=[0, 0, -1],
                                            bmp_output_name=None,
                                            num_pix_x=1024,
                                            num_pix_y=1024,
                                            output_greyscale=True,
                                            threading_event=None):
        num_pix_x = math.ceil(num_pix_x)
        num_pix_y = math.ceil(num_pix_y)
        # each 'bit' can be -1, 0, or 1
        x_bit, y_bit, z_bit = [int(b) for b in ray_destination_dir_xyz]
        # only one non-zero value can be provided
        assert([x_bit!=0, y_bit!=0, z_bit!=0].count(True) == 1)

        model_width = model_max[0] - model_min[0]
        model_length = model_max[1] - model_min[1]
        x_offset = (0-model_min[0])
        y_offset = (0-model_min[1])

        x_scale = num_pix_x/model_width
        y_scale = num_pix_y/model_length

        x_step = model_width/num_pix_x
        y_step = model_length/num_pix_y

        step_size = max(x_step, y_step)
        
        
        if threading_event:
            threading_event.set()
        # create a list for the NIRT command lines to be queued
        nirt_script_path = '{}.nirt'.format(self._input_file_path_no_ext)
        nirt_script_file = open(nirt_script_path, 'w')

        # set the direction to fire rays in
        nirt_script_file.write('dir {} {} {}\n'.format(x_bit, y_bit, z_bit))
        nirt_script_file.write('units {}\n'.format(self.units))
        x = model_min[0]
        z = model_max[2]

        xstepcount = 0
        # the raster loops, loop over each Y for each X location
        while x < model_max[0]:
            # start Y at the minimum for each Y loop
            y = model_min[1]
            ystepcount = 0
            # loop while Y is less than the model's max Y
            while y < model_max[1]:
                # move around the model in X and Y axes, using the determined step-size
                nirt_script_file.write('xyz {} {} {}\n'.format(x, y, z))
                # fire a ray
                nirt_script_file.write('s\n')
                # step in Y
                y += step_size
                ystepcount += 1
            # make sure we aren't going out-of-bounds
            assert ystepcount <= num_pix_y, (ystepcount, num_pix_y)
            # step in X
            x += step_size
            xstepcount += 1
        # make sure we aren't going out-of-bounds
        assert xstepcount <= num_pix_x, (xstepcount, num_pix_x)
        nirt_script_file.close()
        
        # the -s command might speed things up???
        #args = ['nirt', '-s', self.g_path, slice_region_name]
        args = 'nirt -s {} {} < {}'.format(self.g_path, slice_region_name, nirt_script_path)
        print('\nrunning: {}'.format(args))

        # pass the commands to NIRT, get NIRT's response
        p = subprocess.Popen(args,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, shell=True)
        outp = p.communicate()

        chunks = []
        # break up NIRT's response by newline
        out_lines = outp[0].split('\n')
        err_lines = outp[1].split('\n')
        
        im = numpy.zeros((num_pix_x, num_pix_y))
        # r = re.compile(r'\((\s*-?\d+\.?\d+)\s+(-?\d+\.?\d+)\s+(-?\d+\.?\d+)\)')
        r = re.compile(r'\((\s*-?\d+\.?\d+)\s+(-?\d+\.?\d+)\s+(-?\d+\.?\d+)\)\s+(-?\d+\.?\d+)')
        hit_description_header = '    Region Name               Entry (x y z)              LOS  Obliq_in Attrib'
        missed_target = 'You missed the target'
        state = 0

        decade = len(out_lines)/10
        for il, l in enumerate(out_lines):
            # if il%decade==0:
            #     print '{}% completed parsing NIRT output'.format(float(il)/len(out_lines)*100)

            # check if we are starting a new section IF:
            # we are just starting, or we got at least one coordinate
            if (state == 0 or state == 3) and l.startswith('Origin'):
                    # and out_lines[out_lines.index(l)+1].startswith('Direction'):
                state = 1
                chunks.append({'Origin': l, 'Coords': []})
            elif state == 1:
                state = 2
                chunks[-1]['Direction'] = l
            elif state == 2:
                if l.startswith(hit_description_header) or (not l):
                    continue
                # we got a hit or miss
                state = 3
                if missed_target in l:
                    continue
                # store the line for later
                chunks[-1]['Coords'].append(l)
                m = r.search(l)
                if not m:
                    print('first 10 lines out:\n{}'.format(out_lines[:10]))
                    print('first err:\n{}'.format(err_lines[:1]))
                    raise Exception("regex didn't work to find coordinates! report this bug. on input line {}".format(l))
                x, y, z, depth_of_hit = m.groups()

                zeroed_x = (float(x) - model_min[0])
                zeroed_y = (float(y) - model_min[1])
                if zeroed_x:
                    floated_x = zeroed_x/step_size
                    int_x = int(round(floated_x))
                    # enable this if you are paranoid about the math
                    # numpy.testing.assert_approx_equal(floated_x, int_x, 4, 'these were not equal:\n{}\n{}'.format(floated_x, int_x))
                else:
                    int_x = 0
                if zeroed_y:
                    floated_y = zeroed_y/step_size
                    int_y = int(round(floated_y))
                    # enable this if you are paranoid about the math
                    # numpy.testing.assert_approx_equal(floated_y, int_y, 4, 'these were not equal:\n{}\n{}'.format(floated_y, int_y))
                else:
                    int_y = 0

                if output_greyscale:
                    im[int_x, int_y] = (float(depth_of_hit)/slice_thickness)*255
                else:
                    im[int_x, int_y] = 1

            elif state==3:
                # we already got a hit for this spot, so we don't need to check again
                continue

        if output_greyscale:
            result = Image.fromarray(im.astype(numpy.uint8))
        else:
            result = Image.fromarray((im * 255).astype(numpy.uint8))
        result.save(bmp_output_name)
        return bmp_output_name

    def export_model_slices(self,
                            num_slices_desired,
                            max_slice_x, max_slice_y,
                            output_format='stl', output_option_kwargs={}, output_path_format=None):
        """

        :param num_slices_desired:    the number of equal-sized slices you want to end up with
        :param max_slice_x:           the maximum X dimension you want to export (in model units)
        :param max_slice_y:           the maximum Y dimension you want to export (in model units)
        :param output_format:         either 'raster' or 'stl' currently
        :param output_option_kwargs:  i.e. 'raster' format supports 'greyscale_output':True/False
        :param output_path_format:    a string with two {} that the g-database path and slice-num are inserted into
        :return:                      nothing
        """
        orig_path = self._input_file_path_no_ext
        orig_tcl = self.script_string_list
        self.save_tcl()
        self.save_g()
        # calculate the slice thickness needed to get the number of slices requested
        tl_names = self.get_top_level_object_names()
        print('top level names about to be exported: {}'.format(tl_names))
        xyz1, xyz2 = self.get_opposing_corners_bounding_box(self.get_bounding_box_coords_for_entire_db(tl_names))
        print('top level items bounding-box: {} to {}'.format(xyz1, xyz2))

        slice_thickness = abs(xyz2[2] - xyz1[2]) / float(num_slices_desired)

        # now create the slice regions
        slice_coords, temps_to_kill = self.create_slice_regions(slice_thickness, max_slice_x, max_slice_y)

        import threading
        threads = []
        for i, (slice_obj_name, sc) in enumerate(slice_coords):
            if output_format == 'raster':
                if not output_path_format:
                    output_path_format='{}{}.jpg'
                e = threading.Event()
                output_filename = output_path_format.format(self._input_file_path_no_ext, i)
                default_raster_kwargs = {'bmp_output_name': output_filename,
                                         'threading_event': e}
                default_raster_kwargs.update(output_option_kwargs)
                t = threading.Thread(target=self.get_object_raster_from_z_projection,
                                     args=(slice_obj_name,
                                           sc[0],
                                           sc[1],
                                           slice_thickness),
                                     kwargs=default_raster_kwargs)
                t.daemon = True
                t.start()
                # try waiting for NIRT to finish, before starting the next thread
                e.wait()
                # TODO: improve speed of NIRT jobs if possible
                # calling multiple NIRT processes at once doesn't seem to work
                # just wait for each thread to finish
                t.join()
                threads.append(t)
                # allow a max of 4 NIRT process threads
                while len(threads) >= 4:
                    threads.pop(0).join()
            elif output_format == 'stl':
                if not output_path_format:
                    output_path_format = '{}{}'

                self._input_file_path_no_ext = output_path_format.format(orig_path, i)

                if i == 0:
                    self.run_and_save_stl([slice_obj_name])
                else:
                    self.save_stl([slice_obj_name])

        # post-loop output-format specific stuff
        if output_format == 'raster':
            while threads:
                threads.pop(0).join()
            self.script_string_list = []
            # get rid of the slices, so they don't show up as top-level objects if user exports slices again
            # destroy the objects in the reverse order of how they were created
            # [self.kill(temp_bb) for temp_bb in reversed(temps_to_kill)]
            # self.save_tcl()
            # self.save_g()
            self.script_string_list = orig_tcl
            self.save_tcl()
        elif output_format == 'stl':
            self._input_file_path_no_ext = orig_path

    @staticmethod
    def get_object_slice_coords(slice_thickness, xyz1, xyz2):
        lz = min(xyz1[2], xyz2[2])
        mz = max(xyz1[2], xyz2[2])
        iz = lz
        while iz < mz:
            c1 = [c for c in xyz1]
            c1[2] = iz
            c2 = [c for c in xyz2]
            iz += slice_thickness
            if iz > mz:
                iz = mz
            c2[2] = iz
            for i in range(3):
                if c1[i] > c2[i]:
                    g = c1[i]
                    c1[i] = c2[i]
                    c2[i] = g
            yield (c1, c2)

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
        # print stdoutdata
        # print stderrdata
        flattened = [segment.strip().rstrip('/R') for segment in stderrdata.strip().split()]
        # print 'tops found: {}'.format(flattened)
        return flattened

    def get_bounding_box_coords_for_entire_db(self, name_list):
        part_names = ' '.join(name_list)
        return self.get_bounding_box_coords(part_names)

    def get_bounding_box_coords(self, obj_name, mged_post_7_26=False, auto_retry=True):
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
        if not mged_post_7_26:
            make_bb_cmd = 'make_bb'
        else:
            make_bb_cmd = 'bb -c'
        args = 'mged {} "{} temp_box {}; l temp_box"'.format(self.g_path, make_bb_cmd, obj_name)
        proc = subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                shell=True)
        
        (stdoutdata, stderrdata) = proc.communicate()
        if auto_retry and 'invalid command name "make_bb"' in stderrdata:
            if self.verbose:
                print('retrying this command (obj_name: {}), as stderr returned: {}'.format(obj_name, stderrdata))
            return self.get_bounding_box_coords(obj_name, not mged_post_7_26, auto_retry=False)
        elif self.verbose:
            print (stdoutdata, stderrdata)
        subprocess.Popen('mged {} "kill temp_box"'.format(self.g_path), shell=True).communicate()

        bb_coords = []
        # print 'stderrdata.split {}'.format(stderrdata.split('\n')[1:])
        for segment in stderrdata.split('\n')[1:]:
            if '(' not in segment:
                continue
            first_paren = segment.index('(')
            second_paren = segment.index(')')
            x, y, z = segment[first_paren+1:second_paren].split(',')
            
            x = float(x)
            y = float(y)
            z = float(z)
            bb_coords.append((x, y, z))
            # print '(x, y, z) {}'.format((x, y, z))
        # print bb_coords
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
        self.script_string_list.append( 'comb_color {} {} {} {}'.format(obj_name, R, G, B))

    def combination(self, name, operation):
        is_string(name)
        name = self._default_name_(name)
        self.script_string_list.append( 'comb {} {}\n'.format(name, operation))
        return name

    def group(self, name, operation):
        is_string(name)
        name = self._default_name_(name)
        self.script_string_list.append( 'g {} {}\n'.format(name, operation))
        return name

    def region(self, name, operation):
        is_string(name)
        name = self._default_name_(name)
        self.script_string_list.append( 'r {} {}\n'.format(name, operation))
        return name

    def begin_combination_edit(self, combination_to_select, path_to_center):
        if not path_to_center.endswith('.s'):
            (frame, filename, line_number,
                function_name, lines, index) = inspect.getouterframes(inspect.currentframe())[1]
            print('WARNING: right-hand-side arg to begin_combination_edit does not have the .s file extension, which indicates a primitive may not have been passed! Watch out for errors!!!')
            print('(in file: {}, line: {}, function-name: {})'.format(filename, line_number, function_name))
        self.script_string_list.append( 'Z\n')
        self.script_string_list.append( 'draw {}\n'.format(combination_to_select))
        self.script_string_list.append( 'oed / {0}/{1}\n'.format(combination_to_select, path_to_center))

    def begin_primitive_edit(self, name):
        self.script_string_list.append( 'Z\n')
        self.script_string_list.append( 'draw {}\n'.format(name))
        self.script_string_list.append( 'sed {0}\n'.format(name))

    def end_combination_edit(self):
        self.script_string_list.append( 'accept\n')

    def remove_object_from_combination(self, combination, object_to_remove):
        self.script_string_list.append( 'rm {} {}\n'.format(combination, object_to_remove))

    def keypoint(self, x, y, z):
        self.script_string_list.append('keypoint {} {} {}\n'.format(x, y, z))

    def translate(self, x, y, z, relative=False):
        cmd = 'translate'
        if relative:
            cmd = 'tra'
        self.script_string_list.append( '{} {} {} {}\n'.format(cmd, x, y, z))

    def translate_relative(self, dx, dy, dz):
        self.translate(dx, dy, dz, relative=True)

    def rotate_combination(self, x, y, z):
        self.script_string_list.append('orot {} {} {}\n'.format(x, y, z))

    def rotate_primitive(self, name, x, y, z, angle=None):
        is_string(name)
        self.begin_primitive_edit(name)
        self.keypoint(x, y, z)
        if angle:
            self.script_string_list.append( 'arot {} {} {} {}\n'.format(x, y, z, angle))
        else:
            self.script_string_list.append( 'rot {} {} {}\n'.format(x, y, z))
        self.end_combination_edit()

    def rotate_angle(self, name, x, y, z, angle, obj_type='primitive'):
        if obj_type=='primitive':
            self.script_string_list.append( 'Z\n')
            self.script_string_list.append( 'draw {}\n'.format(name))
            self.script_string_list.append( 'sed {}\n'.format(name))
        else:
            raise NotImplementedError('add non primitive editing start command')
        self.script_string_list.append( 'arot {} {} {} {}\n'.format(x,y,z, angle))
        self.script_string_list.append( 'accept\n')
        # self.script_string_list.append( 'Z\n')

    def repeated_error(self, name, primitive, myList):
        print "Invalid Vertices :", myList
        sys.exit("Error : Vertices should be unique in : {} {} ".format(primitive, name))

    def kill(self, name):
        if isinstance(name, list):
            for _name in name:
                self.script_string_list.append( 'kill {}\n'.format(_name))
        else:
            self.script_string_list.append( 'kill {}\n'.format(name))

    def _default_name_(self, name):
        caller_func_name = inspect.stack()[1][3]
        if name is None or name is '':
            nname = self.name_tracker.get_next_name(self, '{}.s'.format(caller_func_name))
            #print('_default_name_ generated: {}'.format(nname))
        else:
            if name not in self.name_tracker.num_parts_in_use_by_part_name:
                self.name_tracker.increment_counter_for_name(name)
                return name
            nname = self.name_tracker.get_next_name(self, name)
        return nname

    def _check_name_unused_(self, name):
        if name in self.name_tracker.num_parts_in_use_by_part_name:
            (frame, filename, line_number,
                function_name, lines, index) = inspect.getouterframes(inspect.currentframe())[1]
            raise Exception('name: {} already used! (in file: {}, line: {}, function-name: {})'.format(name, filename, line_number, function_name))
    
    def grip(self, name, center, normal, magnitude):
        name = self._default_name_(name)
        is_string(name)
        is_truple(center)
        is_truple(normal)
        is_number(magnitude)

        cx, cy, cz = center
        nx, ny, nz= normal

        self.script_string_list.append(  'in {} grip {} {} {}\
                                                     {} {} {}\
                                                     {}\n'.format(name,
                                                                cx, cy, cz,
                                                                nx, ny, nz,
                                                                magnitude))

        return name


    def trc(self, name, vertex, height_vector, base_radius, top_radius):
        name = self._default_name_(name)
        is_string(name)
        is_truple(vertex)
        is_truple(height_vector)
        is_number(base_radius)
        is_number(top_radius)

        vx, vy, vz = vertex
        hx, hy, hz = height_vector
        self.script_string_list.append( 'in {} trc {} {} {} '\
                                       ' {} {} {}'\
                                       ' {} {}\n'.format(name,
                                                         vx, vy, vz,
                                                         hx, hy, hz,
                                                         base_radius, top_radius))
        return name

    def tec(self, name, vertex, height_vector, major_axis, minor_axis, ratio):
        name = self._default_name_(name)
        is_string(name)
        is_truple(vertex)
        is_truple(height_vector)
        is_truple(major_axis)
        is_truple(minor_axis)
        is_ratio(ratio)
        
        vx, vy, vz = vertex
        hx, hy, hz = height_vector
        ax, ay, az = major_axis
        bx, by, bz = minor_axis
        self.script_string_list.append( 'in {} tec {} {} {} '\
                                       ' {} {} {}'\
                                       ' {} {} {}'\
                                       ' {} {} {}'\
                                       ' {}\n'.format(name,
                                                         vx, vy, vz,
                                                         hx, hy, hz,
                                                         ax, ay, az,
                                                         bx, by, bz,
                                                         ratio))
        return name

    def tgc(self, name, base, height,
            ellipse_base_radius_part_A, ellipse_base_radius_part_B,
            top_radius_scaling_A, top_radius_scaling_B):
        name = self._default_name_(name)
        is_string(name)
        is_truple(base)
        is_truple(height)
        is_truple(ellipse_base_radius_part_A)
        is_truple(ellipse_base_radius_part_B)
        is_number(top_radius_scaling_A)
        is_number(top_radius_scaling_B)
        
        basex, basey, basez = base
        hx, hy, hz = height
        ax, ay, az = ellipse_base_radius_part_A
        bx, by, bz = ellipse_base_radius_part_B
        self.script_string_list.append( 'in {} tgc {} {} {} '\
                                       ' {} {} {}'\
                                       ' {} {} {}'\
                                       ' {} {} {}'\
                                       ' {} {}\n'.format(name,
                                                         basex, basey, basez,
                                                         hx, hy, hz,
                                                         ax, ay, az,
                                                         bx, by, bz,
                                                         top_radius_scaling_A,
                                                         top_radius_scaling_B))
        return name

    def rhc(self, name, vertex, height_vector, bvector, half_width, apex_to_asymptote):
        name = self._default_name_(name)
        is_string(name)
        is_truple(vertex)
        is_truple(height_vector)
        is_truple(bvector)
        is_number(half_width)
        is_number(apex_to_asymptote)

        vx, vy, vz = vertex
        bx, by, bz = bvector
        hx, hy, hz = height_vector

        self.script_string_list.append( 'in {} rhc {} {} {} '\
                                       ' {} {} {}'\
                                       ' {} {} {}'\
                                       ' {} {}\n'.format(name,
                                                         vx, vy, vz,
                                                         hx, hy, hz,
                                                         bx, by, bz,
                                                         half_width, apex_to_asymptote))

    def rec(self, name, vertex, height_vector, major_axis, minor_axis):
        name = self._default_name_(name)
        is_string(name)
        is_truple(vertex)
        is_truple(height_vector)
        is_truple(major_axis)
        is_truple(minor_axis)

        vx, vy, vz = vertex
        ax, ay, az = major_axis
        bx, by, bz = minor_axis
        hx, hy, hz = height_vector
        self.script_string_list.append( 'in {} rec {} {} {} '\
                                       ' {} {} {}'\
                                       ' {} {} {}'\
                                       ' {} {} {}\n'.format(name,
                                                         vx, vy, vz,
                                                         hx, hy, hz,
                                                         ax, ay, az,
                                                         bx, by, bz))

    def rcc(self, name, base, height, radius):
        name = self._default_name_(name)
        is_string(name)
        is_truple(base)
        is_truple(height)
        is_number(radius)
        bx, by, bz = base
        hx, hy, hz = height
        self.script_string_list.append('in {} rcc {} {} {} {} {} {} {}\n'
                                       .format(name, bx, by, bz, hx, hy, hz,
                                               radius))
        return name

    def rpc(self, name, vertex, height_vector, base_vector, half_width):
        name = self._default_name_(name)
        is_string(name)
        is_truple(vertex)
        is_truple(height_vector)
        is_truple(base_vector)
        is_number(half_width)
        vx, vy, vz = vertex
        hx, hy, hz = height_vector
        bx, by, bz = base_vector
        self.script_string_list.append('in {} rpc {} {} {} {} {} {} {} {} {} {}\n'
                                       .format(name,
                                               vx,vy,vz,
                                               hx,hy,hz,
                                               bx,by,bz,
                                               half_width))
        return name

    def tor(self, name, vertex, normal, radius_1, radius_2):
        name = self._default_name_(name)
        is_string(name)
        is_truple(vertex)
        is_truple(normal)
        is_number(radius_1)
        is_number(radius_2)

        vx, vy, vz = vertex
        nx, ny, nz = normal

        self.script_string_list.append(  'in {} tor {} {} {}\
                                                    {} {} {}\
                                                    {} {}\n'.format(name,
                                                                    vx, vy, vz,
                                                                    nx, ny, nz,
                                                                    radius_1,
                                                                    radius_2))

        return name

    def box_by_opposite_corners(self, name, pmin, pmax):
        return self.rpp(self, name, pmin, pmax)

    def circular_cylinder(self, name, base_center_point, top_center_point, radius):
        return self.rcc(name, base_center_point, top_center_point, radius)

    def rpp(self, name, pmin, pmax):
        name = self._default_name_(name)
        is_string(name)
        is_truple(pmin)
        is_truple(pmax)
        minx,miny,minz = pmin
        maxx,maxy,maxz = pmax
        assert minx<=maxx, 'minx is not less than maxx! {} {} {}'.format(name, pmin, pmax)
        assert miny<=maxy, 'miny is not less than maxy! {} {} {}'.format(name, pmin, pmax)
        assert minz<=maxz, 'minz is not less than maxz! {} {} {}'.format(name, pmin, pmax)
        self.script_string_list.append( 'in {} rpp {} {} {} {} {} {}\n'.format(name,
                                                                     minx,maxx,
                                                                     miny,maxy,
                                                                     minz,maxz))
        return name

    def eto(self, name, vertex, normal_vector, radius, cvector, axis):
        name = self._default_name_(name)
        is_truple(vertex)
        is_truple(normal_vector)
        is_truple(cvector)
        is_number(radius)
        is_number(axis)

        vx, vy, vz = vertex
        nx, ny, nz = normal_vector
        cx, cy, cz = cvector

        self.script_string_list.append(  'in {} eto {} {} {}\
                                                    {} {} {}\
                                                    {}\
                                                    {} {} {}\
                                                    {}\n'.format(name,
                                                                vx, vy, vz,
                                                                nx, ny, nz,
                                                                radius,
                                                                cx, cy, cz,
                                                                axis))

        return name

    def epa(self, name, vertex, height_vector, avector, bscalar):
        name = self._default_name_(name)
        is_string(name)
        is_truple(height_vector)
        is_truple(avector)
        is_number(bscalar)

        vx, vy, vz = vertex
        hx, hy, hz = height_vector
        ax, ay, az = avector

        self.script_string_list.append( 'in {} epa {} {} {} '\
                                       ' {} {} {}'\
                                       ' {} {} {}'\
                                       ' {}\n'.format(name,
                                                         vx, vy, vz,
                                                         hx, hy, hz,
                                                         ax, ay, az,
                                                         bscalar))                
        return name

    def ehy(self, name, vertex, height_vector, avector, bscalar, apex_to_asymptote):
        name = self._default_name_(name)
        is_string(name)
        is_truple(height_vector)
        is_truple(avector)
        is_number(bscalar)
        is_number(apex_to_asymptote)

        vx, vy, vz = vertex
        hx, hy, hz = height_vector
        ax, ay, az = avector

        self.script_string_list.append( 'in {} ehy {} {} {} '\
                                       ' {} {} {}'\
                                       ' {} {} {}'\
                                       ' {} {}\n'.format(name,
                                                         vx, vy, vz,
                                                         hx, hy, hz,
                                                         ax, ay, az,
                                                         bscalar,
                                                         apex_to_asymptote))                
        return name

    def ell1(self, name, vertex, avector, radius):
        name = self._default_name_(name)
        is_string(name)
        is_truple(vertex)
        is_number(radius)

        vx, vy, vz = vertex
        ax, ay, az = avector

        self.script_string_list.append( 'in {} ell1 {} {} {}\
                                                    {} {} {}\
                                                    {}\n'.format(name,
                                                                vx, vy, vz,
                                                                ax, ay, az,
                                                                radius))

        return name

    def sph(self, name, vertex, radius):
        name = self._default_name_(name)
        is_truple(vertex)
        is_number(radius)
        
        x, y, z = vertex
        
        self.script_string_list.append( 'in {} sph {} {} {} {}'.format(name, x, y, z, radius))
        
        return name

    def part(self, name, vertex, height_vector, radius_at_v_end, radius_at_h_end):
        name = self._default_name_(name)
        is_string(name)
        is_truple(vertex)
        is_truple(height_vector)
        is_number(radius_at_v_end)
        is_number(radius_at_h_end)

        vx, vy, vz = vertex
        hx, hy, hz = height_vector

        self.script_string_list.append( 'in {} part {} {} {}\
                                                    {} {} {}\
                                                    {}\
                                                    {}\n'.format(name,
                                                                vx, vy, vz,
                                                                hx, hy, hz,
                                                                radius_at_v_end,
                                                                radius_at_h_end))

        return name

    def cuboid(self, corner_point, opposing_corner_point, name=None):
        return self.rpp(name, corner_point, opposing_corner_point)

    def arb4(self, name, v1, v2, v3, v4):
        is_string(name)
        name = self._default_name_(name)
        [is_truple(v) for v in [v1, v2, v3, v4]]
        myList = [v1, v2, v3, v4]
        mySet = set(myList)
        if len(mySet) != len(myList):
            self.repeated_error(name, "arb4", myList)
        vs = [str(v) for xyz in [v1, v2, v3, v4] for v in xyz]
        assert len(vs)==4*3
        self.script_string_list.append( 'in {} arb4 {}\n'.format(name,
                                                       ' '.join(vs)))
        return name

    def arb5(self, name, v1, v2, v3, v4, v5):
        is_string(name)
        name = self._default_name_(name)
        [is_truple(v) for v in [v1, v2, v3, v4, v5]]
        myList = [v1, v2, v3, v4, v5]
        mySet = set(myList)
        if len(mySet) != len(myList):
            self.repeated_error(name, "arb5", myList)
        vs = [str(v) for xyz in [v1, v2, v3, v4, v5] for v in xyz]
        assert len(vs)==5*3
        self.script_string_list.append( 'in {} arb5 {}\n'.format(name,
                                                       ' '.join(vs)))
        return name

    def arb6(self, name, v1, v2, v3, v4, v5, v6):
        is_string(name)
        name = self._default_name_(name)
        [is_truple(v) for v in [v1, v2, v3, v4, v5, v6]]
        myList = [v1, v2, v3, v4, v5, v6]
        mySet = set(myList)
        if len(mySet) != len(myList):
            self.repeated_error(name, "arb6", myList)
        vs = [str(v) for xyz in [v1, v2, v3, v4, v5, v6] for v in xyz]
        assert len(vs)==6*3
        self.script_string_list.append( 'in {} arb6 {}\n'.format(name,
                                                       ' '.join(vs)))
        return name

    def arb7(self, name, v1, v2, v3, v4, v5, v6, v7):
        is_string(name)
        name = self._default_name_(name)
        [is_truple(v) for v in [v1, v2, v3, v4, v5, v6, v7]]
        myList = [v1, v2, v3, v4, v5, v6, v7]
        mySet = set(myList)
        if len(mySet) != len(myList):
            self.repeated_error(name, "arb7", myList)
        vs = [str(v) for xyz in [v1, v2, v3, v4, v5, v6, v7] for v in xyz]
        assert len(vs)==7*3
        self.script_string_list.append( 'in {} arb7 {}\n'.format(name,
                                                       ' '.join(vs)))
        return name

    def arb8(self, name, points):
        name = self._default_name_(name)
        is_string(name)
        check_args = [is_truple(x) for x in points]
        assert(len(points)==8)
        points_list =  ' '.join([str(c) for c in chain.from_iterable(points)])
        
        #print 'arb8 points list: {}\n\n{}'.format(points, points_list)
        
        self.script_string_list.append( 'in {} arb8 {} \n'.format(name,
                                                        points_list
                                                        ))
        return name
                                                        
    def arbX(self, name, vList):
        #Detect which function to use, and feed in the parameters
        if len(vList) in range(4, 9):
            arbFunction = getattr(self, "arb" + str(len(vList)))
            
            #Execute it
            arbFunction(name, *vList)

    def half(self, name, normal, distance):
        name = self._default_name_(name)
        is_truple(normal)
        is_number(distance)

        nx, ny, nz = normal

        self.script_string_list.append(  'in {} half {} {} {} {}\n'.format(name,
                                                                        nx, ny, nz,
                                                                        distance))

        return name

        
    def cone(self, name, vertex, height_vector, base_radius, top_radius):
        return self.trc(name, vertex, height_vector, base_radius, top_radius)
        is_string(name)

    def cone_elliptical(self, name, vertex, height_vector, major_axis, minor_axis, ratio):
        return self.tec(name, vertex, height_vector, major_axis, minor_axis, ratio)
        is_string(name)

    def cone_general(self, name, vertex, height_vector, avector, bvector, cscalar, dscalar):
        return self.tgc(name, vertex, height_vector, avector, bvector, cscalar, dscalar)

    def cylinder(self, name, vertex, height_vector, radius):
        return self.rcc(name, vertex, height_vector, radius)

    def cylinder_elliptical(self, name, vertex, height_vector, major_axis, minor_axis):
        return self.rec(name, vertex, height_vector, major_axis, minor_axis)

    def cylinder_hyperbolic(self, name, vertex, height_vector, bvector, half_width, apex_to_asymptote):
        return self.rhc(name, vertex, height_vector, bvector, half_width, apex_to_asymptote)
        is_string(name)

    def cylinder_parabolic(self, name, vertex, height_vector, bvector, half_width):
        return self.rpc(name, vertex, height_vector, bvector, half_width)
        is_string(name)

    def Ellipsoid(self, name, vertex, avector, bvector, cvector):
        is_string(name)
        is_truple(vertex)
        is_truple(avector)
        is_truple(bvector)
        is_truple(cvector)
        vx, vy, vz = vertex
        ax, ay, az = avector
        bx, by, bz = bvector
        cx, cy, cz = cvector
        self.script_string_list.append('in {} ell {} {} {} {} {} {} {} {} {} {} {} {}\n'.format(name,
                                                                     vx, vy, vz,
                                                                     ax, ay, az,
                                                                     bx, by, bz,
                                                                     cx, cy, cz))
        return name

    def elliptical_hyperboloid(self, name, vertex, height_vector, avector, bscalar, apex_to_asymptote):
        return self.ehy(name, vertex, height_vector, avector, bscalar, apex_to_asymptote)

    def elliptical_paraboloid(self, name, vertex, height_vector, avector, bscalar):
        return self.epa(name, vertex, height_vector, avector, bscalar)

    def radius_ellipsoid(self, name, vertex, avector, radius):
        return self.ell1(name, vertex, avector, radius)

    def particle(self, name, vertex, height_vector, radius_at_v_end, radius_at_h_end):
        return self.part(name, vertex, height_vector, radius_at_v_end, radius_at_h_end)

    def Sphere(self, name, vertex, radius):
        return self.sph(name, vertex, radius)

    def torus(self, name, vertex, normal, radius_1, radius_2):
        return self.tor(name, vertex, normal, radius_1, radius_2)

    def torus_elliptical(self, name, vertex, normal_vector, radius, cvector, axis):
        return self.eto(name, vertex, normal_vector, radius, cvector, axis)
        
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
        
        self.script_string_list.append( 'in {} pipe {} {}\n'.format(name, num_points, ' '.join(points_str_list)))
        """ # this worked for me as a spring
        in spring.s pipe 10 -500 -500 250 10 200 500 -500 500 350 100 200 500 500 500 450 100 200 500 500 -500 550 100 200 500 -500 -500 650 100 200 500 -500 500 750 100 200 500 500 500 850 100 200 500 500 -500 950 100 200 500 -500 -500 1050 100 200 500 -500 500 1150 100 200 500 0 500 1200 100 200 500
        r s.r u spring.s
        """


class BrlCadModel(object):
    __metaclass__ = ABCMeta

    def __init__(self, brl_db):
        self.brl_db = brl_db
        self.name_tracker = brl_db.name_tracker
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
