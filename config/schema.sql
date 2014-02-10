SET NAMES utf8;

-- ----------------------------
--  Table structure for `oauth`
-- ----------------------------
DROP TABLE IF EXISTS `oauth`;
CREATE TABLE `oauth` (
  `oauth_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `client_id` varchar(255) NOT NULL,
  `client_secret` varchar(255) NOT NULL,
  `access_token` varchar(255),
  `refresh_token` varchar(255),
  PRIMARY KEY (`oauth_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2511 DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT;

-- ----------------------------
--  Table structure for `job`
-- ----------------------------
DROP TABLE IF EXISTS `job`;
CREATE TABLE `job` (
  `job_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `state` int(1) NOT NULL DEFAULT 0,
  `zombie_head` int(10) DEFAULT 1,
  `folder_id` varchar(255),
  `description` varchar(255) DEFAULT 'I am a lazy piece of shit and I did not enter a description',
  `from_change_id` bigint DEFAULT 1,
  `last_run` datetime DEFAULT NULL,
  `oauth_id` int(10) unsigned NOT NULL,
  PRIMARY KEY (`job_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2511 DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT;

-- ----------------------------
--  Table structure for `revision`
-- ----------------------------
DROP TABLE IF EXISTS `revision`;
CREATE TABLE `revision` (
  `file_id` varchar(255) NOT NULL,
  `revision_id` varchar(255) NOT NULL,
  `mime_type` varchar(255) NOT NULL,
  `modified_date` datetime NOT NULL,
  `last_modifying_user_name` varchar(255) NOT NULL,
  `md5` varchar(255),
  `file_size` bigint,
  `file_contents` blob,
  `file_contents_plaintext` text, 
  `file_contents_plaintext_diff` text,
  PRIMARY KEY (`file_id`,`revision_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2511 DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT;

-- ----------------------------
--  Table structure for `file`
-- ----------------------------
DROP TABLE IF EXISTS `file`;
CREATE TABLE `file` (
  `file_id` varchar(255) NOT NULL,
  `title` varchar(255) NOT NULL,
  `mime_type` varchar(255) NOT NULL,
  `description` varchar(255) NOT NULL,
  `shared` boolean,
  `writers_can_share` boolean,
  `created_date` datetime NOT NULL,
  `modified_date` datetime NOT NULL,
  `original_filename` varchar(255),
  `md5` varchar(255),
  `file_extension` varchar(255),
  `file_size` bigint,
  `last_modifying_user_name` varchar(255) NOT NULL,
  PRIMARY KEY (`file_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2511 DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT;

-- ----------------------------
--  Table structure for `file_owners`
-- ----------------------------
DROP TABLE IF EXISTS `file_owners`;
CREATE TABLE `file_owners` (
  `file_id` varchar(255) NOT NULL,
  `owner_name` varchar(255) NOT NULL,
  PRIMARY KEY (`file_id`, `owner_name`)
) ENGINE=InnoDB AUTO_INCREMENT=2511 DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT;

-- ----------------------------
--  Table structure for `comment`
-- ----------------------------
DROP TABLE IF EXISTS `comment`;
CREATE TABLE `comment` (
  `file_id` varchar(255) NOT NULL,
  `comment_id` varchar(255) NOT NULL,
  `created_date` datetime NOT NULL,
  `modified_date` datetime NOT NULL,
  `author` varchar(255) NOT NULL,
  `content` varchar(255) NOT NULL,
  `status` varchar(255) NOT NULL,
  PRIMARY KEY (`file_id`, `comment_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2511 DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT;

-- ----------------------------
--  Table structure for `reply`
-- ----------------------------
DROP TABLE IF EXISTS `reply`;
CREATE TABLE `reply` (
  `file_id` varchar(255) NOT NULL,
  `comment_id` varchar(255) NOT NULL,
  `reply_id` varchar(255) NOT NULL,
  `created_date` datetime NOT NULL,
  `modified_date` datetime NOT NULL,
  `author` varchar(255) NOT NULL,
  `content` varchar(255) NOT NULL,
  PRIMARY KEY (`file_id`, `comment_id`, `reply_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2511 DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT;