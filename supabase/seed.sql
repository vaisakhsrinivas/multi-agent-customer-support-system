-- Demo data: stable UUIDs for reproducible FKs (12+ rows per table).

insert into public.customers (id, email, full_name, phone) values
  ('aaaaaaaa-0001-4000-8000-000000000001', 'ava.chen@example.com', 'Ava Chen', '+1-415-555-0101'),
  ('aaaaaaaa-0001-4000-8000-000000000002', 'ben.ortiz@example.com', 'Ben Ortiz', '+1-206-555-0102'),
  ('aaaaaaaa-0001-4000-8000-000000000003', 'chloe.kim@example.com', 'Chloe Kim', '+1-646-555-0103'),
  ('aaaaaaaa-0001-4000-8000-000000000004', 'diego.martinez@example.com', 'Diego Martinez', '+1-512-555-0104'),
  ('aaaaaaaa-0001-4000-8000-000000000005', 'emma.nielsen@example.com', 'Emma Nielsen', '+45-20-555-0105'),
  ('aaaaaaaa-0001-4000-8000-000000000006', 'farah.ali@example.com', 'Farah Ali', '+44-20-5550-0106'),
  ('aaaaaaaa-0001-4000-8000-000000000007', 'gavin.obrien@example.com', 'Gavin O''Brien', '+353-1-555-0107'),
  ('aaaaaaaa-0001-4000-8000-000000000008', 'hana.sato@example.com', 'Hana Sato', '+81-3-5555-0108'),
  ('aaaaaaaa-0001-4000-8000-000000000009', 'ivan.petrov@example.com', 'Ivan Petrov', '+7-495-555-0109'),
  ('aaaaaaaa-0001-4000-8000-00000000000a', 'julia.silva@example.com', 'Julia Silva', '+55-11-5555-0110'),
  ('aaaaaaaa-0001-4000-8000-00000000000b', 'ken.tan@example.com', 'Ken Tan', '+65-6555-0111'),
  ('aaaaaaaa-0001-4000-8000-00000000000c', 'lina.haddad@example.com', 'Lina Haddad', '+971-4-555-0112');

insert into public.orders (id, customer_id, status, total_cents, currency, placed_at) values
  ('bbbbbbbb-0001-4000-8000-000000000001', 'aaaaaaaa-0001-4000-8000-000000000001', 'delivered', 4999, 'USD', '2025-11-02 14:30:00+00'),
  ('bbbbbbbb-0001-4000-8000-000000000002', 'aaaaaaaa-0001-4000-8000-000000000001', 'shipped', 12900, 'USD', '2025-12-10 09:15:00+00'),
  ('bbbbbbbb-0001-4000-8000-000000000003', 'aaaaaaaa-0001-4000-8000-000000000001', 'pending', 2499, 'USD', '2026-01-05 18:00:00+00'),
  ('bbbbbbbb-0001-4000-8000-000000000004', 'aaaaaaaa-0001-4000-8000-000000000002', 'delivered', 8900, 'USD', '2025-10-18 11:20:00+00'),
  ('bbbbbbbb-0001-4000-8000-000000000005', 'aaaaaaaa-0001-4000-8000-000000000002', 'cancelled', 1500, 'USD', '2025-11-28 16:45:00+00'),
  ('bbbbbbbb-0001-4000-8000-000000000006', 'aaaaaaaa-0001-4000-8000-000000000003', 'shipped', 22050, 'USD', '2026-02-01 08:00:00+00'),
  ('bbbbbbbb-0001-4000-8000-000000000007', 'aaaaaaaa-0001-4000-8000-000000000003', 'pending', 750, 'USD', '2026-02-20 12:30:00+00'),
  ('bbbbbbbb-0001-4000-8000-000000000008', 'aaaaaaaa-0001-4000-8000-000000000004', 'delivered', 19999, 'USD', '2025-09-14 10:00:00+00'),
  ('bbbbbbbb-0001-4000-8000-000000000009', 'aaaaaaaa-0001-4000-8000-000000000005', 'shipped', 4599, 'EUR', '2026-01-22 07:45:00+00'),
  ('bbbbbbbb-0001-4000-8000-00000000000a', 'aaaaaaaa-0001-4000-8000-000000000006', 'delivered', 11200, 'GBP', '2025-12-03 15:10:00+00'),
  ('bbbbbbbb-0001-4000-8000-00000000000b', 'aaaaaaaa-0001-4000-8000-000000000007', 'pending', 3300, 'EUR', '2026-03-01 09:00:00+00'),
  ('bbbbbbbb-0001-4000-8000-00000000000c', 'aaaaaaaa-0001-4000-8000-000000000008', 'delivered', 6780, 'JPY', '2025-11-11 23:59:00+00');

insert into public.support_tickets (id, customer_id, order_id, subject, body, status, priority, created_at) values
  ('cccccccc-0001-4000-8000-000000000001', 'aaaaaaaa-0001-4000-8000-000000000001', 'bbbbbbbb-0001-4000-8000-000000000001', 'Wrong item received', 'Order arrived with SKU A instead of B. Please advise return process.', 'open', 'high', '2026-03-10 10:00:00+00'),
  ('cccccccc-0001-4000-8000-000000000002', 'aaaaaaaa-0001-4000-8000-00000000000a', null, 'Update shipping address', 'I moved apartments last week and need to update my default address.', 'in_progress', 'normal', '2026-03-11 11:30:00+00'),
  ('cccccccc-0001-4000-8000-000000000003', 'aaaaaaaa-0001-4000-8000-000000000002', 'bbbbbbbb-0001-4000-8000-000000000004', 'Tracking not updating', 'Carrier shows label created but no scans for 4 days.', 'open', 'normal', '2026-03-12 08:15:00+00'),
  ('cccccccc-0001-4000-8000-000000000004', 'aaaaaaaa-0001-4000-8000-000000000006', null, 'Invoice for accounting', 'Need a VAT invoice for my last two orders.', 'resolved', 'low', '2026-02-28 14:00:00+00'),
  ('cccccccc-0001-4000-8000-000000000005', 'aaaaaaaa-0001-4000-8000-000000000003', 'bbbbbbbb-0001-4000-8000-000000000006', 'Change delivery date', 'I will be traveling; can you hold shipment until March 15?', 'open', 'high', '2026-03-13 09:45:00+00'),
  ('cccccccc-0001-4000-8000-000000000006', 'aaaaaaaa-0001-4000-8000-000000000004', null, 'Loyalty points balance', 'My account shows 500 fewer points than expected after January purchases.', 'in_progress', 'normal', '2026-03-09 16:20:00+00'),
  ('cccccccc-0001-4000-8000-000000000007', 'aaaaaaaa-0001-4000-8000-000000000005', 'bbbbbbbb-0001-4000-8000-000000000009', 'Damaged packaging', 'Box was crushed; product seems fine but I want it logged.', 'open', 'low', '2026-03-14 07:00:00+00'),
  ('cccccccc-0001-4000-8000-000000000008', 'aaaaaaaa-0001-4000-8000-00000000000b', null, 'Email preferences', 'Please stop promotional emails but keep order notifications.', 'resolved', 'low', '2026-03-01 12:00:00+00'),
  ('cccccccc-0001-4000-8000-000000000009', 'aaaaaaaa-0001-4000-8000-000000000007', 'bbbbbbbb-0001-4000-8000-00000000000b', 'Payment declined retry', 'Card was declined; I updated the card on file—please retry charge.', 'open', 'high', '2026-03-15 13:10:00+00'),
  ('cccccccc-0001-4000-8000-00000000000a', 'aaaaaaaa-0001-4000-8000-000000000008', null, 'Product registration', 'How do I register my device for the extended warranty?', 'in_progress', 'normal', '2026-03-16 08:30:00+00'),
  ('cccccccc-0001-4000-8000-00000000000b', 'aaaaaaaa-0001-4000-8000-000000000009', null, 'Account access', 'I cannot reset my password; reset emails never arrive.', 'open', 'normal', '2026-03-17 17:45:00+00'),
  ('cccccccc-0001-4000-8000-00000000000c', 'aaaaaaaa-0001-4000-8000-00000000000c', null, 'Bulk order quote', 'Need pricing for 50 units for a small business event.', 'open', 'normal', '2026-03-18 10:05:00+00');
