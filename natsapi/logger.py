# Make logging prettier with this
# https://github.com/encode/uvicorn/blob/master/uvicorn/logging.py
import logging

logger = logging.getLogger("natsapi")
logging.basicConfig(level=logging.INFO)
