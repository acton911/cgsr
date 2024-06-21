from flask import Flask
from modules.env import env_check
from modules.gpio import gpio
from modules.quts import quts

# !!!端口已不再需要填写，通过PID VID自动获取

# Check ENV configs and etc.
env_check()

# Init Flask APP
app = Flask(__name__)

# Register Blueprints
app.register_blueprint(gpio)
app.register_blueprint(quts)

# run flask
app.run(
    host='0.0.0.0',
    port=55555,
)
