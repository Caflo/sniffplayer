import sys
import os
import shutil
from os import stat
from pathlib import Path
import pythoncom
import wmi
import platform
import psutil


def get_os_type():
    return platform.system() 

def is_debugger_present(): # testing purposes
    gettrace = getattr(sys, 'gettrace', lambda : None) 
    return gettrace() is not None

def get_network_interfaces():
    # TODO implement a cross-platform solution
    if get_os_type() == 'Windows':
        return get_network_interfaces_win()
    else:
        raise NotImplementedError()

def get_iface_info():
    return psutil.net_if_addrs() # dict

def get_network_info():
    return psutil.net_if_stats() 

def get_network_interfaces_win():
    pythoncom.CoInitialize() # https://blog.csdn.net/jacke121/article/details/105075784
    c = wmi.WMI()
    qry = "select Name from Win32_NetworkAdapter where NetEnabled=True and NetConnectionStatus=2"

    lst = [o.Name for o in c.query(qry)]
    pythoncom.CoUninitialize()
    return lst

def get_network_interfaces_unix():
    raise NotImplementedError()

def cleanup_files(path, regex):
    for p in Path(path).glob(regex):
        p.unlink()

def get_os_info():
    result = []
    result.append(f"Python: version: {sys.version}")
    result.append(f"Distribution: {platform.platform()}")
    result.append(f"Processor: {platform.machine()}")
    result.append(f"User: {platform.uname()}")
    result.append(f"version: {platform.version()}")
    return result

def get_file_creation_date(path):
    if platform.system() == 'Windows':
        return os.path.getctime(path)
    else:
        stat = os.stat(path)
        try:
            return stat.st_birthtime
        except AttributeError:
            return stat.st_mtime

def delete_folder_contents(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e)) 