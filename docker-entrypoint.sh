#!/usr/bin/env bash

exec gosu "${RUN_AS:-1000:1000}" "$@"
