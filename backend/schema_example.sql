-- Example schema you can paste into the "Schema" box in the UI.
-- The SQL generator only uses tables/columns described here.

CREATE TABLE customers (
    id           INT IDENTITY PRIMARY KEY,
    customer_name NVARCHAR(200) NOT NULL,
    region        NVARCHAR(100),
    created_at    DATETIME DEFAULT GETDATE()
);

CREATE TABLE orders (
    id          INT IDENTITY PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(id),
    order_total DECIMAL(12, 2) NOT NULL,
    order_date  DATE NOT NULL,
    status      NVARCHAR(20) NOT NULL  -- 'paid', 'pending', 'cancelled'
);
