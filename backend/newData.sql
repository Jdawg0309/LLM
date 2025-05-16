DROP DATABASE IF EXISTS llmscribe_db;

CREATE DATABASE llmscribe_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE llmscribe_db;

-- Users Table
CREATE TABLE `user` (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(150) NOT NULL UNIQUE,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(150) NOT NULL,
    user_type ENUM('free', 'paid', 'super') NOT NULL DEFAULT 'free',
    balance FLOAT NOT NULL DEFAULT 0.0,
    last_submission DATETIME,
    is_suspended BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Token Transactions Table
CREATE TABLE token_transaction (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    amount INT NOT NULL,
    transaction_type ENUM('purchase', 'penalty', 'usage') NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES `user`(id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Blacklist Table
CREATE TABLE blacklist (
    id INT PRIMARY KEY AUTO_INCREMENT,
    word VARCHAR(50) NOT NULL UNIQUE,
    submitted_by INT NOT NULL,
    status ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (submitted_by) REFERENCES `user`(id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Correction History Table
CREATE TABLE correction_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    original_text TEXT NOT NULL,
    corrected_text TEXT NOT NULL,
    correction_type ENUM('self', 'llm') NOT NULL,
    tokens_used INT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES `user`(id),
    INDEX idx_correction_type (correction_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE invitations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    inviter_id INT NOT NULL, -- The user who sent the invitation
    invitee_id INT NOT NULL, -- The user who received the invitation
    text_file_id INT NOT NULL, -- The shared text file
    status ENUM('pending', 'accepted', 'rejected') NOT NULL DEFAULT 'pending', -- Status of the invitation
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inviter_id) REFERENCES user(id),
    FOREIGN KEY (invitee_id) REFERENCES user(id),
    FOREIGN KEY (text_file_id) REFERENCES text_files(id)
);

CREATE TABLE collaborations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL, -- The collaborator
    text_file_id INT NOT NULL, -- The shared text file
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (text_file_id) REFERENCES text_files(id)
);

CREATE TABLE text_files (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    owner_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES user(id)
);