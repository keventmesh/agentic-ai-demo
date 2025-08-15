#!/usr/bin/env bash

# exit on error
set -e
source "$(dirname "$(realpath "${BASH_SOURCE[0]}")")"/library.sh

stop_db_customer
remove_db_customer
start_db_customer
initialize_db_customer_schema
insert_db_customer_data
