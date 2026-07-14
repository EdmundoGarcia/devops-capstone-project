"""
Package: service
Package for the application models and service routes
This module creates and configures the Flask app and sets up the logging
and SQL database
"""
import sys
from flask import Flask
from flask_talisman import Talisman
from flask_cors import CORS
from service import config
from service.common import log_handlers

app = Flask(__name__)
app.config.from_object(config)

talisman = Talisman(app)
CORS(app)

# pylint: disable=wrong-import-position, cyclic-import, wrong-import-order
from service import models, routes  # noqa: F401 E402
from service.common import cli_commands, error_handlers  # noqa: F401 E402
# pylint: enable=wrong-import-position

log_handlers.init_logging(app, "gunicorn.error")

# pylint: disable=no-member
app.logger.info(70 * "*")
app.logger.info("  A C C O U N T   S E R V I C E   R U N N I N G  ".center(70, "*"))
app.logger.info(70 * "*")

try:
    models.init_db(app)
except Exception as error:  # pylint: disable=broad-except
    app.logger.critical("%s: Cannot continue", error)
    sys.exit(4)

app.logger.info("Service initialized!")
# pylint: enable=no-member
