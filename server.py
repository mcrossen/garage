#!/usr/bin/env python3
from flask import Flask, request
from time import sleep
from threading import Thread, Lock
import click
import smbus


DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 8080
DEFAULT_LANDING_PAGE = 'index.html'
RELAY_ASSERT_DURATION = 0.5
RELAY_DEVICE_ADDR = 0x10
# the I2C data addresses for each door
GATE = 1
LEFT_GARAGE = 2
RIGHT_GARAGE = 3
# program variables
app = Flask(__name__)
relay_locks = {
    GATE: Lock(),
    LEFT_GARAGE: Lock(),
    RIGHT_GARAGE: Lock(),
}
bus = smbus.SMBus(1)


@click.command()
@click.option('--host', default=DEFAULT_HOST, help='What host to broadcast')
@click.option('--port', default=DEFAULT_PORT, help='What port to bind to')
@click.option('--landing-page', 'page',
    default=DEFAULT_LANDING_PAGE,
    help="the webpage to serve on the main page")
@click.option('--door-password', 'password', default='',
    help="require users to open doors with a password")
def run_server(host, port, page, password):
    """easy web interface to control gate and garage doors"""
    app.config['index'] = page
    app.config['password'] = password
    app.run(host=host, port=port)


def open_door(relay: int):
    def assert_relay(relay: int):
        with relay_locks.get(relay):
            bus.write_byte_data(RELAY_DEVICE_ADDR, relay, 0xFF)
            sleep(RELAY_ASSERT_DURATION)
            bus.write_byte_data(RELAY_DEVICE_ADDR, relay, 0x00)
    Thread(target=assert_relay, kwargs={'relay':relay}).start()


@app.route("/")
@app.route("/index")
def index():
    with open(app.config.get('index'), 'r') as file:
        return file.read()


@app.route("/open_gate", methods = ['POST'])
def open_gate():
    if app.config.get('password') != request.data.decode():
        print("invalid password: {}".format(request.data))
        return "unauthorized", 401
    open_door(GATE)
    return "opening gate..."


@app.route("/open_left_garage", methods = ['POST'])
def open_left_garage():
    if app.config.get('password') != request.data.decode():
        print("invalid password: {}".format(request.data))
        return "unauthorized", 401
    open_door(LEFT_GARAGE)
    return "opening left garage..."


@app.route("/open_right_garage", methods = ['POST'])
def open_right_garage():
    if app.config.get('password') != request.data.decode():
        print("invalid password: {}".format(request.data))
        return "unauthorized", 401
    open_door(RIGHT_GARAGE)
    return "opening right garage..."


@app.route("/health")
def health():
    return "1"


if __name__ == '__main__':
    run_server()
