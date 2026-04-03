-- 设置客户端编码为 UTF8，确保中文正常显示
SET client_encoding = 'UTF8';

-- 插入测试用户 (密码均为: password123, 已通过 bcrypt 哈希)
INSERT INTO users (id, username, email, hashed_password) VALUES
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '测试用户1', 'test1@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', '测试用户2', 'test2@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW');

-- 插入测试商品（用于前台商品浏览）
INSERT INTO products (id, name, description, image_url, category, price, stock, is_active) VALUES
('11111111-1111-1111-1111-111111111001', 'Nova X1 智能手机', '6.8 英寸高刷屏，5000mAh 大电池，适合重度使用场景。', 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=800&q=80', '手机', 4299.00, 80, TRUE),
('11111111-1111-1111-1111-111111111002', 'SilentBuds Pro 降噪耳机', '主动降噪 + 通透模式，支持 30 小时续航。', 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=800&q=80', '音频', 899.00, 120, TRUE),
('11111111-1111-1111-1111-111111111003', 'AeroBook 14 轻薄本', '14 英寸轻薄设计，16GB 内存，1TB SSD。', 'https://images.unsplash.com/photo-1517336714739-489689fd1ca8?auto=format&fit=crop&w=800&q=80', '电脑', 5999.00, 45, TRUE),
('11111111-1111-1111-1111-111111111004', 'Voyager 机械键盘', '全键热插拔，三模连接，适配办公与游戏。', 'https://images.unsplash.com/photo-1511467687858-23d96c32e4ae?auto=format&fit=crop&w=800&q=80', '外设', 499.00, 200, TRUE),
('11111111-1111-1111-1111-111111111005', 'PixelView 27 显示器', '2K 分辨率，165Hz 刷新率，HDR 支持。', 'https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=800&q=80', '显示器', 1699.00, 60, TRUE),
('11111111-1111-1111-1111-111111111006', 'Pulse 智能手表', '全天候心率监测与运动追踪，NFC 快捷支付。', 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80', '穿戴', 1299.00, 90, TRUE);

-- 批量插入推荐算法测试商品（500 条）
INSERT INTO products (name, description, image_url, category, price, stock, is_active)
SELECT
    CASE c.cat
        WHEN '手机' THEN 'Spark 手机 ' || LPAD(i::text, 3, '0')
        WHEN '电脑' THEN 'Aero 笔记本 ' || LPAD(i::text, 3, '0')
        WHEN '音频' THEN 'Echo 音频设备 ' || LPAD(i::text, 3, '0')
        WHEN '外设' THEN 'Matrix 外设 ' || LPAD(i::text, 3, '0')
        WHEN '显示器' THEN 'Vision 显示器 ' || LPAD(i::text, 3, '0')
        WHEN '穿戴' THEN 'Pulse 穿戴设备 ' || LPAD(i::text, 3, '0')
        WHEN '家电' THEN 'Home 家电 ' || LPAD(i::text, 3, '0')
        WHEN '智能家居' THEN 'SmartHome 设备 ' || LPAD(i::text, 3, '0')
        WHEN '摄影' THEN 'Capture 摄影器材 ' || LPAD(i::text, 3, '0')
        WHEN '办公' THEN 'Office 办公设备 ' || LPAD(i::text, 3, '0')
        WHEN '运动户外' THEN 'Trail 运动户外 ' || LPAD(i::text, 3, '0')
        ELSE 'Living 家居用品 ' || LPAD(i::text, 3, '0')
    END AS name,
    CASE c.cat
        WHEN '手机' THEN '支持 5G、快充与高刷新率屏幕，适合日常与娱乐。'
        WHEN '电脑' THEN '轻薄机身与长续航设计，适合办公与学习场景。'
        WHEN '音频' THEN '支持蓝牙连接与降噪模式，兼顾通勤和运动使用。'
        WHEN '外设' THEN '兼容主流设备，稳定耐用，提升桌面交互效率。'
        WHEN '显示器' THEN '高色域和高刷新率组合，覆盖办公与娱乐需求。'
        WHEN '穿戴' THEN '支持健康监测与运动记录，续航表现稳定。'
        WHEN '家电' THEN '节能设计，操作简洁，适配家庭多场景使用。'
        WHEN '智能家居' THEN '支持 APP 远程控制，可联动多种家庭设备。'
        WHEN '摄影' THEN '成像清晰，操作直观，适合入门与进阶用户。'
        WHEN '办公' THEN '针对效率场景优化，提升日常协作体验。'
        WHEN '运动户外' THEN '强调便携和耐用，适配训练与户外活动。'
        ELSE '注重实用与空间利用，适合日常家居搭配。'
    END AS description,
    'https://picsum.photos/seed/rasa-product-' || i || '/800/800' AS image_url,
    c.cat AS category,
    ROUND((299 + ((i * 137) % 4200))::numeric, 2) AS price,
    20 + ((i * 17) % 280) AS stock,
    TRUE AS is_active
FROM generate_series(1, 500) AS gs(i)
CROSS JOIN LATERAL (
    VALUES (
        (ARRAY['手机', '电脑', '音频', '外设', '显示器', '穿戴', '家电', '智能家居', '摄影', '办公', '运动户外', '家居'])[((i - 1) % 12) + 1]
    )
) AS c(cat);

-- 插入测试订单（用于“我的订单”演示）
INSERT INTO orders (id, user_id, status, address, contact_email, total_amount) VALUES
('ORD202603300001', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '待发货', '北京市朝阳区望京SOHO T2', 'test1@example.com', 5198.00),
('ORD202603300002', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '已发货', '上海市浦东新区张江高科园区', 'test1@example.com', 1699.00);

INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal) VALUES
('ORD202603300001', '11111111-1111-1111-1111-111111111001', 'Nova X1 智能手机', 4299.00, 1, 4299.00),
('ORD202603300001', '11111111-1111-1111-1111-111111111002', 'SilentBuds Pro 降噪耳机', 899.00, 1, 899.00),
('ORD202603300002', '11111111-1111-1111-1111-111111111005', 'PixelView 27 显示器', 1699.00, 1, 1699.00);

-- 插入物流信息
INSERT INTO logistics (order_id, tracking_no, status, current_location) VALUES
('ORD202603300002', 'SF123456789', '运输中', '上海分拨中心');
