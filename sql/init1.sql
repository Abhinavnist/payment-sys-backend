-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create merchants table
CREATE TABLE merchants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    business_name VARCHAR(255) NOT NULL,
    business_type VARCHAR(100) NOT NULL,
    contact_phone VARCHAR(20) NOT NULL,
    address TEXT,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    callback_url TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    webhook_secret VARCHAR(255),
    min_deposit INTEGER NOT NULL DEFAULT 500,
    max_deposit INTEGER NOT NULL DEFAULT 300000,
    min_withdrawal INTEGER NOT NULL DEFAULT 1000,
    max_withdrawal INTEGER NOT NULL DEFAULT 1000000,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create merchant_bank_details table
CREATE TABLE merchant_bank_details (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    bank_name VARCHAR(255) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    account_number VARCHAR(50) NOT NULL,
    ifsc_code VARCHAR(20) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create merchant_upi_details table
CREATE TABLE merchant_upi_details (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    upi_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create ip_whitelist table
CREATE TABLE ip_whitelist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    ip_address VARCHAR(45) NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (merchant_id, ip_address)
);

-- Create payments table
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    reference VARCHAR(255) NOT NULL,
    trxn_hash_key VARCHAR(255) UNIQUE NOT NULL,
    payment_type VARCHAR(50) NOT NULL CHECK (payment_type IN ('DEPOSIT', 'WITHDRAWAL')),
    payment_method VARCHAR(50) NOT NULL CHECK (payment_method IN ('UPI', 'BANK_TRANSFER')),
    amount INTEGER NOT NULL CHECK (amount > 0),
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    status VARCHAR(50) NOT NULL CHECK (status IN ('PENDING', 'CONFIRMED', 'DECLINED')) DEFAULT 'PENDING',
    utr_number VARCHAR(50),
    account_name VARCHAR(255),
    account_number VARCHAR(50),
    bank VARCHAR(255),
    bank_ifsc VARCHAR(20),
    user_data JSONB,
    verified_by UUID REFERENCES users(id),
    verification_method VARCHAR(50) CHECK (verification_method IN ('MANUAL', 'AUTO')),
    remarks TEXT,
    callback_sent BOOLEAN NOT NULL DEFAULT FALSE,
    callback_response TEXT,
    callback_attempts INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create bank_statements table
CREATE TABLE bank_statements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    uploaded_by UUID NOT NULL REFERENCES users(id),
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    matched_transactions INTEGER NOT NULL DEFAULT 0,
    uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

---- Create rate_limits table
--CREATE TABLE rate_limits (
--    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
--    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
--    endpoint VARCHAR(100) NOT NULL,
--    requests_per_minute INTEGER NOT NULL DEFAULT 60,
--    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
--    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
--    UNIQUE (merchant_id, endpoint)
--);

-- Create payment_links table
CREATE TABLE payment_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    reference VARCHAR(255) NOT NULL,
    amount INTEGER NOT NULL CHECK (amount > 0),
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    description TEXT,
    status VARCHAR(50) NOT NULL CHECK (status IN ('ACTIVE', 'COMPLETED', 'EXPIRED')),
    payment_id UUID REFERENCES payments(id),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_payments_merchant_id ON payments(merchant_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_created_at ON payments(created_at);
CREATE INDEX idx_payments_trxn_hash_key ON payments(trxn_hash_key);
CREATE INDEX idx_payments_utr_number ON payments(utr_number);
CREATE INDEX idx_merchant_user_id ON merchants(user_id);

-- Create function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers to update the updated_at timestamp
CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_merchants_updated_at
BEFORE UPDATE ON merchants
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_merchant_bank_details_updated_at
BEFORE UPDATE ON merchant_bank_details
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_merchant_upi_details_updated_at
BEFORE UPDATE ON merchant_upi_details
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at
BEFORE UPDATE ON payments
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Create views for common queries
CREATE VIEW pending_payments AS
SELECT
    p.id, p.merchant_id, m.business_name, p.reference, p.trxn_hash_key,
    p.payment_type, p.payment_method, p.amount, p.currency, p.created_at
FROM
    payments p
JOIN
    merchants m ON p.merchant_id = m.id
WHERE
    p.status = 'PENDING';

---- Create function for checking rate limits
--CREATE OR REPLACE FUNCTION check_rate_limit(
--    p_merchant_id UUID,
--    p_endpoint VARCHAR,
--    p_current_time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
--) RETURNS BOOLEAN AS $$
--DECLARE
--    v_limit INTEGER;
--    v_count INTEGER;
--BEGIN
--    -- Get rate limit for merchant and endpoint
--    SELECT requests_per_minute INTO v_limit
--    FROM rate_limits
--    WHERE merchant_id = p_merchant_id AND endpoint = p_endpoint;
--
--    -- If no rate limit is defined, use default
--    IF v_limit IS NULL THEN
--        v_limit := 60;
--    END IF;
--
--    -- Count requests in the last minute
--    SELECT COUNT(*) INTO v_count
--    FROM rate_limit_logs
--    WHERE merchant_id = p_merchant_id
--      AND endpoint = p_endpoint
--      AND timestamp > (p_current_time - INTERVAL '1 minute');
--
--    -- Return true if within rate limit, false otherwise
--    RETURN v_count < v_limit;
--END;
--$$ LANGUAGE plpgsql;

---- Create rate_limit_logs table for tracking API calls
--CREATE TABLE rate_limit_logs (
--    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
--    merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
--    endpoint VARCHAR(100) NOT NULL,
--    ip_address VARCHAR(45) NOT NULL,
--    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
--);

-- -- Create index for rate limiting queries
-- CREATE INDEX idx_rate_limit_logs_merchant_endpoint_timestamp ON
--     rate_limit_logs(merchant_id, endpoint, timestamp);

-- Insert default admin user
INSERT INTO users (
    email,
    hashed_password,
    full_name,
    is_active,
    is_superuser
) VALUES (
    'admin@example.com',
    -- Password: admin123 (replace with properly hashed password in production)
    '$2b$12$t7Gls/kKCdX0YMFUY6v7.edftn6vwE7XYdIH7LLC3JJVtuJmqYuZ6',
    'System Administrator',
    TRUE,
    TRUE
);

DELETE FROM users
WHERE email = 'admin@example.com';

select * from users;
SELECT * FROM merchants;
SELECT * FROM merchant_bank_details;
SELECT * FROM merchant_upi_details;
SELECT * FROM ip_whitelist;
SELECT * FROM payments;
SELECT * FROM bank_statements;
SELECT * FROM payment_links;

ALTER TABLE payments ADD CONSTRAINT unique_utr UNIQUE (utr_number);