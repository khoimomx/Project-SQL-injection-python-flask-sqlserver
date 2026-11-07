-- Only the six tables owned by this lab are touched by reset.
DELETE FROM dbo.saved_filters;
DELETE FROM dbo.profiles;
DELETE FROM dbo.visit_log;
DELETE FROM dbo.invites;
DELETE FROM dbo.lab_notes;
DELETE FROM dbo.catalog;

INSERT dbo.catalog (id, sku, title) VALUES
    (1, 'MK-01', N'Sổ tay lưới'),
    (2, 'MK-02', N'Sổ tay chấm'),
    (3, 'BK-03', N'Bút kỹ thuật'),
    (4, 'ST-04', N'Thước thép');
INSERT dbo.invites VALUES ('OPEN-LAB');
INSERT dbo.lab_notes (tag, code) VALUES
    ('union-id', 'ATLAS-17'), ('union-form', 'ORBIT-23'),
    ('error-sku', 'DELTA-41'), ('error-id', 'ION-62'),
    ('blind-sku', 'KITE-08'), ('blind-form', 'MICA-12'),
    ('time-id', 'TIDE-09'), ('time-form', 'WAVE-16'),
    ('header', 'RADIO-18'), ('cookie', 'EMBER-20'),
    ('saved', 'ECHO-24');
