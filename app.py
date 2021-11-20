import flask
import click
from datetime import datetime
from flask import Flask, session, render_template, jsonify
from flask_pymongo import PyMongo
from scapy.utils import wrpcap
from werkzeug.utils import send_file, send_from_directory
from sniffplayer import sniffer
from sniffplayer.dbhandler import TaskDBHandler
import sniffplayer.log
from sniffplayer.pcapture import ThreadHandler 
from sniffplayer.utils import delete_folder_contents, get_file_creation_date, get_iface_info, get_network_info, get_network_interfaces, get_os_info
import argparse
import sniffplayer.ctrl
import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler

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

# eventually sync if thread crashed
#def sync():
#    tasks = task_handler.read_all()
#    for t in tasks:
#        entry = thread_handler.get_thread_by_task_id(t['_id'])
#        if t['active']:
#            if entry is not None: # check if it's alive in the thread queue
#                if not entry['thread'].thread.is_alive(): # sync
#                    t['active'] = False
#                    t['thread_id'] = None
#            else: # not present in thread queue, sync back to active: 'false'
#                t['active'] = False
#                t['thread_id'] = None
#        # eventually update
#        task_handler.update(t)
#
#sched = BackgroundScheduler(daemon=True)
#sched.add_job(sync,'interval',seconds=60)
#sched.start()

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

@app.route("/osinfo")
def ifaces():
    iface_info = get_iface_info()
    os_info = get_os_info()
    return render_template('osinfo.html', interfaces=iface_info, os_info=os_info)

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

@app.route("/start_all", methods=['POST'])
def start_all():
    id_list = flask.request.form['id'].strip(',') # all ID's separated by comma`
    for id in (0, id_list):
        task = task_handler.read_by_id(id)
        pcap_abs_filename = os.path.join(pcap_path, f"task_{id}.pcap")
        thread_id = thread_handler.start_sniffer(task, pcap_abs_filename) 
        task['active'] = True
        task['thread_id'] = thread_id
        task_handler.update(task)
    return flask.redirect("/tasks")

@app.route("/stop_all", methods=['POST'])
def stop_all():
    id_list = flask.request.form['id'].strip(',') # all ID's separated by comma`
    for id in (0, id_list):
        task = task_handler.read_by_id(id)
        pkts = thread_handler.stop_sniffer(task)
        if not task['dynamic']: # if in static mode, write all captured packets once stopped
            pcap_abs_filename = os.path.join(pcap_path, f"task_{id}.pcap")
            wrpcap(pcap_abs_filename, pkts, append=True)
        task['active'] = False
        task['thread_id'] = None
        task_handler.update(task)
    return flask.redirect("/tasks")

@app.route("/start_task", methods=['POST'])
def start_task():
    id = flask.request.form['id']
    task = task_handler.read_by_id(id)
    
    pcap_abs_filename = os.path.join(pcap_path, f"task_{id}.pcap")
    thread_id = thread_handler.start_sniffer(task, pcap_abs_filename) 
    task['active'] = True
    task['thread_id'] = thread_id
    task_handler.update(task)
    return flask.redirect("/tasks")

@app.route("/stop_task", methods=['POST'])
def stop_task():
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


@app.route("/files", methods=['GET','POST'])
def files():
    files = os.listdir(pcap_path)
    dates = []
    sizes = []
    for f in files:
        creation_date = datetime.fromtimestamp(get_file_creation_date(os.path.join(pcap_path, f)))
        size = "{:.2f}".format(os.path.getsize(os.path.join(pcap_path, f)) / 1024)
        dates.append(creation_date)
        sizes.append(size)
    return render_template("files.html", pcap_path=pcap_path, files=files, dates=dates, sizes=sizes)


@app.route("/files/<path:filename>", methods=['GET', 'POST'])
def download(filename):
    return send_from_directory(
        os.path.abspath(pcap_path),
        filename,
        as_attachment=True,
        environ=flask.request.environ
    )

@app.route("/clear_dir", methods=['GET','POST'])
def clear_dir():
    delete_folder_contents(pcap_path)
    return flask.redirect("/files")
    


@app.route("/schedule", methods=['POST'])
def schedule():
    raise NotImplementedError()

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