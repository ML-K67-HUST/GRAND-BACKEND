#!/bin/bash

docker network create timenest 2>/dev/null || true

if [ "$1" = "--scale=True" ]; then
    echo "🚀 Starting scaled deployment with 3 app instances..."
    docker-compose up --build --scale app=3
else
    echo "🚀 Starting normal deployment..."
    docker-compose up --build
fi