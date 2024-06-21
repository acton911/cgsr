from modules.decorator import exception_logger
from flask import request, jsonify, Blueprint
from .base import *

gpio = Blueprint('gpio', __name__)


@gpio.post("/set_pwm")
@exception_logger
def set_gpio_pwm():
    if not request.is_json:  # judge if data is json
        return {"error": "Request on http://127.0.0.1:port/set_pwm post data must be JSON"}, 415

    pin = request.get_json()
    pin_id = pin.get('id', None)
    pin_level = pin.get('level', None)

    if pin_id is None or pin_level is None:
        return {"error": "Request on http://127.0.0.1:port/set_pwm post data must contain id and level"}, 415
    if pin_level not in [0, 1]:
        return {"error": "Request on http://127.0.0.1:port/set_pwm post data level must be 0 or 1"}, 415

    set_status = set_1v8(pin_id, pin_level)
    if set_status:
        pin_info = {'id': pin_id, 'level': pin_level}
        return pin_info, 200
    else:
        return {'error': f"fail to set GPIO {pin_id} level"}, 200


@gpio.post("/set")
@exception_logger
def set_gpio_level():
    """
    Use POST method to set GPIO level.

    POST URL: "http://127.0.0.1:port/set"
    POST data: example {'id': x, 'level': 1/0}, x refer gpio number, level refer GPIO high/low level.

    example:
        r = requests.post(url, json={'id': 2, 'level': 1})
        print(r.status_code)
        print(r.json())

    :return: current set gpio status, type json, like: {'id': 2, 'level': 0} and status code 200,
             if set failed, return error message, type json, like {'error': "fail to set GPIO 2 level"} and status code 200
    """
    if not request.is_json:  # judge if data is json
        return {"error": "Request on http://127.0.0.1:port/set post data must be JSON"}, 415

    pin = request.get_json()
    pin_id = pin.get('id', None)
    pin_level = pin.get('level', None)

    if pin_id is None or pin_level is None:
        return {"error": "Request on http://127.0.0.1:port/set post data must contain id and level"}, 415
    if pin_level not in [0, 1]:
        return {"error": "Request on http://127.0.0.1:port/set post data level must be 0 or 1"}, 415

    set_status = set_gpio(pin_id, pin_level)
    if set_status:
        pin_info = {'id': pin_id, 'level': pin_level}
        return pin_info, 200
    else:
        return {'error': f"fail to set GPIO {pin_id} level"}, 200


@gpio.post("/get")
@exception_logger
def query_gpio_level():
    """
    Use POST method to get GPIO level status.

    POST URL: "http://127.0.0.1:port/get"
    POST data: example {'id': x}, x refer gpio number

    example:
        r = requests.post(url, json={'id': 2})
        print(r.json())

    :return:
            if query GPIO exist:
                return: {'id': x, 'level': 1/0}
            else return default level 0:
                return: {'id': x, 'level': 0}
    """

    if not request.is_json:  # judge if data is json
        return {"error": "Request on http://127.0.0.1:port/get post data must be JSON"}, 415

    pin = request.get_json()
    pin_id = pin.get('id', None)

    if pin_id is None:
        return {"error": "Request on http://127.0.0.1:port/get post data must contain id"}, 415

    # pin_level = _find_gpio(pin_id)
    pin_level = get_gpio(pin_id)

    if pin_level == '':
        return {'error': f"fail to get GPIO {pin_id} level"}, 200

    return {'id': pin_id, 'level': int(pin_level)}, 200


@gpio.post("/get_pin_out")
@exception_logger
def query_pin_out_level():
    if not request.is_json:  # judge if data is json
        return {"error": "Request on http://127.0.0.1:port/get post data must be JSON"}, 415

    pin = request.get_json()
    pin_id = pin.get('id', None)

    if pin_id is None:
        return {"error": "Request on http://127.0.0.1:port/get post data must contain id"}, 415

    # pin_level = _find_gpio(pin_id)
    pin_level = get_pin_out_level(pin_id)

    if pin_level == '':
        return {'error': f"fail to get GPIO {pin_id} level"}, 200

    return {'id': pin_id, 'level': int(pin_level)}, 200


@gpio.get('/get_all')
@exception_logger
def query_all_gpio_level():
    """
    Use get method to get all GPIO level status.

    Get URL: "http://127.0.0.1:port/get_all"

    example:
        r = requests.get(url)
        print(r.json())

    :return: All ports information.
    """
    return jsonify([])  # DEBUG


@gpio.post("/led_set_status")
@exception_logger
def set_led_status():
    """
    led set status.
    """
    if not request.is_json:  # judge if data is json
        return {"error": "Request on http://127.0.0.1:port/led_set_status post data must be JSON"}, 415

    led_status = request.get_json()
    # free, testing, breakdown
    free = led_status.get('free', None)
    testing = led_status.get('testing', None)
    breakdown = led_status.get('breakdown', None)

    if led_status is None:
        return {
                   "error": "Request on http://127.0.0.1:port/led_set_status post data must contain free, testing, breakdown"}, 415
    if free not in [True, False]:
        return {"error": "Request on http://127.0.0.1:port/led_set_status post data free must be True or False"}, 415
    if testing not in [True, False]:
        return {"error": "Request on http://127.0.0.1:port/led_set_status post data testing must be True or False"}, 415
    if breakdown not in [True, False]:
        return {
                   "error": "Request on http://127.0.0.1:port/led_set_status post data breakdown must be True or False"}, 415

    set_status = led_set_status(free, testing, breakdown)
    if set_status:
        status_info = {'free': free, 'testing': testing, 'breakdown': breakdown}
        return status_info, 200
    else:
        return {'error': f"fail to set LED {free, testing, breakdown} Status"}, 200


@gpio.post("/led_set")
@exception_logger
def set_led():
    """
    led set status.
    """
    global free, testing, breakdown
    status_key_value = {}
    if not request.is_json:  # judge if data is json
        return {"error": "Request on http://127.0.0.1:port/led_set_status post data must be JSON"}, 415

    led_status = request.get_json()
    # free, testing, breakdown
    if 'free' in led_status:
        free = led_status.get('free', None)
        if free not in [True, False]:
            return {"error": "Request on http://127.0.0.1:port/led_set_status post data free must be True or False"}, 415
        status_key_value['free'] = free

    if 'testing' in led_status:
        testing = led_status.get('testing', None)
        if testing not in [True, False]:
            return {"error": "Request on http://127.0.0.1:port/led_set_status post data testing must be True or False"}, 415
        status_key_value['testing'] = testing

    if 'breakdown' in led_status:
        breakdown = led_status.get('breakdown', None)
        if breakdown not in [True, False]:
            return {"error": "Request on http://127.0.0.1:port/led_set_status post data breakdown must be True or False"}, 415
        status_key_value['breakdown'] = breakdown

    if led_status is None:
        return {"error": "Request on http://127.0.0.1:port/led_set_status post data must contain free, testing, breakdown"}, 415

    set_status = led_set(status_key_value)

    if set_status:
        return status_key_value, 200
    else:
        return {'error': f"fail to set LED {led_status} Status"}, 200
