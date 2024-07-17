import json
import os
import subprocess

from flask import Flask, request, render_template, redirect, url_for
from flask_restful import Resource, Api

from log import create_logger

app = Flask(__name__)
api = Api(app)

root = os.path.dirname(os.path.abspath(__file__))

##########FRONTEND############


@app.route("/heroes")
def heroes():
    return render_template("heroes.html")


@app.route("/", methods=["GET", "POST"])
def inicio():
    if request.method == "POST":
        body = request.form["body"]
        with open("lists.txt", "wt") as file:
            file.write(body)
        return redirect(url_for("inicio"))  # noqa: F821
    message = {}
    ps_aux = subprocess.run(
        ["ps", "aux"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    process = [
        line
        for line in ps_aux.stdout.decode("utf-8").split("\n")
        if "python3 -m main run" in line
    ]
    count = len(process)
    if count > 0:
        message = {"message": "Welcome to the ytmusicdl API!", "status": "running"}
    else:
        message = {"message": "Welcome to the ytmusicdl API!", "status": "stopped"}
    try:
        links = open("lists.txt", "rt").read()
    except:
        links = None
    try:
        log = open(os.path.join(root, "app.log"), "r").readlines()[-1]
    except:
        log = None
    try:
        refresh = request.args.get("refresh")
    except:
        refresh = None
    return render_template(
        "index.html",
        message=message,
        links=links if links else "",
        len=len,
        log=log if log else "",
        refresh=refresh if refresh else "",
        is_zip = os.path.isfile(os.path.join(root, "static", "files.zip"))
    )


#########BACKEND###########


class Home(Resource):
    def get(self):
        ps_aux = subprocess.run(
            ["ps", "aux"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        process = [
            line
            for line in ps_aux.stdout.decode("utf-8").split("\n")
            if "python3 -m main run" in line
        ]
        count = len(process)
        if count > 0:
            return {
                "message": "Welcome to the ytmusicdl API!",
                "status": "running",
                "pid": process[0].split()[1],
            }
        else:
            return {"message": "Welcome to the ytmusicdl API!", "status": "stopped"}


api.add_resource(Home, "/api")


class Log(Resource):
    def get(self):
        # Read the log file
        try:
            log = [
                line.strip()
                for line in open(os.path.join(root, "app.log"), "r").readlines()
            ]
        except FileNotFoundError:
            return {"error": "File not found"}, 404
        else:
            # Return the last 20 lines of the log file
            try:
                if request.args.get("last") == "all":
                    return (log), 200
                if (
                    request.args.get("last").isnumeric()
                    and int(request.args.get("last")) > 0
                ):
                    return (log[-(int(request.args.get("last"))) :]), 200
            except:
                pass
            if len(log) < 20:
                return (log), 200
            return (log[-20:]), 200


api.add_resource(Log, "/api/log")


class Error(Resource):
    def get(self):
        # Read the log file
        try:
            log = [
                line.strip()
                for line in open(os.path.join(root, "error.log"), "r").readlines()
            ]
        except FileNotFoundError:
            return {"error": "File not found"}, 404
        else:
            # Return the last 20 lines of the log file
            try:
                if request.args.get("last") == "all":
                    return (log), 200
                if (
                    request.args.get("last").isnumeric()
                    and int(request.args.get("last")) > 0
                ):
                    return (log[-(int(request.args.get("last"))) :]), 200
            except:
                pass
            if len(log) < 20:
                return (log), 200
            return (log[-20:]), 200


api.add_resource(Error, "/api/error")


class Start(Resource):
    def get(self):
        ps_aux = subprocess.run(
            ["ps", "aux"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        count = len(
            [
                line
                for line in ps_aux.stdout.decode("utf-8").split("\n")
                if "python3 -m main run" in line
            ]
        )
        if count > 0:
            return {"status": "Already running"}, 200
        else:
            try:
                os.remove(os.path.join(root, "app.log"))
                os.remove(os.path.join(root, "error.log"))
            except:
                pass
            _ = subprocess.Popen(
                [
                    "/home/endeavour/repos/ytmusicdl/.venv/bin/python3",
                    "-m",
                    "main",
                    "run",
                ]
            )
            return redirect(url_for("inicio", refresh=3))

    def post(self):
        urls = request.json["urls"]
        if len(urls) > 0:
            with open(os.path.join(root, "lists.txt"), "w") as f:
                f.write("\n".join(urls))
            ps_aux = subprocess.run(
                ["ps", "aux"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
            count = len(
                [
                    line
                    for line in ps_aux.stdout.decode("utf-8").split("\n")
                    if "python3 -m main run" in line
                ]
            )
            if count > 0:
                return {"status": "Already running"}, 200
            else:
                os.remove(os.path.join(root, "app.log"))
                os.remove(os.path.join(root, "error.log"))
                _ = subprocess.Popen(
                    [
                        "/home/endeavour/repos/ytmusicdl/.venv/bin/python3",
                        "-m",
                        "main",
                        "run",
                    ]
                )
                return {"status": "OK"}, 200
        else:
            return {"status": "No URLs provided"}, 400


api.add_resource(Start, "/api/start")


class Stop(Resource):
    def get(self):
        ps_aux = subprocess.run(
            ["ps", "aux"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        process = [
            line
            for line in ps_aux.stdout.decode("utf-8").split("\n")
            if "python3 -m main run" in line
        ]
        count = len(process)
        if count > 0:
            log = create_logger("api")
            pid = str(process[0].split()[1])
            _ = subprocess.Popen(["kill", pid])
            log.warning(f"Download process with PID {pid} stopped by user command")
            return {"status": f"Download process with PID {pid} stopped"}, 200
        else:
            return {"status": "Not running"}, 200


api.add_resource(Stop, "/api/stop")

if __name__ == "__main__":
    app.run(debug=True)
