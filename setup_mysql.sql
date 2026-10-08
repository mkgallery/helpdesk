-- Run with:  sudo mysql < setup_mysql.sql
CREATE DATABASE IF NOT EXISTS helpdesk_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'helpdesk_user'@'localhost' IDENTIFIED BY 'StrongPass123!';
GRANT ALL PRIVILEGES ON helpdesk_db.* TO 'helpdesk_user'@'localhost';
FLUSH PRIVILEGES;
