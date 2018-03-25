#!/usr/bin/env python3
from flask import Flask


app = Flask(__name__)


@app.route("/")
@app.route("/index")
def index():
    with open('index.html', 'r') as file:
        return file.read()


@app.route("/gate", methods = ['POST'])
def opengate():
    return "opening gate..."


@app.route("/leftgarage", methods = ['POST'])
def openLeftGarage():
    return "opening left garage..."


@app.route("/rightgarage", methods = ['POST'])
def openRightGarage():
    return "opening right garage..."


if __name__ == '__main__':
    app.run()
