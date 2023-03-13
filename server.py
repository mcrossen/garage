#!/usr/bin/env python3
from flask import Flask, request
from time import sleep
from threading import Thread, Lock
import RPi.GPIO as GPIO
import click
import smbus
import json
import logging

DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 8080
DEFAULT_LANDING_PAGE = 'index.html'
RELAY_ASSERT_DURATION = 0.5
RELAY_POST_SLEEP_DURATION = 8
RELAY_DEVICE_ADDR = 0x10
doors = {
  'garage': {
    'relay_num': 1,
    'sensor_pin': 15,
    'lock': Lock()
  }
}
app = Flask(__name__)
bus = smbus.SMBus(1)
GPIO.setmode(GPIO.BOARD)
app.logger.setLevel(logging.INFO)

def check_door_sensor_state(door_name):
    gpio = doors[door_name]['sensor_pin']
    state = GPIO.input(gpio)
    if state == 1:
        return 'open'
    else:
        return 'closed'

for door_name in doors.keys():
    if 'sensor_pin' in doors[door_name]:
        GPIO.setup(doors[door_name]['sensor_pin'], GPIO.IN, pull_up_down = GPIO.PUD_UP)

def check_door_state(door_name):
    if 'transitioning' in doors[door_name]:
        return 'indeterminate'
    if 'sensor_pin' not in doors[door_name]:
        return 'unknown'
    if 'desired' in doors[door_name]:
        return 'indeterminate'
    return check_door_sensor_state(door_name)

def toggle_door_state_unsafe(door_name):
    relay = doors[door_name]['relay_num']
    bus.write_byte_data(RELAY_DEVICE_ADDR, relay, 0xFF)
    sleep(RELAY_ASSERT_DURATION)
    bus.write_byte_data(RELAY_DEVICE_ADDR, relay, 0x00)
    sleep(RELAY_POST_SLEEP_DURATION)

def toggle_door_state_blocking(door_name):
    with doors[door_name]['lock']:
        toggle_door_state_unsafe(door_name)
        del doors[door_name]['transitioning']
    app.logger.info('finished state toggle for {}'.format(door_name))

def change_door_state_unsafe(door_name, desired):
    current = check_door_sensor_state(door_name)
    if current == desired:
        app.logger.info('extraneous state transition for {} (current: {}, desired: {})'.format(door_name, current, desired))
        return
    toggle_door_state_unsafe(door_name)
    current = check_door_sensor_state(door_name)
    last = doors[door_name]['last']
    desired = doors[door_name]['desired']
    if last == desired and current != desired:
        doors[door_name]['last'] = current
        app.logger.info('repeating state transition for {} (current: {}, desired: {})'.format(door_name, current, desired))
        change_door_state_unsafe(door_name, desired)
    elif last != desired and current == desired:
        doors[door_name]['last'] = current
        app.logger.info('successful state transition for {} (current: {})'.format(door_name, current))
    else:
        app.logger.error('state transition error for {} (current: {}, last: {}, desired: {})'.format(door_name, current, last, desired))

def change_door_state_blocking(door_name, desired):
    with doors[door_name]['lock']:
        change_door_state_unsafe(door_name, desired)
        del doors[door_name]['last']
        del doors[door_name]['desired']
    app.logger.info('finished state transition for {} (desired: {})'.format(door_name, desired))

def change_door_state(door_name, desired):
    if 'sensor_pin' not in doors[door_name] or desired == 'unknown':
        app.logger.info('beginning state toggle for {}'.format(door_name))
        doors[door_name]['transitioning'] = True
        Thread(target=toggle_door_state_blocking, kwargs={'door_name':door_name}).start()
    elif 'desired' in doors[door_name]:
        doors[door_name]['desired'] = desired
        current = check_door_sensor_state(door_name)
        app.logger.info('queuing state transition for {} (current: {}, desired: {})'.format(door_name, current, desired))
    else:
        doors[door_name]['desired'] = desired
        current = check_door_sensor_state(door_name)
        doors[door_name]['last'] = current
        app.logger.info('beginning state transition for {} (current: {}, desired: {})'.format(door_name, current, desired))
        Thread(target=change_door_state_blocking, kwargs={'door_name':door_name, 'desired':desired}).start()

@click.command()
@click.option('--host', default=DEFAULT_HOST, help='What host to broadcast')
@click.option('--port', default=DEFAULT_PORT, help='What port to bind to')
@click.option('--landing-page', 'page',
    default=DEFAULT_LANDING_PAGE,
    help='the webpage to serve on the main page')
def run_server(host, port, page):
    '''easy web interface to control gate and garage doors'''
    app.config['index'] = page
    app.run(host=host, port=port)

@app.route('/')
@app.route('/index')
def index():
    with open(app.config.get('index'), 'r') as file:
        return file.read()

@app.route('/doors/<door_name>', methods = ['GET'])
def door_state(door_name=None):
    if door_name is None:
        return 'bad request', 400
    return '{{\"state\": \"{}\"}}'.format(check_door_state(door_name))

@app.route('/doors/<door_name>', methods = ['POST'])
def open_door(door_name=None):
    if door_name is None:
        return 'bad request', 400
    data = json.loads(request.data)
    change_door_state(door_name, data['state'])
    return '{{\"state\": \"{}\"}}'.format(check_door_state(door_name))

@app.route('/doors', methods = ['GET'])
def list_doors():
    return json.dumps(list(doors.keys()))

@app.route('/health')
def health():
    return '1'

if __name__ == '__main__':
    run_server()
