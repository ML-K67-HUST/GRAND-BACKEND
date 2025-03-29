#!/bin/bash

docker network create timenest 2>/dev/null || true

docker-compose up --build