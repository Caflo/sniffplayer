from flask import Flask, session, render_template
import sniffplayer.log
from sniffplayer.utils import get_network_interfaces
import argparse
import sniffplayer.ctrl
import os
import logging
logger = logging.getLogger(__name__)

# TODO fix work_dir param

app = Flask(__name__)
app.logger.info(f"Working directory: {app.config.get('work_dir')}")

working_dir = os.path.join(os.environ['TMP'], 'sniffplayer') # TODO set default passed as argument by script
config_fname = os.path.join(working_dir, 'sniffer_tasks.json')
rhs = sniffplayer.ctrl.RequestHandlerServer(config_path=working_dir)
sniffer_tasks = rhs.read_sniffers()


@app.route("/")
@app.route("/dashboard")
def dashboard():
    # HERE STATISTICS
    with open(config_fname, 'r') as f:
        res = f.read()
        f.close()
    return res

@app.route("/ifaces")
def ifaces():
    ifaces = get_network_interfaces()
    return render_template('ifaces.html', interfaces=ifaces)

@app.route("/tasks")
def tasks():
    return render_template('tasks.html', sniffer_tasks=sniffer_tasks)


if __name__ == "__main__":

    # Parse optional arguments
    # TODO fix parser
#    description = ""
#    with open("README.md", 'r') as f:
#        description = f.readline() 
#    parser = argparse.ArgumentParser(description=description)
#    default_work_dir = os.environ['TMP']
#    parser.add_argument('--config-path', dest='work_dir', action='store', default=default_work_dir, type=str, help='Set working directory.') 
#    args = parser.parse_args()
    
#    app.config['work_dir'] = args.work_dir
    app.run(debug=True)