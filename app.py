import flask
import click
from flask import Flask, session, render_template, jsonify
import json
from flask_pymongo import PyMongo
from pymongo.write_concern import DEFAULT_WRITE_CONCERN
from scapy.utils import wrpcap
from sniffplayer import sniffer
from sniffplayer.dbhandler import TaskDBHandler
import sniffplayer.log
from sniffplayer.pcapture import ThreadHandler, ThreadHandler2
from sniffplayer.utils import get_network_interfaces
import argparse
import sniffplayer.ctrl
import os
import logging
logger = logging.getLogger(__name__)

DEFAULT_WORK_DIR = 'sniffplayer'
DBNAME = 'sniffplayerdb'

# TODO fix work_dir param
# TODO fix logger
# TODO fix parser below

app = Flask(__name__)
app.logger.info(f"Working directory: {app.config.get('work_dir')}")

working_dir = os.path.join(os.environ['TMP'], DEFAULT_WORK_DIR) # TODO set default passed as argument by script
config_fname = os.path.join(working_dir, 'sniffer_tasks.json')
pcap_path = os.path.join(working_dir, 'pcaps/')
#sniff_ctrl = sniffplayer.ctrl.RequestHandlerServer(config_path=working_dir)

# set-up DB
mongodb_client = PyMongo(app, uri="mongodb://localhost:27017/sniffplayerdb")
db = mongodb_client.db

task_handler = TaskDBHandler(db)
thread_handler = ThreadHandler()

# TODO read working dir from config collection of mongoDB


@app.cli.command("set-config")
@click.argument("path")
def init_config(path):
    # Here set many ENVs: DB path, dbname, task_collection_name, config_collection_name, default_filename, default_work_dir
    os.environ['SNIFFPLAYERDB_PATH'] = path
    print("path set")
    return 
 
@app.route("/")
@app.route("/dashboard") # default page
def dashboard():
    # HERE STATISTICS
#    tasks = sniff_ctrl.read_sniffers(db)
    return render_template('dashboard.html')

@app.route("/ifaces")
def ifaces():
    ifaces = get_network_interfaces()
    return render_template('ifaces.html', interfaces=ifaces)

@app.route("/tasks", methods=['GET', 'POST'])
def tasks():
    tasks = task_handler.read_all()
    ifaces = get_network_interfaces()
    if flask.request.method == 'GET':
        return render_template('tasks.html', tasks=tasks, interfaces=ifaces)

@app.route("/add_task", methods=['POST'])
def add_task():
    iface = flask.request.form['iface']
    dynamic = flask.request.form["sniff_mode"] == 'dynamic'
    task = sniffer.SnifferTask(iface=iface, active=False, dynamic=dynamic, schedule=None)
    task_handler.create(task)
    return flask.redirect("/tasks")

@app.route("/remove_task", methods=['POST'])
def remove_task():
    sniffer_id = flask.request.form['id']
    task_handler.delete(sniffer_id)
    return flask.redirect("/tasks")

@app.route("/start_sniffer", methods=['POST'])
def start_sniffer():
    id = flask.request.form['id']
    task = task_handler.read_by_id(id)
    
    pcap_abs_filename = os.path.join(pcap_path, f"task_{id}.pcap")
    thread_id = thread_handler.start_sniffer(task, pcap_abs_filename) 
    task['active'] = True
    task['thread_id'] = thread_id
    task_handler.update(task)
#    self.__update_sniffer_task(sniffer_task)
#    self.save_sniffers()

    return flask.redirect("/tasks")

@app.route("/stop_sniffer", methods=['POST'])
def stop_sniffer():
    id = flask.request.form['id']
    task = task_handler.read_by_id(id)
    pkts = thread_handler.stop_sniffer(task)
    if not task['dynamic']: # if in static mode, write all captured packets once stopped
        pcap_abs_filename = os.path.join(pcap_path, f"task_{id}.pcap")
        wrpcap(pcap_abs_filename, pkts, append=True)
    task['active'] = False
    task['thread_id'] = None
    task_handler.update(task)
    return flask.redirect("/tasks")

   

if __name__ == "__main__":

    # Parse optional arguments
#    description = ""
#    with open("README.md", 'r') as f:
#        description = f.readline() 
#    parser = argparse.ArgumentParser(description=description)
#    default_work_dir = os.environ['TMP']
#    parser.add_argument('--config-path', dest='work_dir', action='store', default=default_work_dir, type=str, help='Set working directory.') 
#    args = parser.parse_args()
    
#    app.config['work_dir'] = args.work_dir
    app.run(debug=True)