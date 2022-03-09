import sys

from flask import Flask, jsonify
import requests

from circuit_breaker import breaker

app = Flask("client")


@breaker
def call_service_1():
    response = requests.get("http://localhost:5001", timeout=1)
    if response.status_code >= 500:
        raise Exception("Service 1 is down")
    return response.json()["data"]


def call_service_2():
    response = requests.get("http://localhost:5002", timeout=1)
    if response.status_code >= 500:
        raise Exception("Service 2 is down")
    return response.json()["data"]


@app.route("/", methods=['GET'])
def orchestrator():
    try:
        data = call_service_1()
        return jsonify({"message": f"service 1 data: {data}"}), 200
    except Exception as e:
        print(e)
        data = call_service_2()
        return jsonify({"message": f"service 2 data: {data}"}), 200


if __name__ == "__main__":
    port = sys.argv[1]
    app.run(debug=True, port=port)
