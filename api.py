import os
import subprocess

from flask import Flask, request
from flask_restful import Resource, Api

from log import create_logger

app = Flask(__name__)
api = Api(app)

class Home(Resource):
    def get(self):
        ps_aux = subprocess.run(['ps', 'aux'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        process = [line for line in ps_aux.stdout.decode('utf-8').split("\n") if 'python3 -m main run' in line]
        count = len(process)
        if count > 0:
            return {'message': 'Welcome to the ytmusicdl API!', 'status': 'running', 'pid': process[0].split()[1]}
        else:
            return {'message': 'Welcome to the ytmusicdl API!', 'status': 'stopped'}
    
api.add_resource(Home, '/')

class Log(Resource):
    def get(self):
        # Read the log file
        try:
            log = [line.strip() for line in open('app.log', 'r').readlines()]
        except FileNotFoundError:
            return {'error': 'File not found'}, 404
        else:
            # Return the last 20 lines of the log file
            try:
                if request.args.get('last') == 'all':
                    return (log), 200
                if request.args.get('last').isnumeric() and int(request.args.get('last')) > 0:
                    return (log[-(int(request.args.get('last'))):]), 200
            except:
                pass
            if len(log) < 20:
                return (log), 200
            return (log[-20:]), 200

api.add_resource(Log, '/log')

class Error(Resource):
    def get(self):
        # Read the log file
        try:
            log = [line.strip() for line in open('error.log', 'r').readlines()]
        except FileNotFoundError:
            return {'error': 'File not found'}, 404
        else:
            # Return the last 20 lines of the log file
            try:
                if request.args.get('last') == 'all':
                    return (log), 200
                if request.args.get('last').isnumeric() and int(request.args.get('last')) > 0:
                    return (log[-(int(request.args.get('last'))):]), 200
            except:
                pass
            if len(log) < 20:
                return (log), 200
            return (log[-20:]), 200
        
api.add_resource(Error, '/error')


class Start(Resource):
    def post(self):
        urls = request.json['urls']
        if len(urls) > 0:
            with open('lists.txt', 'w') as f:
                f.write('\n'.join(urls))
            ps_aux = subprocess.run(['ps', 'aux'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            count = len([line for line in ps_aux.stdout.decode('utf-8').split("\n") if 'python3 -m main run' in line])
            if count > 0:
                return {'status': 'Already running'}, 200
            else:
                os.remove('app.log')
                os.remove('error.log')
                _ = subprocess.Popen(['python3', '-m', 'main', 'run'])
                return {'status': 'OK'}, 200
        else:
            return {'status': 'No URLs provided'}, 400
        
api.add_resource(Start, '/start')

class Stop(Resource):
    def get(self):
        ps_aux = subprocess.run(['ps', 'aux'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        process = [line for line in ps_aux.stdout.decode('utf-8').split("\n") if 'python3 -m main run' in line]
        count = len(process)
        if count > 0:
            log = create_logger("api")
            pid = str(process[0].split()[1])
            _ = subprocess.Popen(['kill', pid])
            log.warning(f'Download process with PID {pid} stopped by user command')
            return {'status': f'Download process with PID {pid} stopped'}, 200
        else:
            return {'status': 'Not running'}, 200
        
api.add_resource(Stop, '/stop')
    
if __name__ == '__main__':
    app.run(debug=True)