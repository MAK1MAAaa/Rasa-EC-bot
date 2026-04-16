CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

DROP TABLE IF EXISTS kb_chunks CASCADE;
DROP TABLE IF EXISTS kb_documents CASCADE;
DROP TABLE IF EXISTS chat_context_snapshots CASCADE;
DROP TABLE IF EXISTS chat_messages CASCADE;
DROP TABLE IF EXISTS chat_sessions CASCADE;
DROP TABLE IF EXISTS chat_user_global_memory CASCADE;
DROP TABLE IF EXISTS chat_pending_actions CASCADE;
DROP TABLE IF EXISTS chat_attachments CASCADE;
DROP TABLE IF EXISTS geo_cache CASCADE;
DROP TABLE IF EXISTS logistics_complaints CASCADE;
DROP TABLE IF EXISTS after_sales CASCADE;
DROP TABLE IF EXISTS logistics CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS cart_items CASCADE;
DROP TABLE IF EXISTS product_view_history CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS shop_addresses CASCADE;
DROP TABLE IF EXISTS shops CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'customer' CHECK (role IN ('customer', 'merchant')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX uq_users_email_lower ON users ((LOWER(email)));
CREATE INDEX idx_users_role ON users(role);

CREATE TABLE shops (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    contact_email VARCHAR(255),
    contact_phone VARCHAR(30),
    logo_url TEXT,
    rating DOUBLE PRECISION CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5)),
    service_score DOUBLE PRECISION CHECK (service_score IS NULL OR (service_score >= 0 AND service_score <= 5)),
    logistics_score DOUBLE PRECISION CHECK (logistics_score IS NULL OR (logistics_score >= 0 AND logistics_score <= 5)),
    after_sales_score DOUBLE PRECISION CHECK (after_sales_score IS NULL OR (after_sales_score >= 0 AND after_sales_score <= 5)),
    shipping_city VARCHAR(120),
    featured_categories JSONB NOT NULL DEFAULT '[]'::jsonb,
    service_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_shops_owner_user_id ON shops(owner_user_id);

CREATE TABLE shop_addresses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shop_id UUID NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    label VARCHAR(100) NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    contact_phone VARCHAR(30) NOT NULL,
    province VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    address_line TEXT NOT NULL,
    postal_code VARCHAR(20),
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_shop_addresses_shop_id ON shop_addresses(shop_id);

CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shop_id UUID NOT NULL REFERENCES shops(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    image_url TEXT,
    category VARCHAR(100),
    brand VARCHAR(120),
    model VARCHAR(160),
    sku_code VARCHAR(120),
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    original_price DECIMAL(10, 2) CHECK (original_price IS NULL OR original_price >= price),
    rating DOUBLE PRECISION CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5)),
    review_count INT NOT NULL DEFAULT 0 CHECK (review_count >= 0),
    monthly_sales INT NOT NULL DEFAULT 0 CHECK (monthly_sales >= 0),
    ship_in_hours INT NOT NULL DEFAULT 0 CHECK (ship_in_hours >= 0),
    warranty_days INT NOT NULL DEFAULT 0 CHECK (warranty_days >= 0),
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    spec_highlights JSONB NOT NULL DEFAULT '[]'::jsonb,
    stock INT NOT NULL DEFAULT 0 CHECK (stock >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_shop_id ON products(shop_id);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_brand ON products(brand);
CREATE INDEX idx_products_active_created_at ON products(is_active, created_at DESC);
CREATE INDEX idx_products_monthly_sales ON products(monthly_sales DESC);
CREATE INDEX idx_products_rating ON products(rating DESC);

CREATE TABLE product_view_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    view_count INT NOT NULL DEFAULT 1 CHECK (view_count > 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_viewed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_product_view_history_user_product UNIQUE (user_id, product_id)
);

CREATE INDEX idx_product_view_history_user_last_viewed_at
    ON product_view_history(user_id, last_viewed_at DESC);

CREATE TABLE orders (
    id VARCHAR(50) PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    shop_id UUID NOT NULL REFERENCES shops(id),
    status VARCHAR(50) NOT NULL,
    address TEXT NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL CHECK (total_amount >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_orders_user_created_at ON orders(user_id, created_at DESC);
CREATE INDEX idx_orders_shop_created_at ON orders(shop_id, created_at DESC);

CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id VARCHAR(50) NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    product_name VARCHAR(255) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL CHECK (unit_price >= 0),
    quantity INT NOT NULL CHECK (quantity > 0),
    subtotal DECIMAL(10, 2) NOT NULL CHECK (subtotal >= 0)
);

CREATE INDEX idx_order_items_order_id ON order_items(order_id);

CREATE TABLE cart_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    quantity INT NOT NULL CHECK (quantity > 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, product_id)
);

CREATE INDEX idx_cart_items_user_updated_at ON cart_items(user_id, updated_at DESC);

CREATE TABLE logistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id VARCHAR(50) NOT NULL UNIQUE REFERENCES orders(id),
    shipped_from_address_id UUID REFERENCES shop_addresses(id),
    tracking_no VARCHAR(100) UNIQUE,
    status VARCHAR(50) NOT NULL,
    current_location TEXT,
    current_lng DOUBLE PRECISION,
    current_lat DOUBLE PRECISION,
    estimated_delivery_at TIMESTAMP WITH TIME ZONE,
    route_plan JSONB NOT NULL DEFAULT '[]'::jsonb,
    route_geo JSONB NOT NULL DEFAULT '[]'::jsonb,
    llm_raw_text TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE logistics_complaints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id VARCHAR(50) NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    status VARCHAR(50) NOT NULL,
    resolution_note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_logistics_complaints_order_id ON logistics_complaints(order_id);
CREATE INDEX idx_logistics_complaints_status_updated_at ON logistics_complaints(status, updated_at DESC);

CREATE TABLE geo_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_text VARCHAR(512) NOT NULL UNIQUE,
    lng DOUBLE PRECISION NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    provider VARCHAR(32) NOT NULL DEFAULT 'amap',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_geo_cache_updated_at ON geo_cache(updated_at DESC);

CREATE TABLE after_sales (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id VARCHAR(50) NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL CHECK (type IN ('return', 'exchange')),
    reason TEXT,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_after_sales_order_id ON after_sales(order_id);
CREATE INDEX idx_after_sales_status_created_at ON after_sales(status, created_at DESC);

CREATE TABLE kb_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type VARCHAR(32) NOT NULL CHECK (source_type IN ('policy', 'manual')),
    title TEXT NOT NULL,
    version VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    checksum CHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_kb_documents_source_status ON kb_documents(source_type, status);
CREATE INDEX idx_kb_documents_title ON kb_documents(title);

CREATE TABLE kb_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
    chunk_order INT NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(1024) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_kb_chunks_document_order ON kb_chunks(document_id, chunk_order);
CREATE INDEX idx_kb_chunks_embedding_ivfflat ON kb_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_kb_chunks_text_fts ON kb_chunks USING GIN (to_tsvector('simple', chunk_text));

CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(128) NOT NULL,
    sender_id VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL DEFAULT '新会话',
    message_count INT NOT NULL DEFAULT 0 CHECK (message_count >= 0),
    current_snapshot_version INT NOT NULL DEFAULT 0 CHECK (current_snapshot_version >= 0),
    current_context_file_path TEXT,
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, session_id)
);

CREATE INDEX idx_chat_sessions_user_last_message ON chat_sessions(user_id, last_message_at DESC);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(128) NOT NULL,
    sender_role VARCHAR(20) NOT NULL CHECK (sender_role IN ('user', 'assistant', 'system')),
    sequence_no INT NOT NULL CHECK (sequence_no > 0),
    message_text TEXT NOT NULL DEFAULT '',
    attachment_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    route_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    cards JSONB NOT NULL DEFAULT '[]'::jsonb,
    actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(chat_session_id, sequence_no)
);

CREATE INDEX idx_chat_messages_session_sequence ON chat_messages(chat_session_id, sequence_no DESC);
CREATE INDEX idx_chat_messages_user_created_at ON chat_messages(user_id, created_at DESC);

CREATE TABLE chat_context_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(128) NOT NULL,
    snapshot_version INT NOT NULL CHECK (snapshot_version > 0),
    start_sequence_no INT NOT NULL CHECK (start_sequence_no > 0),
    end_sequence_no INT NOT NULL CHECK (end_sequence_no >= start_sequence_no),
    summary_markdown TEXT NOT NULL,
    memory_facts JSONB NOT NULL DEFAULT '{}'::jsonb,
    recent_window JSONB NOT NULL DEFAULT '[]'::jsonb,
    context_file_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(chat_session_id, snapshot_version)
);

CREATE INDEX idx_chat_context_snapshots_session_version ON chat_context_snapshots(chat_session_id, snapshot_version DESC);

CREATE TABLE chat_user_global_memory (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    memory_markdown TEXT NOT NULL,
    memory_facts JSONB NOT NULL DEFAULT '{}'::jsonb,
    recent_topics JSONB NOT NULL DEFAULT '[]'::jsonb,
    context_file_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_pending_actions (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_pending_actions_expires_at ON chat_pending_actions(expires_at);

CREATE TABLE chat_attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    sender_id VARCHAR(255),
    local_path TEXT NOT NULL,
    mime VARCHAR(64) NOT NULL,
    sha256 CHAR(64) NOT NULL,
    width INT,
    height INT,
    size_bytes BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_attachments_user_id ON chat_attachments(user_id, created_at DESC);
CREATE INDEX idx_chat_attachments_sha256 ON chat_attachments(sha256);
