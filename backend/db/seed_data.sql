-- 设置客户端编码为 UTF8，确保中文正常显示
SET client_encoding = 'UTF8';

-- 插入测试用户 (密码均为: password123, 已通过 bcrypt 哈希)
-- 注意: 实际应用中应通过 API 注册，这里仅为演示
INSERT INTO users (id, username, email, hashed_password) VALUES
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '测试用户1', 'test1@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', '测试用户2', 'test2@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW');

-- 插入测试商品
INSERT INTO products (id, name, price, stock) VALUES
(uuid_generate_v4(), '智能手机 Pro', 5999.00, 100),
(uuid_generate_v4(), '无线降噪耳机', 1299.00, 50),
(uuid_generate_v4(), '机械键盘', 499.00, 30);

-- 插入测试订单
INSERT INTO orders (id, user_id, status, address, contact_email, total_amount) VALUES
('ORD20231027001', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '待发货', '北京市朝阳区望京SOHO', 'test1@example.com', 5999.00),
('ORD20231027002', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '已发货', '上海市浦东新区张江高科', 'test1@example.com', 1299.00);

-- 插入物流信息
INSERT INTO logistics (order_id, tracking_no, status, current_location) VALUES
('ORD20231027002', 'SF123456789', '运输中', '上海分拨中心');
