SET client_encoding = 'UTF8';

-- 所有示例账号密码统一为: password123
INSERT INTO users (id, username, email, hashed_password, role) VALUES
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '测试用户一', 'test1@example.com', crypt('password123', gen_salt('bf', 12)), 'customer'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', '测试用户二', 'test2@example.com', crypt('password123', gen_salt('bf', 12)), 'customer'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a21', '商家甲', 'merchant1@example.com', crypt('password123', gen_salt('bf', 12)), 'merchant'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', '商家乙', 'merchant2@example.com', crypt('password123', gen_salt('bf', 12)), 'merchant');

INSERT INTO shops (id, owner_user_id, name, description, contact_email, contact_phone, is_active) VALUES
('00000000-0000-0000-0000-000000000301', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a21', '星河数码旗舰店', '主营手机、电脑与数码配件', 'merchant1@example.com', '13800000001', TRUE),
('00000000-0000-0000-0000-000000000302', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', '青禾智家生活馆', '主营家居电器与智能设备', 'merchant2@example.com', '13800000002', TRUE);

INSERT INTO shop_addresses (id, shop_id, label, contact_name, contact_phone, province, city, district, address_line, postal_code, is_default) VALUES
('00000000-0000-0000-0000-000000000401', '00000000-0000-0000-0000-000000000301', '北京主仓', '张三', '13800000001', '北京市', '北京市', '朝阳区', '望京 SOHO T2 18层', '100102', TRUE),
('00000000-0000-0000-0000-000000000402', '00000000-0000-0000-0000-000000000301', '上海备货仓', '李四', '13800000003', '上海市', '上海市', '浦东新区', '张江高科技园区 A 栋', '200120', FALSE),
('00000000-0000-0000-0000-000000000403', '00000000-0000-0000-0000-000000000302', '广州主仓', '王五', '13800000002', '广东省', '广州市', '天河区', '天河软件园 6层', '510630', TRUE);

INSERT INTO products (id, shop_id, name, description, image_url, category, price, stock, is_active) VALUES
('11111111-1111-1111-1111-111111111001', '00000000-0000-0000-0000-000000000301', '星云 X1 智能手机', '6.8 英寸高刷屏，5000mAh 大电池', 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=800&q=80', '手机', 4299.00, 80, TRUE),
('11111111-1111-1111-1111-111111111002', '00000000-0000-0000-0000-000000000301', '静音豆 Pro 耳机', '主动降噪，综合续航约 30 小时', 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=800&q=80', '音频', 899.00, 120, TRUE),
('11111111-1111-1111-1111-111111111003', '00000000-0000-0000-0000-000000000301', '轻羽 14 笔记本', '轻薄机身，适合办公学习', 'https://images.unsplash.com/photo-1517336714739-489689fd1ca8?auto=format&fit=crop&w=800&q=80', '电脑', 5999.00, 45, TRUE),
('11111111-1111-1111-1111-111111111004', '00000000-0000-0000-0000-000000000301', '航行者机械键盘', '全键热插拔，三模连接', 'https://images.unsplash.com/photo-1511467687858-23d96c32e4ae?auto=format&fit=crop&w=800&q=80', '外设', 499.00, 200, TRUE),
('11111111-1111-1111-1111-111111111005', '00000000-0000-0000-0000-000000000302', '视界 27 显示器', '2K 165Hz，支持 HDR', 'https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=800&q=80', '显示器', 1699.00, 60, TRUE),
('11111111-1111-1111-1111-111111111006', '00000000-0000-0000-0000-000000000302', '脉冲智能手表', '全天健康监测与运动追踪', 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80', '穿戴', 1299.00, 90, TRUE);

-- 500 条推荐算法测试商品（带店铺关联）
INSERT INTO products (shop_id, name, description, image_url, category, price, stock, is_active)
SELECT
    CASE WHEN i % 2 = 0 THEN '00000000-0000-0000-0000-000000000301'::UUID ELSE '00000000-0000-0000-0000-000000000302'::UUID END AS shop_id,
    CASE c.cat
        WHEN '手机' THEN '星火手机 ' || LPAD(i::text, 3, '0')
        WHEN '电脑' THEN '凌风笔记本 ' || LPAD(i::text, 3, '0')
        WHEN '音频' THEN '回声音频设备 ' || LPAD(i::text, 3, '0')
        WHEN '外设' THEN '矩阵外设 ' || LPAD(i::text, 3, '0')
        WHEN '显示器' THEN '视野显示器 ' || LPAD(i::text, 3, '0')
        WHEN '穿戴' THEN '脉动穿戴设备 ' || LPAD(i::text, 3, '0')
        WHEN '家电' THEN '居家电器 ' || LPAD(i::text, 3, '0')
        WHEN '智能家居' THEN '智家设备 ' || LPAD(i::text, 3, '0')
        WHEN '摄影' THEN '影像器材 ' || LPAD(i::text, 3, '0')
        WHEN '办公' THEN '办公工具 ' || LPAD(i::text, 3, '0')
        WHEN '户外' THEN '户外装备 ' || LPAD(i::text, 3, '0')
        ELSE '生活好物 ' || LPAD(i::text, 3, '0')
    END AS name,
    '自动生成测试商品 #' || i || '，用于推荐算法调试。' AS description,
    'https://picsum.photos/seed/rasa-product-' || i || '/800/800' AS image_url,
    c.cat AS category,
    ROUND((299 + ((i * 137) % 4200))::numeric, 2) AS price,
    20 + ((i * 17) % 280) AS stock,
    TRUE AS is_active
FROM generate_series(1, 500) AS gs(i)
CROSS JOIN LATERAL (
    VALUES (
        (ARRAY['手机', '电脑', '音频', '外设', '显示器', '穿戴', '家电', '智能家居', '摄影', '办公', '户外', '家居'])[((i - 1) % 12) + 1]
    )
) AS c(cat);

-- 注意：status 字段保持英文枚举，避免影响后端筛选逻辑
INSERT INTO orders (id, user_id, shop_id, status, address, contact_email, total_amount) VALUES
('ORD202603300001', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '00000000-0000-0000-0000-000000000301', 'pending_shipment', '北京市朝阳区望京 SOHO T2', 'test1@example.com', 5198.00),
('ORD202603300002', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '00000000-0000-0000-0000-000000000302', 'shipped', '上海市浦东新区张江高科', 'test1@example.com', 1699.00);

INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal) VALUES
('ORD202603300001', '11111111-1111-1111-1111-111111111001', '星云 X1 智能手机', 4299.00, 1, 4299.00),
('ORD202603300001', '11111111-1111-1111-1111-111111111002', '静音豆 Pro 耳机', 899.00, 1, 899.00),
('ORD202603300002', '11111111-1111-1111-1111-111111111005', '视界 27 显示器', 1699.00, 1, 1699.00);

INSERT INTO logistics (order_id, shipped_from_address_id, tracking_no, status, current_location, estimated_delivery_at, route_plan, llm_raw_text) VALUES
(
    'ORD202603300002',
    '00000000-0000-0000-0000-000000000403',
    'SF123456789',
    'in_transit',
    '上海分拨中心',
    NOW() + INTERVAL '2 days',
    '["广州中转中心", "杭州中转站", "上海分拨中心"]'::jsonb,
    '示例物流预测文本（种子数据）'
);
