#!/usr/bin/env bash

DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"
ROOT_DIR="$(dirname "$DIR")"
readonly ROOT_DIR


# Simple header for logging purposes.
function header() {
  local header_text="$1"
  local line_length=${#header_text}
  local border_line=$(printf '=%.0s' $(seq 1 $((line_length + 4))))

  echo "$border_line"
  echo "| $header_text |"
  echo "$border_line"
}

function stop_db_customer() {
    header "Stopping local Postgres"
    docker stop db_customer || true
}

function remove_db_customer() {
    header "Removing local Postgres"
    docker rm db_customer || true
}

function start_db_customer() {
    header "Starting local Postgres"
    docker run -d -p 5432:5432 --name db_customer -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=customer postgres:16.4
    echo "Sleeping 10 seconds to let Postgres start"
    sleep 10
}

function initialize_db_customer_schema() {
    header "Applying Postgres schema"
    docker cp "${ROOT_DIR}/db_customer/schema.sql" db_customer:/tmp/schema.sql
    docker exec -it db_customer psql -U postgres -d customer -f /tmp/schema.sql --echo-all -v ON_ERROR_STOP=1
}

function insert_db_customer_data() {
    header "Inserting Postgres data"
    docker cp "${ROOT_DIR}/db_customer/data.sql" db_customer:/tmp/data.sql
    docker exec -it db_customer psql -U postgres -d customer -f /tmp/data.sql --echo-all -v ON_ERROR_STOP=1
}
