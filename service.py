import sys
from functools import wraps
from time import sleep
from random import randint

from flask import Flask, jsonify, request


app = Flask("service")

app.config['TIMEOUT'] = 0.5
app.config['FAIL_WITH_5XX'] = False


def alter_rute(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        sleep(app.config['TIMEOUT'])
        if app.config['FAIL_WITH_5XX']:
            r = jsonify({"error": "BOOM"}), (500 + randint(0, 4))
        else:
            r = f(*args, **kwargs)
        return r
    return wrapper


@app.route("/toggle_fail", methods=['PUT'])
def toggle_fail():
    app.config['FAIL_WITH_5XX'] = not app.config['FAIL_WITH_5XX']
    return jsonify({"message": f"FAIL_WITH_5XX: {app.config['FAIL_WITH_5XX']}"}), 200


@app.route("/timeout", methods=['PUT'])
def update_timeout():
    try:
        app.config['TIMEOUT'] = float(request.json["timeout"])
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    else:
        return jsonify({"message": f"TIMEOUT: {app.config['TIMEOUT']}"}), 200


@app.route("/", methods=['GET'])
@alter_rute
def index():
    return jsonify({"data": "Im a good boy"}), 200


if __name__ == "__main__":
    port = sys.argv[1]
    app.run(port=port)
