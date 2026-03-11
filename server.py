from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response
import os
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


def hello_world(request):
    name = os.environ.get('NAME')
    if name == None or len(name) == 0:
        name = "world"
    message = "Hello, " + name + "!\n"
    logger.info("API called")
    return Response(message)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))

    logger.info(f"Running main application and listening on port {port}")
    logger.info(f"Value of my port {os.environ.get('MY_PORT')}")

    with Configurator() as config:
        logger.info("Configuring APIs")
        config.add_route('hello', '/')
        config.add_view(hello_world, route_name='hello')
        app = config.make_wsgi_app()
    server = make_server('0.0.0.0', port, app)
    logger.info("Starting server")
    server.serve_forever()






