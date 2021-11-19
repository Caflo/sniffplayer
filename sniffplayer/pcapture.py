import socket
import struct
import binascii
from scapy.all import *

class ThreadHandler:
    def __init__(self, pcap_path=None) -> None:
        self.thread_queue = list(dict())
        self.logger = logging.getLogger('pcapture')

    def start_sniffer(self, task, pcap_path=None):
#        self.logger.info(f"Starting sniffer with ID = {task.id}")

        def process(id: str, pcap_abs_filename: str):
            def process_packet(pkt):
                wrpcap(pcap_abs_filename, pkt, append=True)

            return process_packet
        if task['dynamic']:
            self.logger.info(f"Sniffing mode: dynamic")
            t = AsyncSniffer(iface=task['iface'], prn=process(task['_id'], pcap_path)) # appending pcap file live while sniffing
        else:
            self.logger.info(f"Sniffing mode: static")
            t = AsyncSniffer(iface=task['iface']) # silent
        entry = {
            "task_id": task['_id'],
            "thread": t
        }
        t.start()
        self.thread_queue.append(entry)
        return t.thread.ident
        
    def stop_sniffer(self, task):
#        self.logger.info(f"Stopping sniffer with ID = {sniffer_task.id}")
        entry = self.__get_thread_by_task_id(task)
        pkts = entry['thread'].stop()
        self.thread_queue.remove(entry)
        return pkts

    def schedule_sniffer(self, sniffer_id):
        raise NotImplementedError()

    def __get_thread_by_task_id(self, task):
        for entry in self.thread_queue:
            if entry['task_id'] == task['_id']:
                return entry

class ThreadHandler2:
    def __init__(self, pcap_path=None) -> None:
        self.thread_queue = list(dict())

    def start_sniffer(self, task, pcap_path=None):
        self.logger.info(f"Starting sniffer with ID = {task.id}")

        def process(id: int, pcap_abs_filename: str):
            def process_packet(pkt):
                wrpcap(pcap_abs_filename, pkt, append=True)

            return process_packet
        if task.dynamic:
            self.logger.info(f"Sniffing mode: dynamic")
            t = AsyncSniffer(iface=task.iface, prn=process(task.id, pcap_path)) # appending pcap file live while sniffing
        else:
            self.logger.info(f"Sniffing mode: static")
            t = AsyncSniffer(iface=task.iface) # silent
        entry = {
            "task_id": task.id,
            "thread": t
        }
        t.start()
        self.thread_queue.append(entry)
        return t.thread.ident
        
    def stop_sniffer(self, task):
        self.logger.info(f"Stopping sniffer with ID = {task.id}")
        entry = self.__get_thread_by_sniffer_id(task)
        pkts = entry['thread'].stop()
        self.thread_queue.remove(entry)
        return pkts

    def schedule_sniffer(self, sniffer_id):
        raise NotImplementedError()

    def __get_thread_by_sniffer_id(self, task):
        for entry in self.thread_queue:
            if entry['task_id'] == task.id:
                return entry