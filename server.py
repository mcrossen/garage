#!/usr/bin/env python3
from flask import Flask, request
from time import sleep
from threading import Thread, Lock
import RPi.GPIO as gpio
import click


DEFAULT_HOST='0.0.0.0'
DEFAULT_PORT=8080
PIN_ASSERT_DURATION=0.5
DEFAULT_LANDING_PAGE='index.html'
# the gpio values for each pin
GATE=37
LEFT_GARAGE=35
RIGHT_GARAGE=33
PINS=[GATE, LEFT_GARAGE, RIGHT_GARAGE]
# program variables
app = Flask(__name__)
pin_locks = {}

@click.command()
@click.option('--host', default=DEFAULT_HOST, help='What host to broadcast')
@click.option('--port', default=DEFAULT_PORT, help='What port to bind to')
@click.option('--invert-gpio', 'invert', is_flag=True)
@click.option('--landing-page', 'page',
    default=DEFAULT_LANDING_PAGE,
    help="the webpage to serve on the main page")
@click.option('--door-password', 'password', default='',
    help="require users to open doors with a password")
def run_server(host, port, invert, page, password):
    """easy web interface to control gate and garage doors"""
    app.config['index'] = page
    app.config['invert_gpio'] = invert
    app.config['password'] = password
    setup_gpio(PINS)
    app.run(host=host, port=port)


def pin_off():
    return app.config.get('invert_gpio')


def pin_on():
    return not app.config.get('invert_gpio')


def setup_gpio(pins: list):
    gpio.setmode(gpio.BOARD)
    for pin in pins:
        gpio.setup(pin, gpio.OUT)
        gpio.output(pin, pin_off())
        pin_locks[pin] = Lock()


def open_door(pin: int):
    def assert_pin(pin: int):
        with pin_locks.get(pin):
            gpio.output(pin, pin_on())
            sleep(PIN_ASSERT_DURATION)
            gpio.output(pin, pin_off())
    Thread(target=assert_pin, kwargs={'pin':pin}).start()
    

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
