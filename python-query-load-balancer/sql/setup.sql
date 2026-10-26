CREATE DATABASE IF NOT EXISTS load_balancer_demo;

USE load_balancer_demo;

CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    price DECIMAL(10, 2) NOT NULL DEFAULT 0.00
);

INSERT INTO products (name, price)
SELECT 'Keyboard', 750.00
WHERE NOT EXISTS (
    SELECT 1 FROM products WHERE name = 'Keyboard'
);

INSERT INTO products (name, price)
SELECT 'Mouse', 400.00
WHERE NOT EXISTS (
    SELECT 1 FROM products WHERE name = 'Mouse'
);

SELECT * FROM products;