SET client_encoding = 'UTF8';

-- 所有示例账号密码统一为: password123
INSERT INTO users (id, username, email, hashed_password, role) VALUES
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '测试用户一', 'test1@example.com', crypt('password123', gen_salt('bf', 12)), 'customer'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', '测试用户二', 'test2@example.com', crypt('password123', gen_salt('bf', 12)), 'customer'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a21', '商家甲', 'merchant1@example.com', crypt('password123', gen_salt('bf', 12)), 'merchant'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', '商家乙', 'merchant2@example.com', crypt('password123', gen_salt('bf', 12)), 'merchant'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a23', '商家丙', 'merchant3@example.com', crypt('password123', gen_salt('bf', 12)), 'merchant'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a24', '商家丁', 'merchant4@example.com', crypt('password123', gen_salt('bf', 12)), 'merchant'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a25', '商家戊', 'merchant5@example.com', crypt('password123', gen_salt('bf', 12)), 'merchant'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a26', '商家己', 'merchant6@example.com', crypt('password123', gen_salt('bf', 12)), 'merchant'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a27', '商家庚', 'merchant7@example.com', crypt('password123', gen_salt('bf', 12)), 'merchant');

INSERT INTO shops (
    id,
    owner_user_id,
    name,
    description,
    contact_email,
    contact_phone,
    logo_url,
    rating,
    service_score,
    logistics_score,
    after_sales_score,
    shipping_city,
    featured_categories,
    service_tags,
    is_active
) VALUES
(
    '00000000-0000-0000-0000-000000000301',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a21',
    '星河数码旗舰店',
    '主营手机、电脑与桌面外设，强调性能与到手体验。',
    'merchant1@example.com',
    '13800000001',
    'https://picsum.photos/seed/shop-star-river/200/200',
    4.8,
    4.9,
    4.7,
    4.8,
    '北京',
    '["手机", "电脑", "外设"]'::jsonb,
    '["次日达", "官方质保", "以旧换新"]'::jsonb,
    TRUE
),
(
    '00000000-0000-0000-0000-000000000302',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
    '青禾智家生活馆',
    '覆盖家电与智能家居，主打静音、节能和家庭自动化。',
    'merchant2@example.com',
    '13800000002',
    'https://picsum.photos/seed/shop-green-home/200/200',
    4.7,
    4.8,
    4.6,
    4.7,
    '广州',
    '["家电", "智能家居"]'::jsonb,
    '["安装指导", "整屋联动", "节能推荐"]'::jsonb,
    TRUE
),
(
    '00000000-0000-0000-0000-000000000303',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a23',
    '极昼办公装备店',
    '面向办公与会议协作场景，覆盖桌面设备、显示器和商务电脑。',
    'merchant3@example.com',
    '13800000003',
    'https://picsum.photos/seed/shop-polar-office/200/200',
    4.6,
    4.8,
    4.7,
    4.6,
    '上海',
    '["办公", "显示器", "电脑"]'::jsonb,
    '["企业采购", "发票齐全", "会议场景方案"]'::jsonb,
    TRUE
),
(
    '00000000-0000-0000-0000-000000000304',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a24',
    '光谱影音专营店',
    '专注音频、显示器与摄影设备，适合内容创作和影音娱乐。',
    'merchant4@example.com',
    '13800000004',
    'https://picsum.photos/seed/shop-spectrum-media/200/200',
    4.7,
    4.7,
    4.8,
    4.6,
    '深圳',
    '["音频", "显示器", "摄影"]'::jsonb,
    '["创作套装", "专业调校", "直播友好"]'::jsonb,
    TRUE
),
(
    '00000000-0000-0000-0000-000000000305',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a25',
    '山系户外精选店',
    '覆盖露营、徒步和运动穿戴，强调轻量、耐候与舒适性。',
    'merchant5@example.com',
    '13800000005',
    'https://picsum.photos/seed/shop-mountain-outdoor/200/200',
    4.5,
    4.6,
    4.8,
    4.5,
    '成都',
    '["户外", "穿戴"]'::jsonb,
    '["户外咨询", "装备搭配", "耐候测试"]'::jsonb,
    TRUE
),
(
    '00000000-0000-0000-0000-000000000306',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a26',
    '沐川厨房电器馆',
    '聚焦厨房电器与收纳好物，面向居家烹饪和高频厨房整理。',
    'merchant6@example.com',
    '13800000006',
    'https://picsum.photos/seed/shop-muchuan-kitchen/200/200',
    4.6,
    4.7,
    4.6,
    4.8,
    '杭州',
    '["家电", "家居"]'::jsonb,
    '["厨房改造", "套系搭配", "保养建议"]'::jsonb,
    TRUE
),
(
    '00000000-0000-0000-0000-000000000307',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a27',
    '脉搏健康穿戴馆',
    '以健康监测、居家看护和轻量康复设备为核心。',
    'merchant7@example.com',
    '13800000007',
    'https://picsum.photos/seed/shop-pulse-health/200/200',
    4.8,
    4.9,
    4.6,
    4.8,
    '南京',
    '["穿戴", "智能家居"]'::jsonb,
    '["健康监测", "长辈看护", "睡眠场景"]'::jsonb,
    TRUE
);

INSERT INTO shop_addresses (
    id,
    shop_id,
    label,
    contact_name,
    contact_phone,
    province,
    city,
    district,
    address_line,
    postal_code,
    is_default
) VALUES
('00000000-0000-0000-0000-000000000401', '00000000-0000-0000-0000-000000000301', '北京主仓', '张三', '13800000001', '北京市', '北京市', '朝阳区', '望京 SOHO T2 18层', '100102', TRUE),
('00000000-0000-0000-0000-000000000402', '00000000-0000-0000-0000-000000000302', '广州主仓', '李四', '13800000002', '广东省', '广州市', '天河区', '天河软件园 6层', '510630', TRUE),
('00000000-0000-0000-0000-000000000403', '00000000-0000-0000-0000-000000000303', '上海主仓', '王五', '13800000003', '上海市', '上海市', '浦东新区', '张江高科技园区 A 栋', '200120', TRUE),
('00000000-0000-0000-0000-000000000404', '00000000-0000-0000-0000-000000000304', '深圳主仓', '赵六', '13800000004', '广东省', '深圳市', '南山区', '科技园南区 9 栋', '518057', TRUE),
('00000000-0000-0000-0000-000000000405', '00000000-0000-0000-0000-000000000305', '成都主仓', '陈七', '13800000005', '四川省', '成都市', '武侯区', '天府大道北段 88 号', '610041', TRUE),
('00000000-0000-0000-0000-000000000406', '00000000-0000-0000-0000-000000000306', '杭州主仓', '周八', '13800000006', '浙江省', '杭州市', '滨江区', '网商路 699 号', '310052', TRUE),
('00000000-0000-0000-0000-000000000407', '00000000-0000-0000-0000-000000000307', '南京主仓', '吴九', '13800000007', '江苏省', '南京市', '建邺区', '江东中路 333 号', '210019', TRUE);

WITH product_specs (sort_no, shop_id, category, name, brand, model) AS (
    VALUES
    -- 星河数码旗舰店
    (1, '00000000-0000-0000-0000-000000000301'::uuid, '手机', '星云 X1 智能手机', '星河', 'X1'),
    (2, '00000000-0000-0000-0000-000000000301'::uuid, '手机', '星云 X1 Pro 智能手机', '星河', 'X1 Pro'),
    (3, '00000000-0000-0000-0000-000000000301'::uuid, '手机', '星云 X1 Ultra 智能手机', '星河', 'X1 Ultra'),
    (4, '00000000-0000-0000-0000-000000000301'::uuid, '手机', '曜石 Note Air 手机', '曜石', 'Note Air'),
    (5, '00000000-0000-0000-0000-000000000301'::uuid, '手机', '曜石 Note Max 手机', '曜石', 'Note Max'),
    (6, '00000000-0000-0000-0000-000000000301'::uuid, '手机', '极光 Fold 轻薄折叠屏', '极光', 'Fold'),
    (7, '00000000-0000-0000-0000-000000000301'::uuid, '电脑', '轻羽 14 笔记本', '轻羽', '14'),
    (8, '00000000-0000-0000-0000-000000000301'::uuid, '电脑', '轻羽 14 Pro 笔记本', '轻羽', '14 Pro'),
    (9, '00000000-0000-0000-0000-000000000301'::uuid, '电脑', '凌风 16 创作本', '凌风', '16 Creator'),
    (10, '00000000-0000-0000-0000-000000000301'::uuid, '电脑', '凌风 16 Max 游戏本', '凌风', '16 Max'),
    (11, '00000000-0000-0000-0000-000000000301'::uuid, '电脑', '星河 Mini 主机', '星河', 'Mini Station'),
    (12, '00000000-0000-0000-0000-000000000301'::uuid, '外设', '航行者机械键盘', '航行者', 'MK87'),
    (13, '00000000-0000-0000-0000-000000000301'::uuid, '外设', '航行者静音键盘', '航行者', 'Silent75'),
    (14, '00000000-0000-0000-0000-000000000301'::uuid, '外设', '星跃双模鼠标', '星跃', 'DualMouse'),
    (15, '00000000-0000-0000-0000-000000000301'::uuid, '外设', '星跃 2K 摄像头', '星跃', 'Cam 2K'),
    (16, '00000000-0000-0000-0000-000000000301'::uuid, '外设', '霓光拓展坞', '霓光', 'Dock 11-in-1'),

    -- 青禾智家生活馆
    (1, '00000000-0000-0000-0000-000000000302'::uuid, '家电', '青禾净护空气净化器', '青禾', 'Air Pure'),
    (2, '00000000-0000-0000-0000-000000000302'::uuid, '家电', '青禾鲜氧加湿器', '青禾', 'Mist Plus'),
    (3, '00000000-0000-0000-0000-000000000302'::uuid, '家电', '青禾舒眠除湿机', '青禾', 'Dry Care'),
    (4, '00000000-0000-0000-0000-000000000302'::uuid, '家电', '青禾小暖风取暖器', '青禾', 'Warm Mini'),
    (5, '00000000-0000-0000-0000-000000000302'::uuid, '家电', '澜庭轻音扫地机', '澜庭', 'Sweep S1'),
    (6, '00000000-0000-0000-0000-000000000302'::uuid, '家电', '澜庭手持吸尘器', '澜庭', 'Vac H2'),
    (7, '00000000-0000-0000-0000-000000000302'::uuid, '家电', '智舍即热饮水机', '智舍', 'Hot Flow'),
    (8, '00000000-0000-0000-0000-000000000302'::uuid, '家电', '智舍静音循环扇', '智舍', 'Wind Loop'),
    (9, '00000000-0000-0000-0000-000000000302'::uuid, '智能家居', '青禾智能门锁', '青禾', 'Lock Pro'),
    (10, '00000000-0000-0000-0000-000000000302'::uuid, '智能家居', '青禾智能门铃', '青禾', 'Door Bell'),
    (11, '00000000-0000-0000-0000-000000000302'::uuid, '智能家居', '智舍中控屏', '智舍', 'Hub Screen'),
    (12, '00000000-0000-0000-0000-000000000302'::uuid, '智能家居', '智舍光感台灯', '智舍', 'Light Sense'),
    (13, '00000000-0000-0000-0000-000000000302'::uuid, '智能家居', '智舍人体传感器', '智舍', 'Motion One'),
    (14, '00000000-0000-0000-0000-000000000302'::uuid, '智能家居', '澜庭智能窗帘电机', '澜庭', 'Curtain Drive'),
    (15, '00000000-0000-0000-0000-000000000302'::uuid, '智能家居', '澜庭温湿度传感器', '澜庭', 'Climate Tag'),
    (16, '00000000-0000-0000-0000-000000000302'::uuid, '智能家居', '青禾家庭安防套装', '青禾', 'Safe Home Kit'),

    -- 极昼办公装备店
    (1, '00000000-0000-0000-0000-000000000303'::uuid, '办公', '极昼升降办公桌', '极昼', 'Desk Lift'),
    (2, '00000000-0000-0000-0000-000000000303'::uuid, '办公', '极昼人体工学椅', '极昼', 'Chair Pro'),
    (3, '00000000-0000-0000-0000-000000000303'::uuid, '办公', '极昼文档扫描仪', '极昼', 'Scan S2'),
    (4, '00000000-0000-0000-0000-000000000303'::uuid, '办公', '墨舟便携打印机', '墨舟', 'Print Go'),
    (5, '00000000-0000-0000-0000-000000000303'::uuid, '办公', '墨舟高速碎纸机', '墨舟', 'Cut 12'),
    (6, '00000000-0000-0000-0000-000000000303'::uuid, '办公', '白塔会议拾音麦', '白塔', 'Voice Meet'),
    (7, '00000000-0000-0000-0000-000000000303'::uuid, '显示器', '极昼 27 办公显示器', '极昼', 'View 27'),
    (8, '00000000-0000-0000-0000-000000000303'::uuid, '显示器', '极昼 32 4K 显示器', '极昼', 'View 32 4K'),
    (9, '00000000-0000-0000-0000-000000000303'::uuid, '显示器', '白塔 24 护眼显示器', '白塔', 'Care 24'),
    (10, '00000000-0000-0000-0000-000000000303'::uuid, '显示器', '白塔 34 带鱼屏', '白塔', 'Wide 34'),
    (11, '00000000-0000-0000-0000-000000000303'::uuid, '显示器', '墨舟 29 超宽屏', '墨舟', 'Ultra 29'),
    (12, '00000000-0000-0000-0000-000000000303'::uuid, '电脑', '极昼商务本 14', '极昼', 'Biz 14'),
    (13, '00000000-0000-0000-0000-000000000303'::uuid, '电脑', '极昼商务本 16', '极昼', 'Biz 16'),
    (14, '00000000-0000-0000-0000-000000000303'::uuid, '电脑', '白塔轻会议一体机', '白塔', 'Allin Meet'),
    (15, '00000000-0000-0000-0000-000000000303'::uuid, '电脑', '墨舟迷你办公主机', '墨舟', 'Mini Desk'),
    (16, '00000000-0000-0000-0000-000000000303'::uuid, '电脑', '极昼静音工作站', '极昼', 'Workstation S'),

    -- 光谱影音专营店
    (1, '00000000-0000-0000-0000-000000000304'::uuid, '音频', '回声 Studio 头戴耳机', '回声', 'Studio'),
    (2, '00000000-0000-0000-0000-000000000304'::uuid, '音频', '回声 Air 真无线耳机', '回声', 'Air'),
    (3, '00000000-0000-0000-0000-000000000304'::uuid, '音频', '回声播客麦克风', '回声', 'Mic Pro'),
    (4, '00000000-0000-0000-0000-000000000304'::uuid, '音频', '光谱书架音箱', '光谱', 'Sound 5'),
    (5, '00000000-0000-0000-0000-000000000304'::uuid, '音频', '光谱回音壁', '光谱', 'Bar Max'),
    (6, '00000000-0000-0000-0000-000000000304'::uuid, '音频', '光谱桌面 DAC 解码耳放', '光谱', 'DAC One'),
    (7, '00000000-0000-0000-0000-000000000304'::uuid, '显示器', '曜视 27 电竞显示器', '曜视', 'Game 27'),
    (8, '00000000-0000-0000-0000-000000000304'::uuid, '显示器', '曜视 32 MiniLED 显示器', '曜视', 'MiniLED 32'),
    (9, '00000000-0000-0000-0000-000000000304'::uuid, '显示器', '曜视 49 双 QHD 带鱼屏', '曜视', 'Wide 49'),
    (10, '00000000-0000-0000-0000-000000000304'::uuid, '显示器', '光谱参考级调色屏', '光谱', 'Color Pro'),
    (11, '00000000-0000-0000-0000-000000000304'::uuid, '显示器', '光谱便携副屏', '光谱', 'Side 16'),
    (12, '00000000-0000-0000-0000-000000000304'::uuid, '摄影', '影拓 4K 运动相机', '影拓', 'Action 4K'),
    (13, '00000000-0000-0000-0000-000000000304'::uuid, '摄影', '影拓 24-70mm 标准变焦镜头', '影拓', 'Lens 24-70'),
    (14, '00000000-0000-0000-0000-000000000304'::uuid, '摄影', '影拓 Vlog 微单相机', '影拓', 'Vlog M1'),
    (15, '00000000-0000-0000-0000-000000000304'::uuid, '摄影', '影拓碳纤维三脚架', '影拓', 'Tripod Carbon'),
    (16, '00000000-0000-0000-0000-000000000304'::uuid, '摄影', '光谱补光直播灯', '光谱', 'Light Live'),

    -- 山系户外精选店
    (1, '00000000-0000-0000-0000-000000000305'::uuid, '户外', '山系轻量帐篷', '山系', 'Tent Lite'),
    (2, '00000000-0000-0000-0000-000000000305'::uuid, '户外', '山系羽绒睡袋', '山系', 'Sleep Warm'),
    (3, '00000000-0000-0000-0000-000000000305'::uuid, '户外', '远川徒步背包 35L', '远川', 'Pack 35'),
    (4, '00000000-0000-0000-0000-000000000305'::uuid, '户外', '远川徒步背包 55L', '远川', 'Pack 55'),
    (5, '00000000-0000-0000-0000-000000000305'::uuid, '户外', 'TrailPeak 登山杖', 'TrailPeak', 'Pole Carbon'),
    (6, '00000000-0000-0000-0000-000000000305'::uuid, '户外', 'TrailPeak 折叠营地车', 'TrailPeak', 'Camp Wagon'),
    (7, '00000000-0000-0000-0000-000000000305'::uuid, '户外', '山系露营天幕', '山系', 'Shade Pro'),
    (8, '00000000-0000-0000-0000-000000000305'::uuid, '户外', '远川户外保温壶', '远川', 'Bottle 1L'),
    (9, '00000000-0000-0000-0000-000000000305'::uuid, '穿戴', 'TrailPeak 越野跑手表', 'TrailPeak', 'Run Watch'),
    (10, '00000000-0000-0000-0000-000000000305'::uuid, '穿戴', 'TrailPeak 太阳能手表', 'TrailPeak', 'Solar Watch'),
    (11, '00000000-0000-0000-0000-000000000305'::uuid, '穿戴', '山系防水冲锋衣', '山系', 'Shell Pro'),
    (12, '00000000-0000-0000-0000-000000000305'::uuid, '穿戴', '山系速干徒步鞋', '山系', 'Hike Flow'),
    (13, '00000000-0000-0000-0000-000000000305'::uuid, '穿戴', '远川抓绒中层', '远川', 'Fleece Mid'),
    (14, '00000000-0000-0000-0000-000000000305'::uuid, '穿戴', '远川轻量羽绒服', '远川', 'Down Lite'),
    (15, '00000000-0000-0000-0000-000000000305'::uuid, '穿戴', '山系保暖帽围套装', '山系', 'Warm Set'),
    (16, '00000000-0000-0000-0000-000000000305'::uuid, '穿戴', 'TrailPeak 运动护膝', 'TrailPeak', 'Knee Guard'),

    -- 沐川厨房电器馆
    (1, '00000000-0000-0000-0000-000000000306'::uuid, '家电', '沐川轻养破壁机', '沐川', 'Blend Max'),
    (2, '00000000-0000-0000-0000-000000000306'::uuid, '家电', '沐川蒸汽空气炸锅', '沐川', 'Air Steam'),
    (3, '00000000-0000-0000-0000-000000000306'::uuid, '家电', '沐川双胆电饭煲', '沐川', 'Rice Duo'),
    (4, '00000000-0000-0000-0000-000000000306'::uuid, '家电', '沐川静音洗碗机', '沐川', 'Dish Quiet'),
    (5, '00000000-0000-0000-0000-000000000306'::uuid, '家电', '纯岸家用净水器', '纯岸', 'Pure Water'),
    (6, '00000000-0000-0000-0000-000000000306'::uuid, '家电', '纯岸嵌入式烤箱', '纯岸', 'Bake Fit'),
    (7, '00000000-0000-0000-0000-000000000306'::uuid, '家电', '厨光多功能料理锅', '厨光', 'Cook Pot'),
    (8, '00000000-0000-0000-0000-000000000306'::uuid, '家电', '厨光恒温电热水壶', '厨光', 'Warm Kettle'),
    (9, '00000000-0000-0000-0000-000000000306'::uuid, '家居', '沐川原木刀具套装', '沐川', 'Knife Set'),
    (10, '00000000-0000-0000-0000-000000000306'::uuid, '家居', '沐川抗菌砧板', '沐川', 'Board Pro'),
    (11, '00000000-0000-0000-0000-000000000306'::uuid, '家居', '纯岸真空保鲜盒组', '纯岸', 'Fresh Box'),
    (12, '00000000-0000-0000-0000-000000000306'::uuid, '家居', '纯岸厨房置物架', '纯岸', 'Rack Plus'),
    (13, '00000000-0000-0000-0000-000000000306'::uuid, '家居', '厨光珐琅汤锅', '厨光', 'Soup Pot'),
    (14, '00000000-0000-0000-0000-000000000306'::uuid, '家居', '厨光不粘炒锅', '厨光', 'Pan 32'),
    (15, '00000000-0000-0000-0000-000000000306'::uuid, '家居', '沐川餐具消毒收纳柜', '沐川', 'Steri Cabinet'),
    (16, '00000000-0000-0000-0000-000000000306'::uuid, '家居', '纯岸调味收纳套装', '纯岸', 'Spice Kit'),

    -- 脉搏健康穿戴馆
    (1, '00000000-0000-0000-0000-000000000307'::uuid, '穿戴', '脉搏健康手表 Pro', '脉搏', 'Watch Pro'),
    (2, '00000000-0000-0000-0000-000000000307'::uuid, '穿戴', '脉搏健康手表 Air', '脉搏', 'Watch Air'),
    (3, '00000000-0000-0000-0000-000000000307'::uuid, '穿戴', '脉搏 ECG 心电手环', '脉搏', 'ECG Band'),
    (4, '00000000-0000-0000-0000-000000000307'::uuid, '穿戴', '灵跃睡眠监测戒指', '灵跃', 'Sleep Ring'),
    (5, '00000000-0000-0000-0000-000000000307'::uuid, '穿戴', '灵跃血氧手环', '灵跃', 'O2 Band'),
    (6, '00000000-0000-0000-0000-000000000307'::uuid, '穿戴', '脉搏家庭体脂秤', '脉搏', 'Scale Plus'),
    (7, '00000000-0000-0000-0000-000000000307'::uuid, '穿戴', '安眠热敷护眼仪', '安眠', 'Eye Warm'),
    (8, '00000000-0000-0000-0000-000000000307'::uuid, '穿戴', '灵跃筋膜枪 Mini', '灵跃', 'Gun Mini'),
    (9, '00000000-0000-0000-0000-000000000307'::uuid, '穿戴', '脉搏颈部按摩仪', '脉搏', 'Neck Care'),
    (10, '00000000-0000-0000-0000-000000000307'::uuid, '穿戴', '安眠白噪音助眠仪', '安眠', 'Sleep Noise'),
    (11, '00000000-0000-0000-0000-000000000307'::uuid, '智能家居', '脉搏健康中控屏', '脉搏', 'Health Hub'),
    (12, '00000000-0000-0000-0000-000000000307'::uuid, '智能家居', '脉搏跌倒监测雷达', '脉搏', 'Fall Guard'),
    (13, '00000000-0000-0000-0000-000000000307'::uuid, '智能家居', '灵跃用药提醒器', '灵跃', 'Med Timer'),
    (14, '00000000-0000-0000-0000-000000000307'::uuid, '智能家居', '安眠卧室氛围灯', '安眠', 'Mood Light'),
    (15, '00000000-0000-0000-0000-000000000307'::uuid, '智能家居', '脉搏空气质量传感器', '脉搏', 'Air Sense'),
    (16, '00000000-0000-0000-0000-000000000307'::uuid, '智能家居', '灵跃老人看护摄像头', '灵跃', 'Care Cam')
),
ranked AS (
    SELECT
        sort_no,
        shop_id,
        category,
        name,
        brand,
        model,
        CASE shop_id
            WHEN '00000000-0000-0000-0000-000000000301'::uuid THEN 1
            WHEN '00000000-0000-0000-0000-000000000302'::uuid THEN 2
            WHEN '00000000-0000-0000-0000-000000000303'::uuid THEN 3
            WHEN '00000000-0000-0000-0000-000000000304'::uuid THEN 4
            WHEN '00000000-0000-0000-0000-000000000305'::uuid THEN 5
            WHEN '00000000-0000-0000-0000-000000000306'::uuid THEN 6
            ELSE 7
        END AS shop_no,
        CASE shop_id
            WHEN '00000000-0000-0000-0000-000000000301'::uuid THEN 'SG'
            WHEN '00000000-0000-0000-0000-000000000302'::uuid THEN 'QH'
            WHEN '00000000-0000-0000-0000-000000000303'::uuid THEN 'JZ'
            WHEN '00000000-0000-0000-0000-000000000304'::uuid THEN 'GP'
            WHEN '00000000-0000-0000-0000-000000000305'::uuid THEN 'SX'
            WHEN '00000000-0000-0000-0000-000000000306'::uuid THEN 'MC'
            ELSE 'MB'
        END AS shop_code,
        ROW_NUMBER() OVER (PARTITION BY shop_id, category ORDER BY sort_no) AS cat_item_no
    FROM product_specs
),
enriched AS (
    SELECT
        shop_id,
        name,
        CASE category
            WHEN '手机' THEN name || '主打影像、续航与快充平衡，适合通勤和日常娱乐。'
            WHEN '电脑' THEN name || '兼顾性能与便携，适合办公、创作或桌面主力机位。'
            WHEN '外设' THEN name || '围绕桌面效率和连接稳定性设计，适合高频办公与直播。'
            WHEN '家电' THEN name || '强调静音、能效和易清洁，适合家庭高频使用。'
            WHEN '智能家居' THEN name || '支持联动与自动化，适合打造整屋智能场景。'
            WHEN '办公' THEN name || '突出人体工学和耐用性，适合长时间办公与协作。'
            WHEN '显示器' THEN name || '强调屏幕素质和接口完整度，覆盖办公、电竞与创作。'
            WHEN '音频' THEN name || '适合通勤听音、桌面监听和直播录音，强调解析与稳定。'
            WHEN '摄影' THEN name || '面向 Vlog、直播和旅行创作，兼顾画质和携带便利。'
            WHEN '户外' THEN name || '强调轻量、耐候与收纳效率，适合露营与徒步使用。'
            WHEN '穿戴' THEN name || '聚焦全天佩戴舒适度与健康监测，适合持续记录。'
            ELSE name || '兼顾材质质感与居家收纳效率，适合厨房和生活整理。'
        END AS description,
        CASE category
            WHEN '手机' THEN 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=800&q=80'
            WHEN '电脑' THEN 'https://images.unsplash.com/photo-1517336714739-489689fd1ca8?auto=format&fit=crop&w=800&q=80'
            WHEN '外设' THEN 'https://images.unsplash.com/photo-1511467687858-23d96c32e4ae?auto=format&fit=crop&w=800&q=80'
            WHEN '家电' THEN 'https://images.unsplash.com/photo-1586201375761-83865001e31c?auto=format&fit=crop&w=800&q=80'
            WHEN '智能家居' THEN 'https://images.unsplash.com/photo-1558002038-1055907df827?auto=format&fit=crop&w=800&q=80'
            WHEN '办公' THEN 'https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=800&q=80'
            WHEN '显示器' THEN 'https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=800&q=80'
            WHEN '音频' THEN 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=800&q=80'
            WHEN '摄影' THEN 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=800&q=80'
            WHEN '户外' THEN 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=800&q=80'
            WHEN '穿戴' THEN 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80'
            ELSE 'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=800&q=80'
        END AS image_url,
        category,
        brand,
        model,
        shop_code || '-' || LPAD(sort_no::text, 3, '0') AS sku_code,
        ROUND((
            CASE category
                WHEN '手机' THEN 3299
                WHEN '电脑' THEN 4999
                WHEN '外设' THEN 229
                WHEN '家电' THEN 499
                WHEN '智能家居' THEN 259
                WHEN '办公' THEN 359
                WHEN '显示器' THEN 1399
                WHEN '音频' THEN 399
                WHEN '摄影' THEN 899
                WHEN '户外' THEN 229
                WHEN '穿戴' THEN 299
                ELSE 99
            END
            + sort_no * 88
            + cat_item_no * 35
            + shop_no * 12
            + CASE category
                WHEN '电脑' THEN 900
                WHEN '显示器' THEN 600
                WHEN '摄影' THEN 450
                WHEN '家电' THEN 350
                ELSE 0
            END
        )::numeric, 2) AS price,
        ROUND((
            CASE category
                WHEN '手机' THEN 3299
                WHEN '电脑' THEN 4999
                WHEN '外设' THEN 229
                WHEN '家电' THEN 499
                WHEN '智能家居' THEN 259
                WHEN '办公' THEN 359
                WHEN '显示器' THEN 1399
                WHEN '音频' THEN 399
                WHEN '摄影' THEN 899
                WHEN '户外' THEN 229
                WHEN '穿戴' THEN 299
                ELSE 99
            END
            + sort_no * 88
            + cat_item_no * 35
            + shop_no * 12
            + CASE category
                WHEN '电脑' THEN 900
                WHEN '显示器' THEN 600
                WHEN '摄影' THEN 450
                WHEN '家电' THEN 350
                ELSE 0
            END
            + CASE
                WHEN category IN ('外设', '家居') THEN 120
                ELSE 260
            END
        )::numeric, 2) AS original_price,
        ROUND(LEAST(4.9::numeric, 4.1::numeric + (((sort_no + cat_item_no + shop_no) % 8) * 0.1)::numeric), 1) AS rating,
        120 + sort_no * 37 + cat_item_no * 13 + shop_no * 11 AS review_count,
        90 + sort_no * 61 + cat_item_no * 27 + shop_no * 15 AS monthly_sales,
        (ARRAY[6, 12, 24, 36, 48])[1 + ((sort_no + shop_no) % 5)] AS ship_in_hours,
        CASE
            WHEN category IN ('手机', '电脑', '显示器', '家电', '智能家居', '摄影') THEN 365
            ELSE 180
        END AS warranty_days,
        CASE category
            WHEN '手机' THEN jsonb_build_array(brand, '高刷屏', '快充')
            WHEN '电脑' THEN jsonb_build_array(brand, '高性能', '长续航')
            WHEN '外设' THEN jsonb_build_array(brand, '桌面升级', '多设备切换')
            WHEN '家电' THEN jsonb_build_array(brand, '节能运行', '低噪使用')
            WHEN '智能家居' THEN jsonb_build_array(brand, '场景联动', '远程控制')
            WHEN '办公' THEN jsonb_build_array(brand, '人体工学', '高效协作')
            WHEN '显示器' THEN jsonb_build_array(brand, '高分辨率', '多接口')
            WHEN '音频' THEN jsonb_build_array(brand, '高解析', '低延迟')
            WHEN '摄影' THEN jsonb_build_array(brand, '创作友好', '轻量便携')
            WHEN '户外' THEN jsonb_build_array(brand, '轻量化', '耐候材质')
            WHEN '穿戴' THEN jsonb_build_array(brand, '全天佩戴', '健康监测')
            ELSE jsonb_build_array(brand, '耐用材质', '易清洁')
        END AS tags,
        CASE category
            WHEN '手机' THEN jsonb_build_array('型号 ' || model, '高亮直屏', '5000mAh 级续航')
            WHEN '电脑' THEN jsonb_build_array('型号 ' || model, '高色域屏幕', '高速固态')
            WHEN '外设' THEN jsonb_build_array('型号 ' || model, '低延迟连接', '兼容主流系统')
            WHEN '家电' THEN jsonb_build_array('型号 ' || model, '操作简单', '易清洁结构')
            WHEN '智能家居' THEN jsonb_build_array('型号 ' || model, 'App 联动', '状态通知')
            WHEN '办公' THEN jsonb_build_array('型号 ' || model, '商务风格', '长时间使用舒适')
            WHEN '显示器' THEN jsonb_build_array('型号 ' || model, '色彩准确', '支架调节灵活')
            WHEN '音频' THEN jsonb_build_array('型号 ' || model, '多设备兼容', '声音层次清晰')
            WHEN '摄影' THEN jsonb_build_array('型号 ' || model, '快速上手', '户外拍摄友好')
            WHEN '户外' THEN jsonb_build_array('型号 ' || model, '收纳体积友好', '适配多变天气')
            WHEN '穿戴' THEN jsonb_build_array('型号 ' || model, '佩戴舒适', '数据同步便捷')
            ELSE jsonb_build_array('型号 ' || model, '占用空间小', '细节打磨好')
        END AS spec_highlights,
        18 + ((sort_no * 9 + cat_item_no * 7 + shop_no * 5) % 80) AS stock,
        TRUE AS is_active
    FROM ranked
)
INSERT INTO products (
    shop_id,
    name,
    description,
    image_url,
    category,
    brand,
    model,
    sku_code,
    price,
    original_price,
    rating,
    review_count,
    monthly_sales,
    ship_in_hours,
    warranty_days,
    tags,
    spec_highlights,
    stock,
    is_active
)
SELECT
    shop_id,
    name,
    description,
    image_url,
    category,
    brand,
    model,
    sku_code,
    price,
    original_price,
    rating,
    review_count,
    monthly_sales,
    ship_in_hours,
    warranty_days,
    tags,
    spec_highlights,
    stock,
    is_active
FROM enriched
ORDER BY shop_id, sku_code;

INSERT INTO orders (id, user_id, shop_id, status, address, contact_email, total_amount) VALUES
(
    'ORD202603300001',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    '00000000-0000-0000-0000-000000000301',
    'pending_shipment',
    '北京市朝阳区望京 SOHO T2',
    'test1@example.com',
    (SELECT ROUND(SUM(price), 2) FROM products WHERE sku_code IN ('SG-001', 'SG-007'))
),
(
    'ORD202603300002',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    '00000000-0000-0000-0000-000000000302',
    'shipped',
    '上海市浦东新区张江高科',
    'test1@example.com',
    (SELECT ROUND(SUM(price), 2) FROM products WHERE sku_code IN ('QH-009'))
);

INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal)
SELECT 'ORD202603300001', id, name, price, 1, price FROM products WHERE sku_code = 'SG-001';

INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal)
SELECT 'ORD202603300001', id, name, price, 1, price FROM products WHERE sku_code = 'SG-007';

INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal)
SELECT 'ORD202603300002', id, name, price, 1, price FROM products WHERE sku_code = 'QH-009';

INSERT INTO logistics (
    order_id,
    shipped_from_address_id,
    tracking_no,
    status,
    current_location,
    current_lng,
    current_lat,
    estimated_delivery_at,
    route_plan,
    route_geo,
    llm_raw_text
) VALUES
(
    'ORD202603300002',
    '00000000-0000-0000-0000-000000000402',
    'SF123456789',
    'in_transit',
    '上海分拨中心',
    121.473700,
    31.230400,
    NOW() + INTERVAL '2 days',
    '["广州主仓", "杭州中转站", "上海分拨中心"]'::jsonb,
    '[{"name":"广州主仓","lng":113.264400,"lat":23.129100},{"name":"杭州中转站","lng":120.155100,"lat":30.274100},{"name":"上海分拨中心","lng":121.473700,"lat":31.230400}]'::jsonb,
    '示例物流预测文本（结构化目录种子数据）'
);

INSERT INTO after_sales (order_id, type, reason, status) VALUES
(
    'ORD202603300002',
    'return',
    '历史售后示例：门锁外包装磕碰，已完成退货处理',
    'completed'
);
