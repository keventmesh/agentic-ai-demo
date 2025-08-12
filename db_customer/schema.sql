CREATE TABLE customers (
                           customer_id VARCHAR(10) PRIMARY KEY,
                           company_name VARCHAR(255),
                           contact_name VARCHAR(255),
                           contact_email VARCHAR(255) UNIQUE,
                           country VARCHAR(100),
                           phone VARCHAR(50)
);
