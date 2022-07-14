#!/usr/bin/env python
# coding: utf-8


##### Module import

import os
import glob
import sys
import numpy as np
import h5py
import datetime
import argparse


##### Argument parameters

### Arguement parse
arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('input',  type=str, help='Path of input image file or folder.')
arg_parser.add_argument('format', type=str, help='Output file format.')
arg_parser.add_argument('-o', '--output', type=str, default='./', help='Path of output folder, default same as this script.')
### Arguement data
input_path    = arg_parser.parse_args().input
convert_to    = arg_parser.parse_args().format
output_folder = arg_parser.parse_args().output


##### Common function

def extension_filter(path_list, target_ext_list):
    #filtered_path = []
    ext_di = dict(zip(target_ext_list, [[] for x in target_ext_list]))
    for i in range(len(path_list)):
        name, ext = os.path.splitext(path_list[i])
        trimmed_ext = ext.strip('.').lower()
        if trimmed_ext in target_ext_list:
            #filtered_path.append(path_list[i])
            ext_di[trimmed_ext].append(path_list[i])
    return ext_di

def time_tag(input_dt, type=1):
    if type == 2:
        tag = input_dt.strftime('%Y/%m/%d %H:%M:%S')
    else:
        tag = input_dt.strftime('%y%m%d_%H%M')
    return tag


##### Class BRCCIC (BRC Common Image Converter)

class BRCCIC:
    
    def __init__(self, path, output_format):
        self.path = path
        self.input_fn    = os.path.basename(path)
        self.input_name, pre_ext = os.path.splitext(self.input_fn)
        self.input_ext   = pre_ext.strip('.').lower()
        self.output_ext  = output_format.lower()
        self.output_name = self.input_name
        self.output_fn   = self.output_name + '.' + self.output_ext
    
    def bi_str_array_to_str(self, bi_str_ar_1d):
        return b''.join(list(bi_str_ar_1d)).decode()

    def ims_to_arr(self, path_ims):
        ### Metadata dictionary
        ims_metadata_di = {'X': 'lattice_x', 'Y': 'lattice_y' , 'Z': 'lattice_z',
                           'ExtMin0': 'bbox_x_min', 'ExtMax0': 'bbox_x_max',
                           'ExtMin1': 'bbox_y_min', 'ExtMax1': 'bbox_y_max',
                           'ExtMin2': 'bbox_z_min', 'ExtMax2': 'bbox_z_max'}
        ### Read file
        readfile = h5py.File(path_ims, 'r')
        ### Extract metadata
        metadata_di = {}
        ims_datainfo = readfile['DataSetInfo']['Image'].attrs
        for k in ims_metadata_di.keys():
            try:
                metadata_di[ims_metadata_di[k]] = int(self.bi_str_array_to_str(ims_datainfo[k]))
            except ValueError:
                metadata_di[ims_metadata_di[k]] = float(self.bi_str_array_to_str(ims_datainfo[k]))
        ### Convert image
        chunk_ar = readfile['DataSet'][f'ResolutionLevel 0']['TimePoint 0']['Channel 0']['Data'][()]
        img_ar = chunk_ar[:metadata_di['lattice_z'], :metadata_di['lattice_y'], :metadata_di['lattice_x']]
        return img_ar, metadata_di

    def npy_to_arr(self, path_npy):
        ### Read file
        img_ar = np.load(path_npy)
        ### Generate dummy metadata
        metadata_di = {}
        metadata_di['bbox_x_max'] = np.shape(img_ar)[2] - 1
        metadata_di['bbox_x_min'] = 0
        metadata_di['bbox_y_max'] = np.shape(img_ar)[1] - 1
        metadata_di['bbox_y_min'] = 0
        metadata_di['bbox_z_max'] = np.shape(img_ar)[0] - 1
        metadata_di['bbox_z_min'] = 0
        metadata_di['lattice_x'] = np.shape(img_ar)[2]
        metadata_di['lattice_y'] = np.shape(img_ar)[1]
        metadata_di['lattice_z'] = np.shape(img_ar)[0]
        return img_ar, metadata_di

    def am_to_arr(self, path_am):
        ### Read file
        readfile = open(path_am).read()
        ### Extract metadata
        metadata_di = {}
        flag_lattice = False
        flag_bbox    = False
        for line in readfile.split('\n'):
            if 'define Lattice' in line:
                lattice_xyz = list(map(int, line.split('define Lattice')[-1].strip(', ').split(' ')))
                metadata_di['lattice_x'], metadata_di['lattice_y'], metadata_di['lattice_z'] = lattice_xyz
                flag_lattice = True
            if 'BoundingBox' in line:
                try:
                    bbox_xxyyzz = list(map(int, line.split('BoundingBox')[-1].strip(', ').split()))
                except ValueError:
                    bbox_xxyyzz = list(map(float, line.split('BoundingBox')[-1].strip(', ').split()))
                metadata_di['bbox_x_min'], metadata_di['bbox_x_max'], metadata_di['bbox_y_min'] , metadata_di['bbox_y_max'] , metadata_di['bbox_z_min'] , metadata_di['bbox_z_max'] = bbox_xxyyzz
                flag_bbox = True
            if flag_lattice and flag_bbox:
                break
        ### Convert image
        temp_img_li = readfile.split('@1')[-1].strip().split('\n')
        try:
            img_ar = np.array(list(map(int, temp_img_li))).reshape((metadata_di['lattice_z'], metadata_di['lattice_y'], metadata_di['lattice_x']))
        except ValueError:
            img_ar = np.array(list(map(float, temp_img_li))).reshape((metadata_di['lattice_z'], metadata_di['lattice_y'], metadata_di['lattice_x']))
        return img_ar, metadata_di
    
    def arr_to_npy(self, path_output):
        np.save(path_output, self.img_ar)
        
    def judge_am_datatype(self):
        self.ar_min = self.img_ar.min()
        self.ar_max = self.img_ar.max()
        if self.ar_min >= 0 and self.ar_max <= 65535:
            self.am_data_type = 'ushort'
        elif -32768 <= self.ar_min and self.ar_max <= 32767:
            self.am_data_type = 'short'
        else:
            self.am_data_type = 'float'
        return self.am_data_type
        
    def arr_to_am(self, path_output):
        self.am_seed = '# AmiraMesh 3D ASCII 2.0\n\ndefine Lattice :lattice_x: :lattice_y: :lattice_z:\n\nParameters {\n    Colormap "volrenGreen.col",\n    BoundingBox  :bbox_x_min: :bbox_x_max: :bbox_y_min: :bbox_y_max: :bbox_z_min: :bbox_z_max:,\n    CoordType "uniform"\n}\n\nLattice { :am_data_type: Data } @1\n\n# Data section follows\n@1\n:img_data_str:'
        img_data_str = '\n'.join(list(map(str, self.img_ar.reshape(-1).tolist())))
        #am_data_type = judge_am_datatype(img_ar)
        new_am_header = self.am_seed
        for key in self.metadata_di.keys():
            new_am_header = new_am_header.replace(f':{key}:', str(self.metadata_di[key]))
        new_am_header = new_am_header.replace(':am_data_type:', self.judge_am_datatype())
        output_am = new_am_header.replace(':img_data_str:', img_data_str)
        with open(path_output, 'w') as am_txt:
            am_txt.write(output_am)
            am_txt.close()
        
    def extract(self):
        if self.input_ext == 'ims':
            self.img_ar, self.metadata_di = self.ims_to_arr(self.path)
        elif self.input_ext == 'npy':
            self.img_ar, self.metadata_di = self.npy_to_arr(self.path)
        elif self.input_ext == 'am':
            self.img_ar, self.metadata_di = self.am_to_arr(self.path)
        else:
            sys.exit(f'Error: False input extension "{self.ext}"')
        self.dtype = str(self.img_ar.dtype)
        #return self.img_ar, self.metadata_di
    
    def convert(self, path_output_folder):
        self.path_output = os.path.join(path_output_folder, self.output_fn)
        duplicate = 0
        while os.path.exists(self.path_output):
            duplicate += 1
            self.path_output = os.path.join(path_output_folder, self.output_name + f'_{duplicate}.' + self.output_ext)
        if self.output_ext == 'npy':
            self.arr_to_npy(self.path_output)
        elif self.output_ext == 'am':
            self.arr_to_am(self.path_output)
        else:
            sys.exit(f'Error: False output extension "{self.ext}"')


##### Input file path pre-process

### Supportted extension
input_file_extension = ['npy', 'ims', 'am']
### Absolute path
input_path    = os.path.abspath(input_path)
output_folder = os.path.abspath(output_folder)
### File/folder judge and some extras
if os.path.exists(input_path):
    if os.path.isfile(input_path):
        file_path_li          = [input_path]
    elif os.path.isdir(input_path):
        file_path_li          = glob.glob(os.path.join(input_path, '*'))
else:
    sys.exit(f'Error: False input path "{input_path}"')
### Generate output folder if no exists
if not os.path.exists(output_folder):
    os.makedirs(output_folder)
### Filtering none-support files
img_path_di = extension_filter(file_path_li, input_file_extension)
### Info print
print(f'[+] Path of input: "{input_path}"')
print(f'[+] Output folder: "{output_folder}"')
print( '[+] Detected image file(s):')
for t in input_file_extension:
    if len(img_path_di[t]) != 0:
        print(f'    [-] {len(img_path_di[t])} {t} file(s)')
print(f'[+] Convert to: {convert_to} ')


##### Main flow: Load, extract, and convert

print('[+] Start conversion...')
for key in img_path_di.keys():
    path_li = img_path_di[key]
    if len(path_li) == 0:
        continue
    print(f'    [+] {len(path_li)} {key} file(s)')
    disp_period = 10 ** (len(str(len(path_li)))-2) if (len(str(len(path_li)))-2) > 0 else 1
    for i in range(len(path_li)):
        path_file = path_li[i]
        file = BRCCIC(path_file, convert_to)
        file.extract()
        file.convert(output_folder)
        if (i+1) % disp_period == 0:
            print(f'        [-] {time_tag(datetime.datetime.now())} | {i+1} file(s) done.')
    print(f'        [-] {time_tag(datetime.datetime.now())} | all {i+1} {key} file converted.')

print('[+] Conversion finished')
