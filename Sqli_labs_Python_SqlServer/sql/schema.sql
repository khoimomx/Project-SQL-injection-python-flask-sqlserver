CREATE USER lab_student WITHOUT LOGIN;

CREATE TABLE dbo.catalog (
    id int PRIMARY KEY,
    sku varchar(20) NOT NULL UNIQUE,
    title nvarchar(90) NOT NULL
);
CREATE TABLE dbo.lab_notes (
    tag varchar(30) PRIMARY KEY,
    code varchar(64) NOT NULL
);
CREATE TABLE dbo.invites (invite_code varchar(30) PRIMARY KEY);

CREATE TABLE dbo.visit_log (
    id int IDENTITY PRIMARY KEY,
    client_name nvarchar(600) NOT NULL
);
CREATE TABLE dbo.profiles (
    scope varchar(33) PRIMARY KEY,
    display_name nvarchar(600) NOT NULL,
    badge nvarchar(40) NOT NULL
);
CREATE TABLE dbo.saved_filters (
    scope varchar(33) PRIMARY KEY,
    term nvarchar(600) NOT NULL
);
GO
-- A browser gets a different scope in each mode. Even a modified WHERE
-- clause cannot read or change another learner's profile or saved filter.
CREATE FUNCTION dbo.visible_scope(@scope varchar(33))
RETURNS TABLE WITH SCHEMABINDING AS
RETURN SELECT 1 AS allowed
    WHERE USER_NAME() <> N'lab_student'
       OR @scope = CONVERT(varchar(33), SESSION_CONTEXT(N'lab_scope'));
GO
CREATE SECURITY POLICY dbo.learner_scope
    ADD FILTER PREDICATE dbo.visible_scope(scope) ON dbo.profiles,
    ADD BLOCK PREDICATE dbo.visible_scope(scope) ON dbo.profiles AFTER INSERT,
    ADD BLOCK PREDICATE dbo.visible_scope(scope) ON dbo.profiles AFTER UPDATE,
    ADD FILTER PREDICATE dbo.visible_scope(scope) ON dbo.saved_filters,
    ADD BLOCK PREDICATE dbo.visible_scope(scope) ON dbo.saved_filters AFTER INSERT,
    ADD BLOCK PREDICATE dbo.visible_scope(scope) ON dbo.saved_filters AFTER UPDATE
    WITH (STATE = ON);

GRANT SELECT ON dbo.catalog TO lab_student;
GRANT SELECT ON dbo.lab_notes TO lab_student;
GRANT SELECT ON dbo.invites TO lab_student;
GRANT INSERT ON dbo.visit_log TO lab_student;
GRANT SELECT, INSERT ON dbo.profiles TO lab_student;
GRANT UPDATE ON dbo.profiles (display_name, badge) TO lab_student;
GRANT SELECT, INSERT ON dbo.saved_filters TO lab_student;
GRANT UPDATE ON dbo.saved_filters (term) TO lab_student;
