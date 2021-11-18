import sys
from os import stat
from pathlib import Path
import pythoncom
import wmi

def is_debugger_present(): # testing purposes
    gettrace = getattr(sys, 'gettrace', lambda : None) 
    return gettrace() is not None

def get_network_interfaces():
    # TODO implement a cross-platform solution
    return get_network_interfaces_win()

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