BEGIN;

DELETE FROM logistics_complaints
WHERE order_id IN ('ORD202603300001', 'ORD202603300002');

DELETE FROM after_sales
WHERE order_id IN ('ORD202603300001', 'ORD202603300002');

INSERT INTO after_sales (order_id, type, reason, status)
VALUES (
    'ORD202603300002',
    'return',
    '历史售后示例：外包装破损，已完成退货处理',
    'completed'
);

UPDATE orders
SET
    status = 'pending_shipment',
    address = '北京市海淀区中关村软件园二期 8 号楼',
    contact_email = 'test1@example.com'
WHERE id = 'ORD202603300001';

UPDATE orders
SET
    status = 'shipped',
    address = '上海市浦东新区张江高科路 88 号',
    contact_email = 'test1@example.com'
WHERE id = 'ORD202603300002';

DELETE FROM chat_context_snapshots;
DELETE FROM chat_messages;
DELETE FROM chat_sessions;
DELETE FROM chat_user_global_memory;
DELETE FROM chat_pending_actions;

COMMIT;
