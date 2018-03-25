#!/usr/bin/env python3
from flask import Flask


PORT=8080
app = Flask(__name__)


@app.route("/")
@app.route("/index")
def index():
    with open('index.html', 'r') as file:
        return file.read()


@app.route("/open_gate", methods = ['POST'])
def opengate():
    return "opening gate..."


@app.route("/open_left_garage", methods = ['POST'])
def openLeftGarage():
    return "opening left garage..."


@app.route("/open_right_garage", methods = ['POST'])
def openRightGarage():
    return "opening right garage..."


if __name__ == '__main__':
    app.run(port=PORT)
