SET client_encoding = 'UTF8';

-- Demo accounts. All passwords are password123.
INSERT INTO users (id, username, email, hashed_password, role) VALUES
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '演示客户一', 'test1@example.com', crypt('password123', gen_salt('bf', 12)), 'customer'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', '演示客户二', 'test2@example.com', crypt('password123', gen_salt('bf', 12)), 'customer'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a21', '数码星河店长', 'merchant1@example.com', crypt('password123', gen_salt('bf', 12)), 'merchant'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', '智能家居店长', 'merchant2@example.com', crypt('password123', gen_salt('bf', 12)), 'merchant'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a23', '办公效率店长', 'merchant3@example.com', crypt('password123', gen_salt('bf', 12)), 'merchant'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a24', '山野生活店长', 'merchant4@example.com', crypt('password123', gen_salt('bf', 12)), 'merchant'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a25', '备用商家一', 'merchant5@example.com', crypt('password123', gen_salt('bf', 12)), 'merchant'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a26', '备用商家二', 'merchant6@example.com', crypt('password123', gen_salt('bf', 12)), 'merchant'),
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a27', '备用商家三', 'merchant7@example.com', crypt('password123', gen_salt('bf', 12)), 'merchant');

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
    '数码星河旗舰店',
    '主营手机、笔记本、显示器和影音配件，适合演示客服根据预算、颜色、用途进行推荐。',
    'merchant1@example.com',
    '13800000001',
    '/demo-assets/logos/digital.svg',
    4.8,
    4.9,
    4.7,
    4.8,
    '深圳',
    '["手机数码", "电脑办公", "影音配件"]'::jsonb,
    '["24小时内发货", "7天无理由", "一年质保"]'::jsonb,
    TRUE
),
(
    '00000000-0000-0000-0000-000000000302',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
    '青禾智能家居',
    '主营智能门锁、扫地机器人、空气净化器和家庭安防设备，适合演示售前咨询和售后政策。',
    'merchant2@example.com',
    '13800000002',
    '/demo-assets/logos/home.svg',
    4.7,
    4.8,
    4.6,
    4.7,
    '广州',
    '["智能家居", "清洁电器", "家庭安防"]'::jsonb,
    '["上门安装", "快速换新", "远程指导"]'::jsonb,
    TRUE
),
(
    '00000000-0000-0000-0000-000000000303',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a23',
    '办公效率工坊',
    '主营人体工学椅、升降桌、打印设备和会议套装，适合演示办公场景推荐。',
    'merchant3@example.com',
    '13800000003',
    '/demo-assets/logos/office.svg',
    4.6,
    4.7,
    4.7,
    4.6,
    '上海',
    '["办公家具", "办公设备", "会议设备"]'::jsonb,
    '["企业采购", "专票支持", "安装服务"]'::jsonb,
    TRUE
),
(
    '00000000-0000-0000-0000-000000000304',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a24',
    '山野生活馆',
    '主营户外服饰、背包、露营灯和保温杯，适合演示跨类目推荐和售后进度查询。',
    'merchant4@example.com',
    '13800000004',
    '/demo-assets/logos/outdoor.svg',
    4.8,
    4.8,
    4.7,
    4.8,
    '杭州',
    '["户外装备", "露营用品", "旅行配件"]'::jsonb,
    '["48小时内发货", "破损包赔", "换货无忧"]'::jsonb,
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
('00000000-0000-0000-0000-000000000401', '00000000-0000-0000-0000-000000000301', '深圳默认仓', '陈星', '13800000001', '广东省', '深圳市', '南山区', '科技园科苑路 18 号 A 座', '518057', TRUE),
('00000000-0000-0000-0000-000000000402', '00000000-0000-0000-0000-000000000302', '广州默认仓', '林青', '13800000002', '广东省', '广州市', '天河区', '智慧城云溪路 66 号', '510630', TRUE),
('00000000-0000-0000-0000-000000000403', '00000000-0000-0000-0000-000000000303', '上海默认仓', '周明', '13800000003', '上海市', '上海市', '浦东新区', '张江高科路 288 号', '200120', TRUE),
('00000000-0000-0000-0000-000000000404', '00000000-0000-0000-0000-000000000304', '杭州默认仓', '何川', '13800000004', '浙江省', '杭州市', '余杭区', '未来科技城仓储中心 9 号', '310030', TRUE);

INSERT INTO products (
    id,
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
) VALUES
('00000000-0000-0000-0000-000000000501', '00000000-0000-0000-0000-000000000301', '星河 X1 轻旗舰手机 冰川银 12GB+256GB', '高刷 OLED 屏、轻薄机身和全天候续航，适合预算四千以内、偏好银色手机的用户。', '/demo-assets/products/phone.svg', '手机数码', '星河', 'X1', 'SG-PHONE-X1', 3999.00, 4499.00, 4.8, 1180, 620, 12, 365, '["银色", "高刷屏", "长续航", "轻薄"]'::jsonb, '["6.7英寸 OLED", "12GB+256GB", "5000mAh 电池", "一年质保"]'::jsonb, 46, TRUE),
('00000000-0000-0000-0000-000000000502', '00000000-0000-0000-0000-000000000301', '星河 X1 Pro 影像手机 深空黑 16GB+512GB', '主打夜景拍摄和大存储，适合摄影、短视频和高性能需求。', '/demo-assets/products/phone.svg', '手机数码', '星河', 'X1 Pro', 'SG-PHONE-PRO', 5299.00, 5999.00, 4.9, 860, 390, 12, 365, '["黑色", "影像旗舰", "大存储", "快充"]'::jsonb, '["16GB+512GB", "潜望长焦", "120W 快充", "IP68 防尘防水"]'::jsonb, 32, TRUE),
('00000000-0000-0000-0000-000000000503', '00000000-0000-0000-0000-000000000301', '凌云 Air 14 轻薄本 银色 i5 16GB 1TB', '适合毕业设计、论文写作、轻量开发和通勤携带。', '/demo-assets/products/laptop.svg', '电脑办公', '凌云', 'Air 14', 'SG-LAPTOP-14', 5499.00, 6199.00, 4.8, 734, 280, 24, 365, '["银色", "轻薄本", "学生推荐", "办公"]'::jsonb, '["14英寸 2.8K 屏", "16GB 内存", "1TB SSD", "1.25kg 机身"]'::jsonb, 24, TRUE),
('00000000-0000-0000-0000-000000000504', '00000000-0000-0000-0000-000000000301', '凌云 Pro 16 创作本 灰色 i7 32GB 1TB', '适合剪辑、建模、开发和多任务办公，性能释放稳定。', '/demo-assets/products/laptop.svg', '电脑办公', '凌云', 'Pro 16', 'SG-LAPTOP-16', 8299.00, 8999.00, 4.7, 512, 180, 24, 365, '["灰色", "创作本", "高性能", "大屏"]'::jsonb, '["16英寸 3.2K 屏", "32GB 内存", "1TB SSD", "独立显卡"]'::jsonb, 18, TRUE),
('00000000-0000-0000-0000-000000000505', '00000000-0000-0000-0000-000000000301', '星河 27 英寸 4K Type-C 显示器', 'Type-C 一线连接，适合论文排版、代码开发和双屏办公。', '/demo-assets/products/monitor.svg', '电脑办公', '星河', 'View 27 4K', 'SG-MONITOR-27', 1899.00, 2299.00, 4.7, 603, 240, 24, 365, '["27英寸", "4K", "Type-C", "护眼"]'::jsonb, '["3840x2160 分辨率", "90W Type-C 供电", "低蓝光", "升降支架"]'::jsonb, 40, TRUE),
('00000000-0000-0000-0000-000000000506', '00000000-0000-0000-0000-000000000301', '声阔 Lite 降噪耳机 米白色', '通勤、会议和自习场景都适合，支持主动降噪和多设备切换。', '/demo-assets/products/headphones.svg', '影音配件', '声阔', 'Lite ANC', 'SG-EARBUDS', 499.00, 699.00, 4.6, 924, 510, 12, 180, '["米白色", "主动降噪", "通勤", "会议"]'::jsonb, '["40dB 降噪", "36小时续航", "双设备连接", "低延迟模式"]'::jsonb, 80, TRUE),
('00000000-0000-0000-0000-000000000507', '00000000-0000-0000-0000-000000000302', '青禾 S3 指静脉智能门锁', '支持指静脉、密码、NFC 和临时密码，适合家庭安防咨询演示。', '/demo-assets/products/lock.svg', '智能家居', '青禾', 'S3', 'QH-LOCK-PRO', 1299.00, 1699.00, 4.8, 678, 320, 24, 365, '["指静脉", "上门安装", "家庭安防", "黑色"]'::jsonb, '["C级锁芯", "7种开锁方式", "异常告警", "免费安装"]'::jsonb, 36, TRUE),
('00000000-0000-0000-0000-000000000508', '00000000-0000-0000-0000-000000000302', '青禾 Sweep S1 扫拖机器人', '自动集尘、拖布热风烘干，适合养宠家庭和大户型。', '/demo-assets/products/robot-vacuum.svg', '清洁电器', '青禾', 'Sweep S1', 'QH-ROBOT-S1', 2599.00, 3199.00, 4.7, 542, 260, 24, 365, '["扫拖一体", "自动集尘", "宠物家庭", "大户型"]'::jsonb, '["6000Pa 吸力", "自动回洗拖布", "热风烘干", "激光导航"]'::jsonb, 28, TRUE),
('00000000-0000-0000-0000-000000000509', '00000000-0000-0000-0000-000000000302', '青禾 Air Pure 空气净化器', '适合卧室和客厅，支持甲醛数显和静音睡眠模式。', '/demo-assets/products/home-appliance.svg', '清洁电器', '青禾', 'Air Pure', 'QH-AIR-PURE', 999.00, 1299.00, 4.6, 436, 190, 24, 365, '["除甲醛", "静音", "卧室", "空气净化"]'::jsonb, '["CADR 500m3/h", "甲醛数显", "睡眠模式", "滤芯提醒"]'::jsonb, 42, TRUE),
('00000000-0000-0000-0000-000000000510', '00000000-0000-0000-0000-000000000302', '青禾 Cam 2K 智能摄像头', '2K 清晰画质和人形检测，适合看家、看宠和门店监控。', '/demo-assets/products/home-appliance.svg', '家庭安防', '青禾', 'Cam 2K', 'QH-CAMERA-2K', 299.00, 399.00, 4.5, 390, 330, 12, 180, '["2K", "看家", "人形检测", "夜视"]'::jsonb, '["2K 分辨率", "双向语音", "红外夜视", "异常推送"]'::jsonb, 90, TRUE),
('00000000-0000-0000-0000-000000000511', '00000000-0000-0000-0000-000000000302', '青禾 Hub Mini 智能中枢屏', '联动门锁、摄像头和传感器，适合全屋智能入门。', '/demo-assets/products/home-appliance.svg', '智能家居', '青禾', 'Hub Mini', 'QH-HUB-MINI', 599.00, 799.00, 4.6, 288, 150, 24, 365, '["全屋智能", "中枢屏", "联动", "语音控制"]'::jsonb, '["4英寸触控屏", "蓝牙网关", "Matter 兼容", "场景自动化"]'::jsonb, 55, TRUE),
('00000000-0000-0000-0000-000000000512', '00000000-0000-0000-0000-000000000302', '青禾 Sensor 安防传感器套装', '门窗、水浸、人体传感器组合，适合租房和家庭安全提醒。', '/demo-assets/products/home-appliance.svg', '家庭安防', '青禾', 'Sensor Kit', 'QH-SENSOR-KIT', 399.00, 499.00, 4.5, 260, 210, 12, 180, '["门窗传感器", "水浸报警", "租房", "安防套装"]'::jsonb, '["门窗传感器 x2", "水浸传感器 x1", "人体传感器 x1", "App 推送"]'::jsonb, 70, TRUE),
('00000000-0000-0000-0000-000000000513', '00000000-0000-0000-0000-000000000303', '坐享 Pro 人体工学椅 黑色', '腰托、头枕和扶手多向调节，适合长时间写论文和办公。', '/demo-assets/products/chair.svg', '办公家具', '坐享', 'Pro', 'BG-CHAIR-PRO', 1299.00, 1599.00, 4.7, 590, 230, 36, 365, '["人体工学", "黑色", "久坐", "办公"]'::jsonb, '["自适应腰托", "4D 扶手", "可调头枕", "三年质保"]'::jsonb, 34, TRUE),
('00000000-0000-0000-0000-000000000514', '00000000-0000-0000-0000-000000000303', '升维 E2 电动升降桌 白色 1.4米', '坐站交替办公，适合宿舍、书房和小型工作室。', '/demo-assets/products/chair.svg', '办公家具', '升维', 'E2', 'BG-DESK-LIFT', 1699.00, 1999.00, 4.6, 420, 160, 48, 365, '["电动升降", "白色", "书房", "坐站交替"]'::jsonb, '["1.4米桌面", "双电机", "四档记忆", "承重 100kg"]'::jsonb, 20, TRUE),
('00000000-0000-0000-0000-000000000515', '00000000-0000-0000-0000-000000000303', '印客 P8 无线彩色打印机', '支持手机直连和自动双面打印，适合作业、合同和照片输出。', '/demo-assets/products/home-appliance.svg', '办公设备', '印客', 'P8', 'BG-PRINTER-P8', 899.00, 1099.00, 4.5, 318, 120, 36, 365, '["无线打印", "自动双面", "学生", "彩色"]'::jsonb, '["Wi-Fi 直连", "自动双面", "微信小程序打印", "低成本墨仓"]'::jsonb, 26, TRUE),
('00000000-0000-0000-0000-000000000516', '00000000-0000-0000-0000-000000000303', '会畅 M4 会议摄像头套装', '摄像头、麦克风和补光灯组合，适合远程答辩和线上会议。', '/demo-assets/products/monitor.svg', '会议设备', '会畅', 'M4', 'BG-MEETING-M4', 699.00, 899.00, 4.5, 276, 140, 24, 180, '["远程会议", "答辩", "麦克风", "补光"]'::jsonb, '["1080P 摄像头", "双麦降噪", "三档补光", "免驱连接"]'::jsonb, 38, TRUE),
('00000000-0000-0000-0000-000000000517', '00000000-0000-0000-0000-000000000304', '山野 Storm 三合一冲锋衣 藏青色', '防风、防水、可拆卸内胆，适合旅行、徒步和通勤。', '/demo-assets/products/outdoor.svg', '户外装备', '山野', 'Storm', 'OUT-JACKET-STORM', 799.00, 999.00, 4.8, 642, 300, 48, 240, '["冲锋衣", "藏青色", "防水", "徒步"]'::jsonb, '["10000mm 防水", "可拆卸内胆", "防风帽", "男女同款"]'::jsonb, 44, TRUE),
('00000000-0000-0000-0000-000000000518', '00000000-0000-0000-0000-000000000304', '山野 Trek 32L 旅行背包 黑色', '多仓位收纳和背负系统，适合短途旅行与城市通勤。', '/demo-assets/products/outdoor.svg', '旅行配件', '山野', 'Trek 32L', 'OUT-BACKPACK-32', 399.00, 529.00, 4.7, 528, 260, 48, 180, '["32L", "黑色", "旅行", "通勤"]'::jsonb, '["独立电脑仓", "干湿分离", "防泼水", "减负背负"]'::jsonb, 58, TRUE),
('00000000-0000-0000-0000-000000000519', '00000000-0000-0000-0000-000000000304', '山野 Camp 露营灯 暖白光', '支持移动电源反向充电，适合露营、夜钓和应急照明。', '/demo-assets/products/outdoor.svg', '露营用品', '山野', 'Camp Light', 'OUT-CAMP-LAMP', 199.00, 269.00, 4.6, 486, 340, 24, 180, '["露营灯", "暖白光", "应急", "长续航"]'::jsonb, '["三档亮度", "最长 60 小时", "IPX4 防水", "Type-C 充电"]'::jsonb, 96, TRUE),
('00000000-0000-0000-0000-000000000520', '00000000-0000-0000-0000-000000000304', '山野 Keep 800ml 保温杯 沙色', '大容量、轻量化，适合通勤、旅行和户外补水。', '/demo-assets/products/outdoor.svg', '旅行配件', '山野', 'Keep 800', 'OUT-THERMOS-800', 159.00, 199.00, 4.6, 390, 280, 24, 180, '["保温杯", "沙色", "800ml", "旅行"]'::jsonb, '["316 不锈钢", "24小时保温", "一键开合", "杯盖防漏"]'::jsonb, 110, TRUE),
('00000000-0000-0000-0000-000000000521', '00000000-0000-0000-0000-000000000301', '星河 Pad 11 学习平板 银色 8GB+256GB', '轻薄平板适合网课、论文阅读和移动办公，可与键盘套搭配使用。', '/demo-assets/products/default.svg', '手机数码', '星河', 'Pad 11', 'SG-TABLET-11', 2499.00, 2899.00, 4.7, 520, 260, 12, 365, '["平板", "银色", "学习", "移动办公"]'::jsonb, '["11英寸 2.5K 屏", "8GB+256GB", "手写笔支持", "轻薄机身"]'::jsonb, 50, TRUE),
('00000000-0000-0000-0000-000000000522', '00000000-0000-0000-0000-000000000301', '星河 Watch Fit 智能手表 曜石黑', '支持运动记录、消息提醒和长续航，适合通勤和健康管理。', '/demo-assets/products/default.svg', '手机数码', '星河', 'Watch Fit', 'SG-WATCH-FIT', 699.00, 899.00, 4.6, 430, 310, 12, 180, '["智能手表", "运动", "长续航", "黑色"]'::jsonb, '["14天续航", "100种运动模式", "心率监测", "消息提醒"]'::jsonb, 72, TRUE),
('00000000-0000-0000-0000-000000000523', '00000000-0000-0000-0000-000000000301', '凌云 Mini Pro 迷你主机 i5 16GB 512GB', '小体积办公主机，适合宿舍、前台和轻量开发环境。', '/demo-assets/products/monitor.svg', '电脑办公', '凌云', 'Mini Pro', 'SG-MINI-PC', 2999.00, 3499.00, 4.7, 310, 130, 24, 365, '["迷你主机", "办公", "轻量开发", "小体积"]'::jsonb, '["i5 处理器", "16GB 内存", "512GB SSD", "双屏输出"]'::jsonb, 26, TRUE),
('00000000-0000-0000-0000-000000000524', '00000000-0000-0000-0000-000000000301', '星河 34 英寸 WQHD 曲面显示器', '带鱼屏适合代码、剪辑和多窗口办公，提升横向工作区。', '/demo-assets/products/monitor.svg', '电脑办公', '星河', 'View 34 Curve', 'SG-MONITOR-34', 2499.00, 2999.00, 4.8, 410, 170, 24, 365, '["34英寸", "曲面屏", "带鱼屏", "多任务"]'::jsonb, '["3440x1440 分辨率", "100Hz 刷新率", "升降支架", "低蓝光"]'::jsonb, 22, TRUE),
('00000000-0000-0000-0000-000000000525', '00000000-0000-0000-0000-000000000301', '声阔 Studio 头戴式降噪耳机 黑金色', '适合宿舍自习、远程会议和长时间音乐聆听。', '/demo-assets/products/headphones.svg', '影音配件', '声阔', 'Studio ANC', 'SG-HEADSET-STUDIO', 899.00, 1199.00, 4.7, 680, 280, 12, 180, '["头戴式", "主动降噪", "会议", "长续航"]'::jsonb, '["自适应降噪", "50小时续航", "空间音效", "双麦通话"]'::jsonb, 64, TRUE),
('00000000-0000-0000-0000-000000000526', '00000000-0000-0000-0000-000000000301', '星河 Dock Pro Type-C 扩展坞', '适合笔记本外接显示器、网线、键鼠和 U 盘的桌面扩展。', '/demo-assets/products/default.svg', '电脑办公', '星河', 'Dock Pro', 'SG-DOCK-PRO', 399.00, 499.00, 4.6, 360, 260, 12, 180, '["Type-C", "扩展坞", "外接显示器", "桌面办公"]'::jsonb, '["HDMI 4K", "千兆网口", "PD 100W", "8合1 接口"]'::jsonb, 100, TRUE),
('00000000-0000-0000-0000-000000000527', '00000000-0000-0000-0000-000000000302', '青禾 Curtain M1 智能窗帘电机', '支持定时开合、语音控制和日出日落自动化。', '/demo-assets/products/home-appliance.svg', '智能家居', '青禾', 'Curtain M1', 'QH-CURTAIN-M1', 799.00, 999.00, 4.6, 260, 120, 24, 365, '["智能窗帘", "语音控制", "定时", "全屋智能"]'::jsonb, '["静音电机", "断电手拉", "App 控制", "轨道兼容"]'::jsonb, 40, TRUE),
('00000000-0000-0000-0000-000000000528', '00000000-0000-0000-0000-000000000302', '青禾 Thermo T1 温湿度传感器', '监测室内温湿度，可联动空调、加湿器和新风设备。', '/demo-assets/products/home-appliance.svg', '智能家居', '青禾', 'Thermo T1', 'QH-THERMO-T1', 129.00, 169.00, 4.5, 520, 420, 12, 180, '["温湿度", "传感器", "联动", "小户型"]'::jsonb, '["电子墨水屏", "蓝牙网关联动", "低电量提醒", "一年续航"]'::jsonb, 150, TRUE),
('00000000-0000-0000-0000-000000000529', '00000000-0000-0000-0000-000000000302', '青禾 Light Strip 智能氛围灯带 5米', '适合客厅、卧室和桌面氛围布置，可按场景自动切换。', '/demo-assets/products/home-appliance.svg', '智能家居', '青禾', 'Light Strip', 'QH-LIGHT-STRIP', 199.00, 269.00, 4.5, 460, 360, 12, 180, '["灯带", "氛围灯", "场景联动", "卧室"]'::jsonb, '["1600万色", "音乐律动", "App 控制", "5米套装"]'::jsonb, 120, TRUE),
('00000000-0000-0000-0000-000000000530', '00000000-0000-0000-0000-000000000302', '青禾 Pet Feeder 智能宠物喂食器', '支持远程投喂和余粮提醒，适合上班族养宠家庭。', '/demo-assets/products/home-appliance.svg', '智能家居', '青禾', 'Pet Feeder', 'QH-PET-FEEDER', 499.00, 699.00, 4.6, 300, 180, 24, 365, '["宠物", "远程投喂", "余粮提醒", "定时"]'::jsonb, '["4L 粮桶", "定时投喂", "双电源", "防卡粮结构"]'::jsonb, 46, TRUE),
('00000000-0000-0000-0000-000000000531', '00000000-0000-0000-0000-000000000303', '阅享 A4 高速扫描仪', '适合合同、发票和论文资料数字化归档。', '/demo-assets/products/home-appliance.svg', '办公设备', '阅享', 'Scan A4', 'BG-SCANNER-A4', 1099.00, 1399.00, 4.6, 230, 90, 24, 365, '["扫描仪", "合同归档", "双面扫描", "办公"]'::jsonb, '["40页自动进纸", "双面扫描", "OCR 识别", "PDF 合并"]'::jsonb, 24, TRUE),
('00000000-0000-0000-0000-000000000532', '00000000-0000-0000-0000-000000000303', '会畅 Speak 全向会议麦克风', '适合小会议室、线上答辩和多人远程协作。', '/demo-assets/products/headphones.svg', '会议设备', '会畅', 'Speak', 'BG-MIC-SPEAK', 499.00, 699.00, 4.5, 280, 150, 24, 180, '["会议麦克风", "远程协作", "降噪", "免驱"]'::jsonb, '["360度拾音", "AI 降噪", "USB/蓝牙连接", "8小时续航"]'::jsonb, 50, TRUE),
('00000000-0000-0000-0000-000000000533', '00000000-0000-0000-0000-000000000303', '协作 Pro 移动白板 90x120cm', '适合团队讨论、毕业设计流程梳理和商家运营看板。', '/demo-assets/products/default.svg', '办公家具', '协作', 'Board Pro', 'BG-WHITEBOARD-PRO', 599.00, 799.00, 4.5, 190, 80, 48, 365, '["白板", "移动支架", "团队讨论", "流程梳理"]'::jsonb, '["双面书写", "磁吸表面", "可锁脚轮", "附赠配件"]'::jsonb, 18, TRUE),
('00000000-0000-0000-0000-000000000534', '00000000-0000-0000-0000-000000000304', '山野 Dome 2 双人速开帐篷', '适合周末露营和轻量徒步，快速搭建、防雨通风。', '/demo-assets/products/outdoor.svg', '露营用品', '山野', 'Dome 2', 'OUT-TENT-DOME2', 699.00, 899.00, 4.7, 360, 170, 48, 240, '["帐篷", "双人", "速开", "防雨"]'::jsonb, '["双层结构", "5分钟搭建", "防雨指数 3000mm", "收纳包"]'::jsonb, 36, TRUE),
('00000000-0000-0000-0000-000000000535', '00000000-0000-0000-0000-000000000304', '山野 Warm 700 羽绒睡袋', '适合春秋露营和长途旅行，兼顾保暖和压缩体积。', '/demo-assets/products/outdoor.svg', '露营用品', '山野', 'Warm 700', 'OUT-SLEEPBAG-700', 499.00, 659.00, 4.6, 310, 140, 48, 180, '["睡袋", "羽绒", "春秋", "轻量"]'::jsonb, '["700蓬羽绒", "舒适温标 5℃", "压缩收纳", "防泼水面料"]'::jsonb, 42, TRUE),
('00000000-0000-0000-0000-000000000536', '00000000-0000-0000-0000-000000000304', '山野 Trail 碳素登山杖 一对', '轻量碳素材质，适合徒步、爬山和长距离旅行减负。', '/demo-assets/products/outdoor.svg', '户外装备', '山野', 'Trail Carbon', 'OUT-TREK-POLES', 299.00, 399.00, 4.6, 420, 230, 24, 180, '["登山杖", "碳素", "徒步", "减负"]'::jsonb, '["三节伸缩", "碳素杆身", "快锁结构", "防滑手柄"]'::jsonb, 85, TRUE);

-- Browsing history makes recommendation demos personalized for test1@example.com.
INSERT INTO product_view_history (user_id, product_id, view_count, created_at, last_viewed_at)
SELECT 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', id, 4, TIMESTAMPTZ '2026-05-17 09:00:00+08', TIMESTAMPTZ '2026-05-18 21:20:00+08' FROM products WHERE sku_code = 'SG-LAPTOP-14';
INSERT INTO product_view_history (user_id, product_id, view_count, created_at, last_viewed_at)
SELECT 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', id, 3, TIMESTAMPTZ '2026-05-17 09:05:00+08', TIMESTAMPTZ '2026-05-18 21:12:00+08' FROM products WHERE sku_code = 'SG-MONITOR-27';
INSERT INTO product_view_history (user_id, product_id, view_count, created_at, last_viewed_at)
SELECT 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', id, 2, TIMESTAMPTZ '2026-05-17 09:10:00+08', TIMESTAMPTZ '2026-05-18 20:55:00+08' FROM products WHERE sku_code = 'SG-EARBUDS';
INSERT INTO product_view_history (user_id, product_id, view_count, created_at, last_viewed_at)
SELECT 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', id, 1, TIMESTAMPTZ '2026-05-17 09:15:00+08', TIMESTAMPTZ '2026-05-18 20:30:00+08' FROM products WHERE sku_code = 'SG-PHONE-X1';

-- Single-shop cart for auto checkout demo.
INSERT INTO cart_items (user_id, product_id, quantity, created_at, updated_at)
SELECT 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', id, 1, TIMESTAMPTZ '2026-05-18 21:30:00+08', TIMESTAMPTZ '2026-05-18 21:30:00+08' FROM products WHERE sku_code = 'SG-LAPTOP-14';
INSERT INTO cart_items (user_id, product_id, quantity, created_at, updated_at)
SELECT 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', id, 1, TIMESTAMPTZ '2026-05-18 21:32:00+08', TIMESTAMPTZ '2026-05-18 21:32:00+08' FROM products WHERE sku_code = 'SG-MONITOR-27';

-- Keep benchmark-compatible orders for test1@example.com.
INSERT INTO orders (id, user_id, shop_id, status, address, contact_email, total_amount, created_at) VALUES
('ORD202603300001', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '00000000-0000-0000-0000-000000000301', 'pending_shipment', '北京市海淀区中关村软件园二期 8 号楼', 'test1@example.com', 4498.00, TIMESTAMPTZ '2026-03-30 10:00:00+08'),
('ORD202603300002', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '00000000-0000-0000-0000-000000000302', 'shipped', '上海市浦东新区世纪大道 100 号', 'test1@example.com', 1299.00, TIMESTAMPTZ '2026-03-30 12:10:00+08');

INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal)
SELECT 'ORD202603300001', id, name, price, 1, price FROM products WHERE sku_code = 'SG-PHONE-X1';
INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal)
SELECT 'ORD202603300001', id, name, price, 1, price FROM products WHERE sku_code = 'SG-EARBUDS';
INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal)
SELECT 'ORD202603300002', id, name, price, 1, price FROM products WHERE sku_code = 'QH-LOCK-PRO';

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
    llm_raw_text,
    updated_at
) VALUES
(
    'ORD202603300002',
    '00000000-0000-0000-0000-000000000402',
    'SF123456789',
    'in_transit',
    '上海分拨中心',
    121.473700,
    31.230400,
    TIMESTAMPTZ '2026-04-01 18:00:00+08',
    '["广州默认仓", "杭州转运中心", "上海分拨中心", "浦东派送站"]'::jsonb,
    '[{"name":"广州默认仓","lng":113.264400,"lat":23.129100},{"name":"杭州转运中心","lng":120.155100,"lat":30.274100},{"name":"上海分拨中心","lng":121.473700,"lat":31.230400},{"name":"浦东派送站","lng":121.544000,"lat":31.221000}]'::jsonb,
    '包裹已到达上海分拨中心，预计明日送达。',
    TIMESTAMPTZ '2026-03-31 16:20:00+08'
);

INSERT INTO after_sales (order_id, type, reason, status, created_at) VALUES
('ORD202603300002', 'return', '历史售后示例：用户反馈门锁外包装破损，商家已完成退货退款。', 'completed', TIMESTAMPTZ '2026-04-02 14:20:00+08');

-- Additional test2@example.com orders cover merchant and after-sales demonstrations.
INSERT INTO orders (id, user_id, shop_id, status, address, contact_email, total_amount, created_at) VALUES
('ORD202604010001', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', '00000000-0000-0000-0000-000000000301', 'shipped', '南京市建邺区江东中路 88 号', 'test2@example.com', 5499.00, TIMESTAMPTZ '2026-04-01 09:15:00+08'),
('ORD202604010002', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', '00000000-0000-0000-0000-000000000301', 'shipped', '南京市建邺区江东中路 88 号', 'test2@example.com', 1899.00, TIMESTAMPTZ '2026-04-01 11:35:00+08'),
('ORD202604020001', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', '00000000-0000-0000-0000-000000000303', 'pending_shipment', '杭州市西湖区文三路 90 号', 'test2@example.com', 1998.00, TIMESTAMPTZ '2026-04-02 10:10:00+08'),
('ORD202604030001', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', '00000000-0000-0000-0000-000000000303', 'shipped', '杭州市西湖区文三路 90 号', 'test2@example.com', 1299.00, TIMESTAMPTZ '2026-04-03 13:00:00+08'),
('ORD202604040001', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', '00000000-0000-0000-0000-000000000304', 'shipped', '成都市高新区天府三街 199 号', 'test2@example.com', 797.00, TIMESTAMPTZ '2026-04-04 15:30:00+08'),
('ORD202604050001', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', '00000000-0000-0000-0000-000000000304', 'shipped', '成都市高新区天府三街 199 号', 'test2@example.com', 958.00, TIMESTAMPTZ '2026-04-05 16:45:00+08');

INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal)
SELECT 'ORD202604010001', id, name, price, 1, price FROM products WHERE sku_code = 'SG-LAPTOP-14';
INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal)
SELECT 'ORD202604010002', id, name, price, 1, price FROM products WHERE sku_code = 'SG-MONITOR-27';
INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal)
SELECT 'ORD202604020001', id, name, price, 1, price FROM products WHERE sku_code = 'BG-CHAIR-PRO';
INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal)
SELECT 'ORD202604020001', id, name, price, 1, price FROM products WHERE sku_code = 'BG-MEETING-M4';
INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal)
SELECT 'ORD202604030001', id, name, price, 1, price FROM products WHERE sku_code = 'BG-CHAIR-PRO';
INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal)
SELECT 'ORD202604040001', id, name, price, 1, price FROM products WHERE sku_code = 'OUT-BACKPACK-32';
INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal)
SELECT 'ORD202604040001', id, name, price, 2, price * 2 FROM products WHERE sku_code = 'OUT-CAMP-LAMP';
INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal)
SELECT 'ORD202604050001', id, name, price, 1, price FROM products WHERE sku_code = 'OUT-JACKET-STORM';
INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal)
SELECT 'ORD202604050001', id, name, price, 1, price FROM products WHERE sku_code = 'OUT-THERMOS-800';

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
    llm_raw_text,
    updated_at
) VALUES
('ORD202604010001', '00000000-0000-0000-0000-000000000401', 'SF202604010001', 'delivered', '南京建邺签收点', 118.732900, 32.003600, TIMESTAMPTZ '2026-04-03 18:00:00+08', '["深圳默认仓", "南京转运中心", "南京建邺签收点"]'::jsonb, '[{"name":"深圳默认仓","lng":113.934000,"lat":22.540000},{"name":"南京转运中心","lng":118.796900,"lat":32.060300},{"name":"南京建邺签收点","lng":118.732900,"lat":32.003600}]'::jsonb, '订单已签收，可演示退货或换货申请。', TIMESTAMPTZ '2026-04-03 13:20:00+08'),
('ORD202604010002', '00000000-0000-0000-0000-000000000401', 'SF202604010002', 'delivered', '南京建邺签收点', 118.732900, 32.003600, TIMESTAMPTZ '2026-04-03 18:00:00+08', '["深圳默认仓", "南京转运中心", "南京建邺签收点"]'::jsonb, '[{"name":"深圳默认仓","lng":113.934000,"lat":22.540000},{"name":"南京转运中心","lng":118.796900,"lat":32.060300},{"name":"南京建邺签收点","lng":118.732900,"lat":32.003600}]'::jsonb, '订单已签收，售后待商家处理。', TIMESTAMPTZ '2026-04-03 15:00:00+08'),
('ORD202604030001', '00000000-0000-0000-0000-000000000403', 'SF202604030001', 'delivered', '杭州西湖签收点', 120.130300, 30.259200, TIMESTAMPTZ '2026-04-05 18:00:00+08', '["上海默认仓", "杭州转运中心", "杭州西湖签收点"]'::jsonb, '[{"name":"上海默认仓","lng":121.599000,"lat":31.204000},{"name":"杭州转运中心","lng":120.155100,"lat":30.274100},{"name":"杭州西湖签收点","lng":120.130300,"lat":30.259200}]'::jsonb, '订单已签收，商家已同意换货。', TIMESTAMPTZ '2026-04-05 12:00:00+08'),
('ORD202604040001', '00000000-0000-0000-0000-000000000404', 'SF202604040001', 'delivered', '成都高新签收点', 104.066800, 30.572800, TIMESTAMPTZ '2026-04-06 18:00:00+08', '["杭州默认仓", "成都转运中心", "成都高新签收点"]'::jsonb, '[{"name":"杭州默认仓","lng":120.016000,"lat":30.284000},{"name":"成都转运中心","lng":104.066800,"lat":30.572800},{"name":"成都高新签收点","lng":104.070600,"lat":30.553900}]'::jsonb, '订单已签收，退货质检处理中。', TIMESTAMPTZ '2026-04-06 11:40:00+08'),
('ORD202604050001', '00000000-0000-0000-0000-000000000404', 'SF202604050001', 'delivered', '成都高新签收点', 104.066800, 30.572800, TIMESTAMPTZ '2026-04-07 18:00:00+08', '["杭州默认仓", "成都转运中心", "成都高新签收点"]'::jsonb, '[{"name":"杭州默认仓","lng":120.016000,"lat":30.284000},{"name":"成都转运中心","lng":104.066800,"lat":30.572800},{"name":"成都高新签收点","lng":104.070600,"lat":30.553900}]'::jsonb, '订单已签收，历史售后已完成。', TIMESTAMPTZ '2026-04-07 14:30:00+08');

INSERT INTO after_sales (order_id, type, reason, status, created_at) VALUES
('ORD202604010002', 'return', '显示器屏幕边框有明显磕碰，申请退货退款。', 'submitted', TIMESTAMPTZ '2026-04-04 10:00:00+08'),
('ORD202604030001', 'exchange', '人体工学椅扶手配件错发，申请换货。', 'merchant_approved', TIMESTAMPTZ '2026-04-06 09:30:00+08'),
('ORD202604040001', 'return', '背包外袋拉链损坏，商家已收件质检中。', 'processing', TIMESTAMPTZ '2026-04-07 11:10:00+08'),
('ORD202604050001', 'exchange', '冲锋衣尺码不合适，已完成换货。', 'completed', TIMESTAMPTZ '2026-04-08 15:45:00+08');

INSERT INTO logistics_complaints (order_id, reason, status, resolution_note, created_at, updated_at) VALUES
('ORD202604010001', '派送曾延迟一天，用户要求核实原因。', 'resolved', '客服已解释因极端天气导致延迟，并补偿优惠券。', TIMESTAMPTZ '2026-04-03 18:30:00+08', TIMESTAMPTZ '2026-04-04 09:00:00+08');
