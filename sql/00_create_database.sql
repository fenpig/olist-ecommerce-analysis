-- File: 00_create_database.sql
-- Goal: Initialize the Phase 1 project database with the approved character set and collation.
-- Input objects: None.
-- Output objects: Database `olist_delivery_analysis`.
-- Prerequisites: MySQL 8.0.44 access and explicit user authorization to execute SQL.
-- Repeatable: Yes, through IF NOT EXISTS.
-- Implementation task: T06 scaffold; execution is deferred to a later authorized task.
-- Current status: scaffold.
-- Safety: This file is not executed in T06 and contains no destructive statements.

CREATE DATABASE IF NOT EXISTS `olist_delivery_analysis`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
