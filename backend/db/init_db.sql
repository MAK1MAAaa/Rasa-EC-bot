-- 启用 UUID 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 4.1 用户表 (users)
DROP TABLE IF EXISTS users CASCADE;
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4.3 商品表 (products)
DROP TABLE IF EXISTS products CASCADE;
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock INT NOT NULL DEFAULT 0
);

-- 4.2 订单主表 (orders)
DROP TABLE IF EXISTS orders CASCADE;
CREATE TABLE orders (
    id VARCHAR(50) PRIMARY KEY, -- 订单号通常是业务生成的字符串
    user_id UUID REFERENCES users(id),
    status VARCHAR(50) NOT NULL, -- 待发货/已发货/已完成/已取消
    address TEXT NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4.4 物流表 (logistics)
DROP TABLE IF EXISTS logistics CASCADE;
CREATE TABLE logistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id VARCHAR(50) REFERENCES orders(id),
    tracking_no VARCHAR(100) UNIQUE,
    status VARCHAR(50) NOT NULL, -- 揽件/运输中/派送中/已签收
    current_location TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4.5 售后表 (after_sales)
DROP TABLE IF EXISTS after_sales CASCADE;
CREATE TABLE after_sales (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id VARCHAR(50) REFERENCES orders(id),
    type VARCHAR(50) NOT NULL, -- 退货 / 换货
    reason TEXT,
    status VARCHAR(50) NOT NULL, -- 处理中 / 已同意 / 已驳回
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
