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
feature_seed AS (
    SELECT
        shop_id,
        category,
        name AS base_name,
        brand,
        model,
        shop_code || '-' || LPAD(sort_no::text, 3, '0') AS sku_code,
        shop_no,
        sort_no,
        cat_item_no,
        1 + ((cat_item_no - 1) / 2) AS cluster_no,
        1 + ((cat_item_no - 1) % 2) AS variant_no
    FROM ranked
),
featured AS (
    SELECT
        shop_id,
        category,
        base_name,
        brand,
        model,
        sku_code,
        shop_no,
        sort_no,
        cat_item_no,
        cluster_no,
        variant_no,
        CASE category
            WHEN '手机' THEN (ARRAY['曜石黑', '月岩白', '海盐蓝', '晨雾粉', '松针绿', '星砂金', '冰川银', '深空灰'])[1 + ((cluster_no - 1) % 8)]
            WHEN '电脑' THEN (ARRAY['云墨黑', '星雾银', '松烟灰', '雪山白', '深海蓝', '玄铁灰', '晨曦金', '钛空银'])[1 + ((cluster_no - 1) % 8)]
            WHEN '显示器' THEN (ARRAY['曜岩黑', '月光银', '深空灰', '雪域白', '晨曦银', '石墨黑', '星际灰', '冰川白'])[1 + ((cluster_no - 1) % 8)]
            WHEN '家电' THEN (ARRAY['珍珠白', '松雾灰', '奶油白', '曜石黑', '云杉绿', '冰川银', '雾霾蓝', '香槟金'])[1 + ((cluster_no - 1) % 8)]
            WHEN '智能家居' THEN (ARRAY['曜石黑', '月影白', '深海蓝', '钛雾灰', '暖沙金', '冰川银', '极夜黑', '雅瓷白'])[1 + ((cluster_no - 1) % 8)]
            WHEN '户外' THEN (ARRAY['橄榄绿', '岩石灰', '沙地卡其', '湖水蓝', '火山黑', '雪峰白', '松针绿', '赤陶棕'])[1 + ((cluster_no - 1) % 8)]
            WHEN '穿戴' THEN (ARRAY['曜石黑', '云雾白', '海盐蓝', '珊瑚粉', '松针绿', '钛金灰', '琥珀棕', '冰川银'])[1 + ((cluster_no - 1) % 8)]
            WHEN '外设' THEN (ARRAY['夜幕黑', '冰川白', '石墨灰', '雾海蓝', '暖砂白', '曜石黑', '银砂灰', '晨曦白'])[1 + ((cluster_no - 1) % 8)]
            WHEN '办公' THEN (ARRAY['胡桃木', '岩灰', '浅沙白', '商务黑', '钛银灰', '云母白', '深胡桃', '石英灰'])[1 + ((cluster_no - 1) % 8)]
            WHEN '音频' THEN (ARRAY['曜石黑', '月光白', '深海蓝', '酒红色', '枪灰色', '银白色', '砂岩灰', '奶油白'])[1 + ((cluster_no - 1) % 8)]
            WHEN '摄影' THEN (ARRAY['磨砂黑', '钛银色', '碳纤黑', '云雾白', '石墨灰', '香槟银', '沙岩棕', '冰川银'])[1 + ((cluster_no - 1) % 8)]
            ELSE (ARRAY['原木色', '奶油白', '岩灰色', '雾霾蓝', '暖砂色', '冰川白', '深空灰', '可可棕'])[1 + ((cluster_no - 1) % 8)]
        END AS color_label,
        CASE category
            WHEN '手机' THEN (ARRAY['6.1 英寸直屏', '6.3 英寸轻薄版', '6.67 英寸大电池', '6.78 英寸旗舰屏', '6.82 英寸影像版', '7.1 英寸折叠屏', '6.55 英寸手感版', '6.74 英寸均衡版'])[1 + ((cluster_no - 1) % 8)]
            WHEN '电脑' THEN (ARRAY['14 英寸轻薄本', '14.5 英寸高分屏', '16 英寸创作本', '16 英寸性能本', '迷你主机', '会议一体机', '塔式工作站', '14 英寸商务本'])[1 + ((cluster_no - 1) % 8)]
            WHEN '显示器' THEN (ARRAY['24 英寸', '27 英寸', '32 英寸', '34 英寸带鱼屏', '49 英寸双 QHD', '16 英寸便携屏', '27 英寸高刷', '29 英寸超宽屏'])[1 + ((cluster_no - 1) % 8)]
            WHEN '家电' THEN (ARRAY['2L 小体积', '4L 桌面款', '6L 家用版', '8L 大容量', '10L 大风量', '12 套洗涤位', '600m³/h 风量', '16L 热水量'])[1 + ((cluster_no - 1) % 8)]
            WHEN '智能家居' THEN (ARRAY['人脸+指纹', '双摄猫眼', '10.1 英寸中控', '桌面/墙装两用', '120° 人体感应', '轨道电机', '温湿双测', '四件套组合'])[1 + ((cluster_no - 1) % 8)]
            WHEN '户外' THEN (ARRAY['双人轻量版', '零下 10℃ 适用', '35L 容量', '55L 重装版', '碳纤三节', '折叠越野轮', '420cm 天幕', '1L 保温规格'])[1 + ((cluster_no - 1) % 8)]
            WHEN '穿戴' THEN (ARRAY['42mm', '46mm', 'S/M 码', 'M/L 码', 'Pro 版本', '轻量版', '45mm', '38mm'])[1 + ((cluster_no - 1) % 8)]
            WHEN '外设' THEN (ARRAY['87 键布局', '75 键静音轴', '79g 轻量', '2K 直播画质', '11 合 1 扩展', '双模连接', '旋钮快捷键', '热插拔结构'])[1 + ((cluster_no - 1) % 8)]
            WHEN '办公' THEN (ARRAY['140cm 桌板', '腰背分区支撑', 'A4 双面高速', '便携热敏打印', '12 页碎纸量', '6 麦拾音', '多档升降', '长坐舒压'])[1 + ((cluster_no - 1) % 8)]
            WHEN '音频' THEN (ARRAY['头戴旗舰', '真无线入耳', 'USB/XLR 双接口', '5 英寸单元', '5.1 声道', '桌面解码耳放', 'LDAC', '主动降噪'])[1 + ((cluster_no - 1) % 8)]
            WHEN '摄影' THEN (ARRAY['4K 60fps', '24-70mm 焦段', 'APS-C 微单', '碳纤维脚架', '直播补光', 'F2.8 恒定光圈', '五轴防抖', '便携手持'])[1 + ((cluster_no - 1) % 8)]
            ELSE (ARRAY['天然原木', '抗菌防滑', '真空保鲜', '分层收纳', '珐琅涂层', '32cm 锅体', 'UV 消毒', '模块化分格'])[1 + ((cluster_no - 1) % 8)]
        END AS primary_spec,
        CASE category
            WHEN '手机' THEN CASE
                WHEN cluster_no >= 7 THEN (ARRAY['16GB+512GB', '16GB+1TB'])[variant_no]
                ELSE (ARRAY['12GB+256GB', '12GB+512GB'])[variant_no]
            END
            WHEN '电脑' THEN CASE
                WHEN cluster_no >= 3 THEN (ARRAY['32GB+1TB', '64GB+2TB'])[variant_no]
                ELSE (ARRAY['16GB+512GB', '32GB+1TB'])[variant_no]
            END
            WHEN '显示器' THEN (ARRAY['2K 120Hz', '4K 144Hz'])[variant_no]
            WHEN '家电' THEN (ARRAY['低噪运行', '一级能效'])[variant_no]
            WHEN '智能家居' THEN (ARRAY['Wi-Fi / Matter 联动', '蓝牙 Mesh / Zigbee 联动'])[variant_no]
            WHEN '户外' THEN (ARRAY['防泼水耐候', '轻量可压缩'])[variant_no]
            WHEN '穿戴' THEN (ARRAY['7 天续航', '14 天续航'])[variant_no]
            WHEN '外设' THEN (ARRAY['蓝牙 + 2.4G 双模', '多设备切换'])[variant_no]
            WHEN '办公' THEN (ARRAY['企业会议场景', '长时间久坐友好'])[variant_no]
            WHEN '音频' THEN (ARRAY['蓝牙 5.4', '低延迟模式'])[variant_no]
            WHEN '摄影' THEN (ARRAY['创作套装友好', '旅行便携'])[variant_no]
            ELSE (ARRAY['耐磨耐用', '易清洁收纳'])[variant_no]
        END AS secondary_spec,
        CASE category
            WHEN '手机' THEN (ARRAY['通勤影像', '长续航出差', '手游旗舰', '轻薄自拍', '夜景人像', '大屏阅读', '折叠商务', '耐摔备用'])[1 + ((cluster_no - 1) % 8)]
            WHEN '电脑' THEN (ARRAY['日常办公', '视频会议', '内容创作', '高性能剪辑', '桌面扩展', '会议室协作', '静音渲染', '移动差旅'])[1 + ((cluster_no - 1) % 8)]
            WHEN '显示器' THEN (ARRAY['办公护眼', '电竞高刷', '内容创作', '多窗口协作', '沉浸式游戏', '移动副屏', '图像调色', '直播监看'])[1 + ((cluster_no - 1) % 8)]
            WHEN '家电' THEN (ARRAY['卧室静音', '母婴房净化', '厨房高频', '租房小户型', '全家共享', '重油污清洁', '夏季循环送风', '冬季取暖'])[1 + ((cluster_no - 1) % 8)]
            WHEN '智能家居' THEN (ARRAY['入户安防', '玄关联动', '客厅中控', '夜间照明', '人体感应', '窗帘自动化', '环境监测', '老人看护'])[1 + ((cluster_no - 1) % 8)]
            WHEN '户外' THEN (ARRAY['周末露营', '高海拔徒步', '长线穿越', '自驾营地', '越野跑步', '重装运输', '亲子露营', '全天保温'])[1 + ((cluster_no - 1) % 8)]
            WHEN '穿戴' THEN (ARRAY['睡眠监测', '运动记录', '长辈看护', '血氧提醒', '心率追踪', '居家康复', '久坐办公', '减压放松'])[1 + ((cluster_no - 1) % 8)]
            WHEN '外设' THEN (ARRAY['桌面升级', '宿舍游戏', '远程会议', '直播开会', '多屏办公', '移动办公', '效率键位', '热插拔折腾'])[1 + ((cluster_no - 1) % 8)]
            WHEN '办公' THEN (ARRAY['久坐办公', '居家书房', '企业会议', '移动差旅', '纸质归档', '开放办公区', '会议拾音', '桌面整理'])[1 + ((cluster_no - 1) % 8)]
            WHEN '音频' THEN (ARRAY['通勤听歌', '桌面监听', '直播录音', '家庭影院', '宿舍追剧', '游戏语音', '播客录制', '夜间沉浸'])[1 + ((cluster_no - 1) % 8)]
            WHEN '摄影' THEN (ARRAY['Vlog 创作', '直播补光', '旅行拍摄', '人像拍摄', '桌面开箱', '运动记录', '轻量外拍', '内容工作室'])[1 + ((cluster_no - 1) % 8)]
            ELSE (ARRAY['厨房整理', '高频烹饪', '餐具收纳', '备菜分区', '家庭聚餐', '橱柜扩容', '保鲜备餐', '台面整洁'])[1 + ((cluster_no - 1) % 8)]
        END AS scenario_label,
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
        ROUND((
            CASE category
                WHEN '手机' THEN 2299 + cluster_no * 420 + variant_no * 180
                WHEN '电脑' THEN 4599 + cluster_no * 900 + variant_no * 450
                WHEN '外设' THEN 159 + cluster_no * 120 + variant_no * 55
                WHEN '家电' THEN 299 + cluster_no * 240 + variant_no * 120
                WHEN '智能家居' THEN 199 + cluster_no * 220 + variant_no * 95
                WHEN '办公' THEN 259 + cluster_no * 180 + variant_no * 80
                WHEN '显示器' THEN 1199 + cluster_no * 650 + variant_no * 260
                WHEN '音频' THEN 299 + cluster_no * 170 + variant_no * 90
                WHEN '摄影' THEN 799 + cluster_no * 550 + variant_no * 230
                WHEN '户外' THEN 189 + cluster_no * 160 + variant_no * 75
                WHEN '穿戴' THEN 269 + cluster_no * 190 + variant_no * 85
                ELSE 129 + cluster_no * 85 + variant_no * 35
            END
            + CASE
                WHEN base_name LIKE '%Ultra%' THEN 680
                WHEN base_name LIKE '%Fold%' THEN 1480
                WHEN base_name LIKE '%工作站%' THEN 1650
                WHEN base_name LIKE '%MiniLED%' THEN 720
                WHEN base_name LIKE '%带鱼屏%' THEN 540
                WHEN base_name LIKE '%相机%' THEN 620
                WHEN base_name LIKE '%镜头%' THEN 980
                WHEN base_name LIKE '%门锁%' THEN 660
                WHEN base_name LIKE '%洗碗机%' THEN 880
                WHEN base_name LIKE '%帐篷%' THEN 420
                WHEN base_name LIKE '%睡袋%' THEN 280
                WHEN base_name LIKE '%手表%' THEN 260
                WHEN base_name LIKE '%套装%' THEN 340
                ELSE 0
            END
            + shop_no * 21
        )::numeric, 2) AS price,
        ROUND((
            CASE category
                WHEN '手机' THEN 420 + cluster_no * 40 + variant_no * 50
                WHEN '电脑' THEN 680 + cluster_no * 90 + variant_no * 70
                WHEN '显示器' THEN 360 + cluster_no * 60 + variant_no * 45
                WHEN '家电' THEN 260 + cluster_no * 35 + variant_no * 25
                WHEN '智能家居' THEN 220 + cluster_no * 30 + variant_no * 20
                WHEN '摄影' THEN 480 + cluster_no * 80 + variant_no * 55
                WHEN '户外' THEN 180 + cluster_no * 22 + variant_no * 18
                WHEN '穿戴' THEN 210 + cluster_no * 25 + variant_no * 18
                ELSE 140 + cluster_no * 18 + variant_no * 12
            END
        )::numeric, 2) AS price_gap,
        ROUND(LEAST(4.9::numeric, 4.2::numeric + (((cluster_no + variant_no + shop_no) % 6) * 0.1)::numeric), 1) AS rating,
        180 + cluster_no * 59 + variant_no * 41 + shop_no * 19 + sort_no * 7 AS review_count,
        120 + cluster_no * 88 + variant_no * 46 + shop_no * 21 + cat_item_no * 15 AS monthly_sales,
        (ARRAY[6, 12, 24, 36, 48])[1 + ((cluster_no + shop_no + variant_no) % 5)] AS ship_in_hours,
        CASE
            WHEN category IN ('手机', '电脑', '显示器', '家电', '智能家居', '摄影') THEN 365
            WHEN category IN ('穿戴', '户外') THEN 240
            ELSE 180
        END AS warranty_days
    FROM feature_seed
),
named AS (
    SELECT
        shop_id,
        category,
        base_name,
        brand,
        model,
        sku_code,
        color_label,
        primary_spec,
        secondary_spec,
        scenario_label,
        image_url,
        price,
        price_gap,
        rating,
        review_count,
        monthly_sales,
        ship_in_hours,
        warranty_days,
        shop_no,
        cluster_no,
        variant_no,
        sort_no,
        CASE
            WHEN category = '手机' THEN base_name || ' ' || color_label || ' ' || primary_spec
            WHEN category = '电脑' THEN base_name || ' ' || color_label || ' ' || secondary_spec
            WHEN category = '显示器' THEN base_name || ' ' || color_label || ' ' || primary_spec
            WHEN category IN ('家电', '智能家居', '穿戴', '摄影') THEN base_name || ' ' || color_label || ' ' || secondary_spec
            ELSE base_name || ' ' || color_label
        END AS display_name
    FROM featured
),
enriched AS (
    SELECT
        shop_id,
        display_name AS name,
        CASE category
            WHEN '手机' THEN display_name || ' 提供 ' || color_label || ' 配色，规格为 ' || primary_spec || '，搭配 ' || secondary_spec || '，主打 ' || scenario_label || '。'
            WHEN '电脑' THEN display_name || ' 采用 ' || color_label || ' 机身，提供 ' || primary_spec || ' 与 ' || secondary_spec || '，定位 ' || scenario_label || '。'
            WHEN '显示器' THEN display_name || ' 提供 ' || color_label || ' 外观与 ' || primary_spec || '，配合 ' || secondary_spec || '，适合 ' || scenario_label || '。'
            WHEN '家电' THEN display_name || ' 采用 ' || color_label || ' 配色，核心规格为 ' || primary_spec || '，支持 ' || secondary_spec || '，适合 ' || scenario_label || '。'
            WHEN '智能家居' THEN display_name || ' 提供 ' || color_label || ' 版本，支持 ' || primary_spec || ' 与 ' || secondary_spec || '，适合 ' || scenario_label || '。'
            WHEN '户外' THEN display_name || ' 采用 ' || color_label || ' 面料，规格为 ' || primary_spec || '，强调 ' || secondary_spec || '，适合 ' || scenario_label || '。'
            WHEN '穿戴' THEN display_name || ' 提供 ' || color_label || ' 版本，规格为 ' || primary_spec || '，支持 ' || secondary_spec || '，适合 ' || scenario_label || '。'
            ELSE display_name || ' 提供 ' || color_label || ' 配色，规格为 ' || primary_spec || '，支持 ' || secondary_spec || '，适合 ' || scenario_label || '。'
        END AS description,
        image_url,
        category,
        brand,
        model,
        sku_code,
        price,
        ROUND((price + price_gap)::numeric, 2) AS original_price,
        rating,
        review_count,
        monthly_sales,
        ship_in_hours,
        warranty_days,
        CASE category
            WHEN '手机' THEN jsonb_build_array(brand, color_label, primary_spec, secondary_spec, scenario_label, '快充', '近似价位机型')
            WHEN '电脑' THEN jsonb_build_array(brand, color_label, primary_spec, secondary_spec, scenario_label, '高性能', '近似价位机型')
            WHEN '显示器' THEN jsonb_build_array(brand, color_label, primary_spec, secondary_spec, scenario_label, '多接口', '近似价位机型')
            WHEN '家电' THEN jsonb_build_array(brand, color_label, primary_spec, secondary_spec, scenario_label, '低噪使用', '近似价位机型')
            WHEN '智能家居' THEN jsonb_build_array(brand, color_label, primary_spec, secondary_spec, scenario_label, '场景联动', '近似价位机型')
            WHEN '户外' THEN jsonb_build_array(brand, color_label, primary_spec, secondary_spec, scenario_label, '耐候材质', '近似价位机型')
            WHEN '穿戴' THEN jsonb_build_array(brand, color_label, primary_spec, secondary_spec, scenario_label, '健康监测', '近似价位机型')
            ELSE jsonb_build_array(brand, color_label, primary_spec, secondary_spec, scenario_label, '近似价位机型')
        END AS tags,
        CASE category
            WHEN '手机' THEN jsonb_build_array('型号 ' || model, color_label, primary_spec, secondary_spec, scenario_label)
            WHEN '电脑' THEN jsonb_build_array('型号 ' || model, color_label, primary_spec, secondary_spec, scenario_label)
            WHEN '显示器' THEN jsonb_build_array('型号 ' || model, color_label, primary_spec, secondary_spec, scenario_label)
            WHEN '家电' THEN jsonb_build_array('型号 ' || model, color_label, primary_spec, secondary_spec, scenario_label)
            WHEN '智能家居' THEN jsonb_build_array('型号 ' || model, color_label, primary_spec, secondary_spec, scenario_label)
            WHEN '户外' THEN jsonb_build_array('型号 ' || model, color_label, primary_spec, secondary_spec, scenario_label)
            WHEN '穿戴' THEN jsonb_build_array('型号 ' || model, color_label, primary_spec, secondary_spec, scenario_label)
            ELSE jsonb_build_array('型号 ' || model, color_label, primary_spec, secondary_spec, scenario_label)
        END AS spec_highlights,
        12 + ((cluster_no * 11 + variant_no * 9 + shop_no * 7 + sort_no) % 68) AS stock,
        TRUE AS is_active
    FROM named
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
