-- Use only for SQL Server 2019 or later

--CREATE DATABASE PR_LAB_APP;
--GO
--USE PR_LAB_APP;
--GO

--CREATE TABLE dbo.files (
--    id BIGINT IDENTITY(1,1) PRIMARY KEY,
--    filename NVARCHAR(255) NOT NULL UNIQUE,
--    size_bytes BIGINT NOT NULL,
--    uploaded_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
--);
--GO

--CREATE TABLE dbo.messages (
--    id BIGINT IDENTITY(1,1) PRIMARY KEY,
--    text NVARCHAR(500) NOT NULL,
--    file_name NVARCHAR(255) NULL,
--    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
--);
--GO

--SELECT * FROM dbo.files;
--SELECT * FROM dbo.messages;


--CREATE LOGIN Delta WITH PASSWORD = 'IDK5!';
--GO

--USE PR_LAB_APP;
--GO
--CREATE USER White_Delta FOR LOGIN Delta;
--GO
--ALTER ROLE db_owner ADD MEMBER White_Delta;
--GO

--SELECT name, is_disabled
--FROM sys.server_triggers
--WHERE parent_class_desc = 'SERVER';

--DISABLE TRIGGER ALL ON ALL SERVER;