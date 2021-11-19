import flask
from flask import Flask, session, render_template
from sniffplayer import sniffer
import sniffplayer.log
from sniffplayer.utils import get_network_interfaces
import argparse
import sniffplayer.ctrl
import os
import logging
logger = logging.getLogger(__name__)

# TODO fix work_dir param
# TODO fix logger
# TODO fix parser below

app = Flask(__name__)
app.logger.info(f"Working directory: {app.config.get('work_dir')}")

working_dir = os.path.join(os.environ['TMP'], 'sniffplayer') # TODO set default passed as argument by script
config_fname = os.path.join(working_dir, 'sniffer_tasks.json')
sniff_ctrl = sniffplayer.ctrl.RequestHandlerServer(config_path=working_dir)
sniff_ctrl.read_sniffers()

@app.route("/")
@app.route("/dashboard") # default page
def dashboard():
    # HERE STATISTICS
    return render_template('dashboard.html')

@app.route("/ifaces")
def ifaces():
    ifaces = get_network_interfaces()
    return render_template('ifaces.html', interfaces=ifaces)

@app.route("/tasks", methods=['GET', 'POST'])
def tasks():
    ifaces = get_network_interfaces()
    if flask.request.method == 'GET':
        return render_template('tasks.html', sniffer_tasks=sniff_ctrl.sniffer_tasks, interfaces=ifaces)

@app.route("/add_task", methods=['POST'])
def add_task():
    iface = flask.request.form['iface']
    dynamic = flask.request.form["sniff_mode"] == 'dynamic'
    sniff_ctrl.add_sniffer(iface, dynamic)
    return flask.redirect("/tasks")
#    return render_template('tasks.html', sniffer_tasks=sniff_ctrl.sniffer_tasks, interfaces=ifaces)

@app.route("/remove_task", methods=['POST'])
def remove_task():
    sniffer_id = int(flask.request.form['id'])
    sniff_ctrl.remove_sniffer(sniffer_id)
    return flask.redirect("/tasks")

@app.route("/start_sniffer", methods=['POST'])
def start_sniffer():
    sniffer_id = int(flask.request.form['id'])
    sniff_ctrl.start_sniffer(sniffer_id)
    return flask.redirect("/tasks")

@app.route("/stop_sniffer", methods=['POST'])
def stop_sniffer():
    sniffer_id = int(flask.request.form['id'])
    sniff_ctrl.stop_sniffer(sniffer_id)
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