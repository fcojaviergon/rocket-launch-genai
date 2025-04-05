#!/bin/bash

# Start Flower to monitor Celery
celery -A tasks.worker flower --port=5566 