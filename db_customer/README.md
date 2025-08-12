# Customer Database

The schema and the seed are built from the files here.

The schema file and seed file are separated into 2 respective files (schema.sql and data.sql).
Then they are put in the Postgres container's `/docker-entrypoint-initdb.d` directory so that the schema and the data is applied when the Postgres container starts running.

## Using the customer database locally

Start the customer database:
```shell
../hack/customer-db-start.sh
```

Stop the customer database:
```shell
../hack/customer-db-stop.sh
```

