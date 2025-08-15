#!/usr/bin/env bash

# exit on error
set -e
source "$(dirname "$(realpath "${BASH_SOURCE[0]}")")"/library.sh

stop_db_customer
