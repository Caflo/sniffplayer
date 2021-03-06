from abc import abstractclassmethod
from io import SEEK_SET
import os
import logging
import json
import bisect
import pickle
from re import A
from typing import final
from bson.objectid import ObjectId
from scapy.all import *
from .pcapture import ThreadHandler
from .sniffer import Schedule, SnifferTask
from .utils import get_network_interfaces, cleanup_files, is_debugger_present
from distutils.util import strtobool
import socket
import traceback

JSON_CONF_FILENAME = 'sniffer_tasks.json'
JSON_CONF_ABSFILENAME = ''
PCAP_FILE_ABSPATH = ''
BUFSIZE_MSG = 1024 
BUFSIZE_FILE = 4096 # 4 KB
INT_SIZE = 4 

class RequestHandlerServer:

    # TODO create class FileHelper that contains all functions that load, save and modify sniffers.json

    def __init__(self, config_path=None, config_filename=None, pcap_path=None) -> None:
        if config_path is None:
            self.conf_dir = os.environ['TMP']
        else:
            self.conf_dir = config_path
        if config_filename is None:
            self.conf_filename = JSON_CONF_FILENAME
        else:
            self.conf_filename = config_filename
        global JSON_CONF_ABSFILENAME 
        JSON_CONF_ABSFILENAME = os.path.join(self.conf_dir, self.conf_filename)
        # TODO add custom PCAP path setting
        if pcap_path is None:
            self.pcap_path = self.conf_dir
        else:
            self.pcap_path = pcap_path

        self.logger = logging.getLogger('sniffy_server')
        if not os.path.isfile(JSON_CONF_ABSFILENAME): # initialize json conf file
            self.create_conf_file()
            self.logger.info(f"Created configuration file : {JSON_CONF_ABSFILENAME}")
        else:
            self.logger.info(f"Found configuration file: {JSON_CONF_ABSFILENAME}")

        self.logger.info(f"Reading sniffers from JSON...")
        self.tasks = self.read_sniffers() 
        self.thread_handler = ThreadHandler()
    
    def init_server(self, host, port):
        # TODO try-except block
        self.logger.info(f"Init server... (host = {host}, port = {port})")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            s.listen()
            self.logger.info(f"Listening...")
            while True:
                try:
                    conn, addr = s.accept()
                    with conn:
                        self.logger.info(f"Connected with {addr}")
                        raw_data = conn.recv(1024)
                        data = pickle.loads(raw_data)
                        self.logger.info(f"Received data: {data}")
                        self.switch_action(data, conn) # switch requests here
                except KeyboardInterrupt:
                    self.logger.info(f"Received CTRL+C, exiting...")
                    s.close()
                    break
    
    def restart_server(self, conn):
        raise NotImplementedError()

    def stop_server(self, conn):
        self.logger.info(f"Stopping server...")
        sys.exit(0) 

    def add_sniffer(self, interface, dynamic):
        try:
            sniffer_task = SnifferTask(id=self.get_free_id(), iface=interface, dynamic=dynamic)
            bisect.insort(self.tasks, sniffer_task)
            self.save_sniffers()
            self.logger.info(f"Successfully added sniffer (id = {sniffer_task.id}), (iface = {sniffer_task.iface})")
        except Exception as ex:
            self.logger.info(f"Catched {type(ex).__name__}, continuing")
            message = traceback.format_exc()
            print(message)
        finally:
            self.logger.info(f"Closing client socket...")

    def remove_sniffer(self, sniffer_id):
        try:
            sniffer_task = self.get_sniffer_task_by_id(sniffer_id)
            i = self.tasks.index(sniffer_task)
            self.tasks.pop(i)
            self.save_sniffers()
            self.logger.info(f"Successfully removed sniffer (id = {sniffer_id - 1})")
        except Exception as ex:
            self.logger.info(f"Catched {type(ex).__name__}, continuing")
            message = traceback.format_exc()
            print(message)
        finally:
            self.logger.info(f"Closing client socket...")

    def clear_all_sniffers(self, conn): 
        try:
            self.__check_active_threads()
            for sniffer_task in self.tasks:
                if sniffer_task.active:
                    conn.send(b"Cannot do the requested action. Stop any active sniffer before cleaning up.")
                    return
            self.tasks.clear()
            self.save_sniffers()

            # also clean-up .pcap files
            cleanup_files(self.pcap_path, 'task_[0-9].pcap')
            self.logger.info(f"Cleaned-up .pcap files")

            self.logger.info(f"Successfully cleared all sniffers")
            conn.send(b"Cleared sniffers successfully.")
        except Exception as ex:
            self.logger.info(f"Catched {type(ex).__name__}, continuing")
            message = traceback.format_exc()
            print(message)
        finally:
            self.logger.info(f"Closing client socket...")
            conn.close()

    def start_sniffer(self, sniffer_id):
        try:
            sniffer_task = self.get_sniffer_task_by_id(sniffer_id)
            self.pcap_abs_filename = os.path.join(self.pcap_path, f"task_{sniffer_id}.pcap")
            thread_id = self.thread_handler.start_sniffer(sniffer_task, self.pcap_abs_filename) # TODO could return an error code
            sniffer_task.active = True
            sniffer_task.thread_id = thread_id
            self.__update_sniffer_task(sniffer_task)
            self.save_sniffers()
            self.logger.info(f"Updated status of sniffer with ID = {sniffer_id}")
        except Exception as ex:
            self.logger.info(f"Catched {type(ex).__name__}, continuing")
            message = traceback.format_exc()
            print(message)
            self.logger.info(f"Closing client socket...")
            
    def stop_sniffer(self, sniffer_id, cycling=False):
        try:
            sniffer_task = self.get_sniffer_task_by_id(sniffer_id)
            pkts = self.thread_handler.stop_sniffer(sniffer_task) # TODO could return an error code
            if not is_debugger_present():
                self.notifier.notify_sniffer_schedule(f'Sniffy', f'Successfully stopped sniffer {sniffer_id}') #TODO customize showing
            sniffer_task.active = False
            sniffer_task.thread_id = None
            self.__update_sniffer_task(sniffer_task)
            self.save_sniffers()
            self.pcap_abs_filename = os.path.join(self.pcap_path, f"task_{sniffer_id}.pcap")
            self.logger.info(f"Updated status of sniffer with ID = {sniffer_id}")
            self.logger.info(f"Pcap file saved: {self.pcap_abs_filename}")
            if not sniffer_task.dynamic: # if in static mode, write all captured packets once stopped
                wrpcap(self.pcap_abs_filename, pkts, append=True)
        except Exception as ex:
            self.logger.info(f"Catched {type(ex).__name__}, continuing")
            message = traceback.format_exc()
            print(message)
 
    def start_all(self, conn):
        self.__check_active_threads()
#        n = len(self.__get_inactive_sniffer_tasks()) # TODO test this function
        inast = self.__get_inactive_sniffer_tasks()
        
        try:
            val = struct.pack('!i', len(inast))
            conn.sendall(val)
            for st in inast:
                self.start_sniffer(st.id, conn)
        except Exception as ex:
            self.logger.info(f"Catched {type(ex).__name__}, continuing")
            message = traceback.format_exc()
            print(message)
        finally:
            self.logger.info(f"Closing client socket...")
            conn.close()
 

    def stop_all(self, conn):
        self.__check_active_threads()
#        n = len(self.__get_active_sniffer_tasks()) # TODO test this function
        ast = self.__get_active_sniffer_tasks()

        try:
            val = struct.pack('!i', len(ast))
            conn.sendall(val)
            for st in ast:
                self.stop_sniffer(st.id, conn)
        except Exception as ex:
            self.logger.info(f"Catched {type(ex).__name__}, continuing")
            message = traceback.format_exc()
            print(message)
        finally:
            self.logger.info(f"Closing client socket...")
            conn.close()
 
    def schedule_sniffer(self, sniffer_id, conn):
        # Example
#        self.start_sniffer()
#        time.sleep(20)
#        self.stop_sniffer()
        raise NotImplementedError()

    def get_all_sniffers(self, conn):
        try:
            self.__check_active_threads()
            sb = ""
            for sniffer_task in self.tasks:
                sb += f"ID: {sniffer_task.id}"
                sb += ' - ' + f"Iface: {sniffer_task.iface}"
                sb += ' - ' + f"Active: {sniffer_task.active}"
                if sniffer_task.active:
                    sb += ' (' + f"Proc ID: {sniffer_task.thread_id}" + ')'
                if sniffer_task.dynamic:
                    sb += ' (' + f"Sniff mode: dynamic" + ')'
                else:
                    sb += ' (' + f"Sniff mode: static" + ')'
                if hasattr(sniffer_task.schedule, 'mode'):
                    if sniffer_task.schedule.mode == 'interval':
                        sb += ' - ' + f"Schedule interval: {sniffer_task.schedule.interval} minutes" 
                sb += '\n'
            sb = sb[:-1]
#            if len(sb) > BUFSIZE_MSG: # TODO send chunked
            conn.sendall(sb.encode())
        except Exception as ex:
            self.logger.info(f"Catched {type(ex).__name__}, continuing")
            message = traceback.format_exc()
            print(message)
        finally:
            self.logger.info(f"Closing client socket...")
            conn.close()

    def get_active_sniffers(self, conn):
        try:
            self.__check_active_threads()
            sb = ""
            for sniffer in self.tasks:
                if sniffer.active:
                    sb += f"ID: {sniffer.id}"
                    sb += ' - ' + f"Iface: {sniffer.iface}"
                    sb += ' - ' + f"Active: {sniffer.active}"
                    sb += ' (' + f"Thread ID: {sniffer.thread_id}" + ')'
                    if sniffer.dynamic:
                        sb += ' (' + f"Sniff mode: dynamic" + ')'
                    else:
                        sb += ' (' + f"Sniff mode: static" + ')'
                    if hasattr(sniffer.schedule, 'mode'):
                        if sniffer.schedule.mode == 'interval':
                            sb += ' - ' + f"Schedule interval: {sniffer.schedule.interval} minutes" 
                sb += '\n'
            sb = sb[:-1]
            conn.sendall(sb.encode())
        except Exception as ex:
            self.logger.info(f"Catched {type(ex).__name__}, continuing")
            message = traceback.format_exc()
            print(message)
        finally:
            self.logger.info(f"Closing client socket...")
            conn.close()

    def list_network_interfaces(self, conn): # must be server-side since client could be also remote
        try:
            lst = get_network_interfaces()
            sb = ""
            for el in lst:
                sb += el 
                sb += '\n' 
            sb = sb[:-1]
            conn.sendall(sb.encode())
        except Exception as ex:
            self.logger.info(f"Catched {type(ex).__name__}, continuing")
            message = traceback.format_exc()
            print(message)
        finally:
            self.logger.info(f"Closing client socket...")
            conn.close()


    def dump_stats(self, sniffer_id, conn):
        # Static: get statistics from dumped pcap file after sniffer completed (requires stop)
        # Dynamic: get statistics on-demand while sniffer is running (requires pause and resuming):
        # can be done with prn=wrpcap('file.pcap', pkt, append=True) in the sniff function 

        raise NotImplementedError()




    def get_sniffer_task_by_id(self, sniffer_id):
        for st in self.tasks:
            if st.id == sniffer_id:
                return st

    def get_thread_by_sniffer_id(self, sniffer_id):
        for entry in self.s_threads:
            if entry['task_id'] == sniffer_id:
                return entry

    def get_free_id(self):
        prev_id = 0
        for sniffer_task in self.tasks:
            if sniffer_task.id-1 != prev_id:
                return prev_id + 1
            prev_id += 1
        return prev_id + 1

    def create_conf_file(self):
        with open(JSON_CONF_ABSFILENAME, 'w') as f:
            f.write('[]')

    def read_sniffers(self, db=None):
        tasks = db.tasks.find({})
        for t in tasks:
            self.tasks.append(t)

        if db:
            return tasks

    def save_sniffers(self):
        sniffer_tasksJSON = json.dumps(self.sniffer_tasks, default=lambda o: o.__dict__, sort_keys=True, indent=4)

        with open(JSON_CONF_ABSFILENAME, 'w') as f:
            f.write(sniffer_tasksJSON)
        
        self.logger.info(f"Successfully updated configuration file") 

    def __check_active_threads(self): # check to synchronize json file in case some thread crashed
        sync_flag = False
        self.logger.info(f"Checking active threads...") 
        for sniffer_task in self.sniffer_tasks:
            for entry in self.thread_handler.thread_queue:
                if entry['task_id'] == sniffer_task.id:
                    if entry['thread'].thread.is_alive() != sniffer_task.active: # synchronize
                        sniffer_task.active = entry['thread'].thread.is_alive()
                        self.logger.info(f"Synchronized sniffer with ID {sniffer_task.id} -> Active: {sniffer_task.active}...") 
                        sync_flag = True
                        break
        # save if 
        if sync_flag:
            self.save_sniffers()

    def __update_sniffer_task(self, sniffer_task):
        for st in self.sniffer_tasks:
            if st.id == sniffer_task.id:
                st = sniffer_task
    
    def __get_active_sniffer_tasks(self):
        active_sniffer_tasks = []
        self.logger.info(f"Getting active sniffer tasks...") 
        for sniffer_task in self.sniffer_tasks:
            for entry in self.thread_handler.thread_queue:
                if entry['task_id'] == sniffer_task.id and entry['thread'].thread.is_alive():
                    active_sniffer_tasks.append(sniffer_task)
        return active_sniffer_tasks

    def __get_inactive_sniffer_tasks(self):
        inactive_sniffer_tasks = []
        self.logger.info(f"Getting inactive sniffer tasks...") 
        for sniffer_task in self.sniffer_tasks:
            if sniffer_task.active == False:
                inactive_sniffer_tasks.append(sniffer_task)
        return inactive_sniffer_tasks


    def find_task_by_id(self, db, id):
        return db.tasks.find({"_id": ObjectId(id)})

    def switch_action(self, args, conn):
        if args.cmd == 'stop-server':
            self.stop_server(conn)
        if args.cmd == 'restart-server':
            self.restart_server(conn)
        if args.cmd == 'add':
            self.add_sniffer(args.interface, args.dynamic, conn)
        if args.cmd == 'remove':
            self.remove_sniffer(args.sniffer_id, conn)
        if args.cmd == 'clear-all':
            self.clear_all_sniffers(conn)
        if args.cmd == 'start':
            self.start_sniffer(args.sniffer_id, conn)
        if args.cmd == 'stop':
            self.stop_sniffer(args.sniffer_id, conn)
        if args.cmd == 'start-all':
            self.start_all(conn)
        if args.cmd == 'stop-all':
            self.stop_all(conn)
        if args.cmd == 'pause-all':
            self.pause_all(conn)
        if args.cmd == 'schedule':
            self.schedule_sniffer(conn)
        if args.cmd == 'get-all':
            self.get_all_sniffers(conn)
        if args.cmd == 'get-active':
            self.get_active_sniffers(conn)
        if args.cmd == 'list-ifaces':
            self.list_network_interfaces(conn)
        if args.cmd == 'dump-stats':
            self.dump_stats(conn)

        conn.close()