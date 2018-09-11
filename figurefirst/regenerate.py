import os
import dill as pickle
import numpy as np
import imp
try:
    from . import svg_to_axes
except:
    import svg_to_axes
from optparse import OptionParser
import types

def __is_mpl_call_saveable__(function_name):
    not_saveable = ['add_artist']
    if function_name in not_saveable:
        return False
    else:
        return True

def __save_fifidata__(data_filename, layout_key,
                        package, function, 
                        title, args_description, 
                        *args, **kwargs):
    if title == 'figurefirst.regenerate.replot':
        # this is a code word for note saving the data
        return

    # load
    if os.path.exists(data_filename):
        fifidata_file = open(data_filename, 'r')
        fifidata = pickle.load(fifidata_file)
        fifidata_file.close()
    else:
        fifidata = {}

    if layout_key not in fifidata.keys():
        fifidata[layout_key] = []

    # new figure action (e.g. mpl call)
    new_figure_action = {'package': package,
                         'function': function,
                         'title': title,
                         'args_description': args_description,
                         'args': args,
                         'kwargs': kwargs}

    # delete duplicate entries
    if 0:
        idx = []
        for i, action in enumerate(fifidata[layout_key]):
            if action['title'] == title:
                idx.append(i)
        if len(idx) > 0:
            for i in sorted(idx, reverse=True):
                del fifidata[layout_key][i]
        if len(idx) > 0:
            fifidata[layout_key].insert(np.min(idx), new_figure_action)
        else:
            fifidata[layout_key].append(new_figure_action)
    #
    
    fifidata[layout_key].append(new_figure_action)

    # save
    fifidata_file = open(data_filename, 'w')
    pickle.dump(fifidata, fifidata_file)
    fifidata_file.close()

def __load_custom_function__(package_name, function_name):
    if package_name == 'figurefirst':
        function_name = 'mpl_functions.'+function_name
    elif package_name == 'custom':
        if type(function_name) == types.FunctionType:
            return function_name
        else:
            package_name = function_name.split('.')[0]
            function_name = function_name[len(package_name)+1:]

    try:
        f, filename, description = imp.find_module(package_name)
    except:
        if '.' in package_name:
            raise ValueError('Use the basename for the module, and include all submodules in the function name. e.g. package_name: figurefirst, function_name: mpl_function.adjust_spines')
        else:
            raise ValueError('Could not find package: ' + package_name + ', maybe you need to install it?')
    package = imp.load_module(package_name, f, filename, description)
    
    nest = function_name.split('.')
    function = package
    for attr in nest:
        function = getattr(function, attr)

    return function

def replot(layout_filename, output_filename='template', data_filename=''):
    '''
    Regenerate a figure from saved data

    layout_filename - path and name for layout svg file
    output_filename - path and name for output svg file (default replaces the layout_filename with the output)
    data_filename - path and name for the data.pickle file that was generated by figurefirst with the raw
                    graphical source data and commands. Default of None will search for the data.pickle file
                    in the same directory using the default name. 
    '''
    if data_filename == '':
        data_filename = layout_filename.split('.svg')[0]+'_data.dillpickle'
    if output_filename == 'template':
        output_filename = layout_filename

    layout = svg_to_axes.FigureLayout(layout_filename)
    layout.make_mplfigures(hide=True)

    fifidata_file = open(data_filename, 'r')
    fifidata = pickle.load(fifidata_file)
    fifidata_file.close()

    for layout_key in fifidata.keys():
        for action in fifidata[layout_key]:
            ax = layout.axes[layout_key]

            info = ['figurefirst.regenerate.replot'] # trick function into skipping save
            package = action['package']
            function = action['function']
            args = action['args']
            kwargs = action['kwargs']

            if package == 'matplotlib' or package == 'figurefirst':
                ax.__getattr__('_'+function)(info, *args, **kwargs)
            else:
                ax.__getattr__('_custom')(info, function, *args, **kwargs)

    for figure in layout.figures.keys():
        try:
            layout.append_figure_to_layer(layout.figures[figure], figure, cleartarget=True)
        except:
            print('Skipping figure: '+figure)

    layout.write_svg(output_filename)

def load_data_file(filename):
    if filename[-4:] == '.svg':
        data_filename = filename.split('.svg')[0]+'_data.dillpickle'
        print('Automatically finding data file: ' + data_filename)
    else:
        data_filename = filename

    if os.path.exists(data_filename):
        f = open(data_filename, 'r')
        data = pickle.load(f)
        f.close()
    else:
        print('No data file: ' + data_filename)
        data = None

    return data

def save_data_file(data, filename):
    if filename[-4:] == '.svg':
        data_filename = filename.split('.svg')[0]+'_data.dillpickle'
        print('Automatically finding data file: ' + data_filename)
    else:
        data_filename = filename

    f = open(data_filename, 'w')
    data = pickle.dump(data, f)
    f.close()
    
def clear_fifidata(data_filename, layout_key):
    data = load_data_file(data_filename)
    if data is not None:
        if layout_key in data.keys():
            data[layout_key] = []
        save_data_file(data, data_filename)

def compress(filename, max_length=500):
    '''
    Attempt to downsize (via interpolation) large arguments. Very experimental. 
    Searches for arguments that are:
        1. A np.ndarray of length > max_length
        2. A list of np.ndarrays where each element of the list is identical in length, and that length > max_length
    '''
    fifidata = load_data_file(filename)

    for layout_key in fifidata.keys():
        for action in fifidata[layout_key]:
            args = action['args']
            new_args = []
            for i, arg in enumerate(args):
                new_arg = arg
                if type(arg) == np.ndarray:
                    if len(arg) > max_length:
                        xp = np.linspace(0, 1, len(arg))
                        x = np.linspace(0, 1, max_length)
                        new_arg = np.interp(x, xp, arg)
                elif type(arg) == list and len(arg) > 0:
                    if type(arg[0]) == np.ndarray:
                        lengths = [len(a) for a in arg]
                        if len(np.unique(lengths)) == 1: # all same length
                            if lengths[0] > max_length: # too long
                                new_arg = []
                                for a in arg:
                                    xp = np.linspace(0, 1, len(a))
                                    x = np.linspace(0, 1, max_length)
                                    n = np.interp(x, xp, a)
                                    new_arg.append(n)
                new_args.append(new_arg)
            action['args'] = new_args

    compressed_fifidatafile = filename.split('.dillpickle')[0] + '_compressed.dillpickle'
    fifidata_file = open(compressed_fifidatafile, 'w')
    pickle.dump(fifidata, fifidata_file)
    fifidata_file.close()

def __write_label__(file, label, heading, with_breaks=False):
    s = '#'*heading + ' ' + label
    file.writelines(s+'\n')
    if with_breaks:
        __write_break__(file)
        
def __write_break__(file, length=125):
    s = '#'*length
    file.writelines(s+'\n')
    
def __write_data__(file, data):
    '''
    Supports: 
        - single value
        - list
        - 1d array
        - 2d array
        - list of 1d arrays (or lists)
    '''
    
    # single value
    if not hasattr(data, '__iter__'):
        file.writelines(str(data)+'\n')
        return
    
    # list of arrays or lists
    if type(data) is list:
        if hasattr(data[0], '__iter__'):
            for i, data_i in enumerate(data):
                __write_label__(file, 'Number: ' + str(i+1), 6)
                __write_data__(file, data_i)
            return
              
    # 2d array
    if type(data) is np.ndarray:
        if len(data.shape) == 2:
            __write_label__(file, '2-dimensional array, lines = rows', 6)
            for i in range(data.shape[0]):
                __write_data__(file, data[i])
            return
    
    # list or 1d array
    if hasattr(data, '__iter__'):
        if not hasattr(data[0], '__iter__'):
            if type(data) == np.ndarray:
                data = data.tolist() # also converts to 32 bit, saves space
            s = ', '.join(map(str, data))
            file.writelines(s+'\n')
            
def __write_action__(file, action):
    if len(action['args_description']) == 0:
        return
    else:
        __write_label__(file, action['title'], 3)
        __write_break__(file, int(len(action['title'])*1.25))
        for i, arg_title in enumerate(action['args_description']):
            __write_label__(file, arg_title, 4)
            __write_data__(file, action['args'][i])
        __write_break__(file)
            
def __clean_layout_key__(layout_key):
    s = str(layout_key)
    s = s.replace("u'", "")
    s = s.replace(" ", "_")
    s = s.replace(",", "")
    s = s.replace("'", "")
    s = s.strip("()[]{}")
    return s

def write_to_csv(data_filename, figure, panel_id_to_layout_keys=None, header=''):
    '''
    figure - name, or number, for figure
    panel_id_to_layout_keys - dict of panel ids (e.g. 'a') that point to a list of associated layout_keys
    header - a string (you can include \n and # if you want multiple lines and markdown syntax)
    '''
    csv_filename = data_filename.split('.dillpickle')[0]+'_summary.md'
    file = open(csv_filename, 'w+')
    
    data = load_data_file(data_filename)
    if panel_id_to_layout_keys is None:
        panel_id_to_layout_keys = {}
        for layout_key in data.keys():
            panel_id = __clean_layout_key__(layout_key)
            panel_id_to_layout_keys[panel_id] = [layout_key]
            
    # write header
    __write_break__(file)
    figurefirst_header = '##### This file was automatically generated from source data using FigureFirst: http://flyranch.github.io/figurefirst/'
    file.writelines(header+'\n'+figurefirst_header+'\n')
    
    __write_break__(file)
    __write_label__(file, 'Figure: '+str(figure), 1, with_breaks=True)
    
    panel_id_names = panel_id_to_layout_keys.keys()
    panel_id_names.sort()
    for panel_id in panel_id_names:
        __write_label__(file, 'Panel: '+panel_id, 2, with_breaks=True)
        layout_keys = panel_id_to_layout_keys[panel_id]
        for layout_key in layout_keys:
            for action in data[layout_key]:
                __write_action__(file, action)
                
    file.close()

def list_layout_keys(data_filename):
    data = load_data_file(data_filename)
    for key in data.keys():
        print(key)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("--layout", type="str", dest="layout", default='',
                        help="path to layout svg")
    parser.add_option("--output", type="str", dest="output", default='template',
                        help="path to output svg")
    parser.add_option("--data", type="str", dest="data", default='',
                        help="path to fifi data file (a pickle file)")
    (options, args) = parser.parse_args()  
    
    replot(options.layout, options.output, options.data)