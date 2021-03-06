from platform import system
from re import T
import flask
import click
from datetime import date, datetime, timedelta
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
import os
import time
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
pcap_path = os.path.join(working_dir, 'pcaps')
#sniff_ctrl = sniffplayer.ctrl.RequestHandlerServer(config_path=working_dir)

# set-up DB
mongodb_client = PyMongo(app, uri="mongodb://localhost:27017/sniffplayerdb")
db = mongodb_client.db

task_handler = TaskDBHandler(db)
thread_handler = ThreadHandler()

sched = BackgroundScheduler(daemon=True)
sched.start()

# TODO read working dir from config collection of mongoDB

# eventually sync if thread crashed #TODO fix and make it periodic and  ajax
def sync():
    print("Sync...")
    tasks = task_handler.read_all()
    for t in tasks:
        entry = thread_handler.get_thread_by_task(t)
        if t['active']:
            if entry is not None: # check if it's alive in the thread queue
                if not entry['thread'].thread.is_alive(): # sync
                    t['active'] = False
                    t['thread_id'] = None
            else: # not present in thread queue, sync back to active: 'false'
                t['active'] = False
                t['thread_id'] = None
        # eventually update
        task_handler.update(t)

sync()

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
    filter = {
        "active": True
    }
    tasks = task_handler.read_all(filter=filter)
    return render_template('dashboard.html', tasks=tasks)

@app.route("/osinfo")
def ifaces():
    iface_info = get_iface_info()
    os_info = get_os_info()
    return render_template('osinfo.html', interfaces=iface_info, os_info=os_info)

@app.route("/tasks", methods=['GET', 'POST'])
def tasks():
    tasks = task_handler.read_all()
    ifaces = list(get_iface_info().keys())
    if flask.request.method == 'GET':
        return render_template('tasks.html', tasks=tasks, interfaces=ifaces)

@app.route("/add_task", methods=['POST'])
def add_task():
    iface = flask.request.form['iface']
    dynamic = flask.request.form["sniff_mode"] == 'dynamic'
    sched_from = None
    sched_to = None
    if 'schedule_from' in flask.request.form:
#        sched_from = datetime.strptime(flask.request.form['schedule_from'], '%Y-%m-%dT%H:%M')
        sched_from = flask.request.form['schedule_from']
    if 'schedule_to' in flask.request.form:
        sched_to = flask.request.form['schedule_to']
    schedule = sniffer.Schedule(sched_from=sched_from, sched_to=sched_to) 
    task = sniffer.SnifferTask(iface=iface, active=False, dynamic=dynamic, schedule=schedule)
    task_handler.create(task)
    return flask.redirect("/tasks")

@app.route("/remove_task", methods=['POST'])
def remove_task():
#    sync_flag = False
    sniffer_id = flask.request.form['id']
    task_handler.delete(sniffer_id)
#    sync_flag = True
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
def start_task(scheduled=False, t_id=None):
    if not scheduled:
        id = flask.request.form['id']
    else:
        id = t_id
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

def schedule_from(task): # handle starting
#    sched.add_job(start_task, 'date', run_date=datetime.now()+timedelta(seconds=10), args=[True, task['_id']])
    sched.add_job(start_task, 'date', run_date=datetime.strptime(task['schedule']['_from'], '%Y-%m-%dT%H:%M'), args=[True, task['_id']])

#def schedule_to(task): # handle stopping
#    id = flask.request.form['id']
#    task = task_handler.read_by_id(id)
#
#    sched.add_job(thread_handler.stop_sniffer,'interval',seconds=4)
#    sched.start()
#    pkts = thread_handler.stop_sniffer(task)
#
#    if not task['dynamic']: # if in static mode, write all captured packets once stopped
#        pcap_abs_filename = os.path.join(pcap_path, f"task_{id}.pcap")
#        wrpcap(pcap_abs_filename, pkts, append=True)
#    task['active'] = False
#    task['thread_id'] = None
#    task_handler.update(task)

@app.route("/schedule_task", methods=['POST'])
def schedule_task():
    id = flask.request.form['id']
    task = task_handler.read_by_id(id)
    if task['schedule']['_from']:
        schedule_from(task)
#    if task['schedule']['_from']:
#        schedule_to(task)
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