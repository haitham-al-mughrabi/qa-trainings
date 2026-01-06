# MySQL Migration Setup Guide

## Overview

Your QA Trainings application has been configured to use MySQL instead of SQLite. This guide walks you through the migration process.

## What's Been Updated

### 1. **docker-compose.yml**
   - Added MySQL 8.0 service with automatic database creation
   - Configured networking and health checks
   - Set up persistent volume for MySQL data
   - Web service now depends on MySQL being healthy

### 2. **app.py**
   - Updated to detect `DATABASE_URL` environment variable
   - Automatically uses MySQL when running in Docker
   - Falls back to SQLite for local development if no DATABASE_URL is set

### 3. **Dependencies**
   - **pyproject.toml**: Added `pymysql` for MySQL support
   - **requirements.txt**: Added `pymysql`

### 4. **Migration Script**
   - Created `migrate_to_mysql.py` - copies all data from SQLite to MySQL

## Quick Start

### Option 1: Using Docker (Recommended)

#### Step 1: Install Dependencies
```bash
pip install pymysql
```

#### Step 2: Start MySQL Container
```bash
docker-compose up -d mysql
```

Wait for MySQL to be ready (about 10-15 seconds):
```bash
docker-compose logs mysql | grep "ready for connections"
```

#### Step 3: Run Migration
```bash
python migrate_to_mysql.py --mysql-host localhost --mysql-user qa_user --mysql-password qa_password
```

#### Step 4: Start Full Application
```bash
docker-compose up -d
```

Access the app at http://localhost:5000

#### Step 5: Verify Migration
The application should now be using MySQL. You can verify by:
- Checking application functionality
- Viewing logs: `docker-compose logs web`

### Option 2: Local MySQL Setup

If you have MySQL 8.0+ installed locally on your machine:

#### Step 1: Create Database and User
```sql
CREATE DATABASE qa_trainings;
CREATE USER 'qa_user'@'localhost' IDENTIFIED BY 'qa_password';
GRANT ALL PRIVILEGES ON qa_trainings.* TO 'qa_user'@'localhost';
FLUSH PRIVILEGES;
```

#### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 3: Run Migration
```bash
python migrate_to_mysql.py --mysql-host localhost --mysql-user qa_user --mysql-password qa_password
```

#### Step 4: Start Application
```bash
python app.py
```

Access at http://localhost:5000

## Migration Script Usage

### Basic Usage (Default credentials)
```bash
python migrate_to_mysql.py
```

### With Custom Credentials
```bash
python migrate_to_mysql.py \
  --mysql-host mysql.example.com \
  --mysql-port 3306 \
  --mysql-user your_user \
  --mysql-password your_password \
  --mysql-db your_database
```

### What the Script Does
1. ✓ Checks SQLite database exists
2. ✓ Connects to MySQL
3. ✓ Truncates existing tables in MySQL (safety measure)
4. ✓ Copies all data from SQLite to MySQL:
   - training (6 records)
   - topic (332 records)
   - student (14 records)
   - instructor (3 records)
   - attendance (252 records)
   - progress (261 records)
   - knowledge_skill (7 records)
   - knowledge_assessment (55 records)
   - certificate (14 records)
   - training_instructors (association table)
5. ✓ Verifies all data was copied correctly
6. ✓ Shows summary report

### Script Output Example
```
======================================================================
QA Trainings: SQLite to MySQL Migration
======================================================================

✓ SQLite database found: /Users/.../instance/trainings.db

Connecting to MySQL at localhost:3306...
✓ Connected to MySQL database 'qa_trainings'

Migrating data from SQLite to MySQL...

  ✓ training: 6 records migrated
  ✓ topic: 332 records migrated
  ✓ student: 14 records migrated
  ✓ instructor: 3 records migrated
  ✓ attendance: 252 records migrated
  ✓ progress: 261 records migrated
  ✓ knowledge_skill: 7 records migrated
  ✓ knowledge_assessment: 55 records migrated
  ✓ certificate: 14 records migrated

Verifying migration...
  ✓ training: 6 records verified
  ✓ topic: 332 records verified
  ... [more records verified]

======================================================================
✓ Migration completed successfully!
======================================================================

Database Configuration:
  Host: localhost:3306
  Database: qa_trainings
  User: qa_user
  Total records migrated: 941

Your app is configured to use MySQL via DATABASE_URL environment variable.

To start with Docker: docker-compose up -d
```

## Docker Credentials

Default credentials in docker-compose.yml:
- **Root Password**: `root_password`
- **Database**: `qa_trainings`
- **User**: `qa_user`
- **Password**: `qa_password`
- **Port**: 3306

⚠️ **Important**: Change these in production! Edit `docker-compose.yml` before deploying.

## Troubleshooting

### Connection Refused
```
Error: Connection refused at localhost:3306
```
**Solution**: Make sure MySQL container is running:
```bash
docker-compose ps
docker-compose up -d mysql
```

### Database Not Found
```
Error: Unknown database 'qa_trainings'
```
**Solution**: Docker-compose creates it automatically. If using local MySQL:
```sql
CREATE DATABASE qa_trainings;
```

### Permission Denied
```
Error: Access denied for user 'qa_user'@'localhost'
```
**Solution**: Verify credentials match your MySQL setup or docker-compose.yml

### Migration Script Can't Connect
```
Error: No module named 'pymysql'
```
**Solution**: Install pymysql:
```bash
pip install pymysql
```

### Partial Migration (Data Mismatch)
If verification shows mismatched record counts:
1. Check MySQL is accessible
2. Verify table structure: `DESCRIBE table_name;`
3. Check MySQL error logs: `docker-compose logs mysql`

## Verification Checklist

After migration, verify:
- [ ] All tables exist in MySQL
- [ ] Record counts match SQLite (see script output)
- [ ] Application loads without errors
- [ ] Can view trainings at http://localhost:5000/trainings
- [ ] Can access admin panel (if applicable)
- [ ] Search/filter functions work
- [ ] Can create new records

## Database Structure

All 10 tables are migrated with their original structure:

| Table | Records | Purpose |
|-------|---------|---------|
| training | 6 | Training programs |
| topic | 332 | Training topics/sessions |
| student | 14 | Student records |
| instructor | 3 | Instructor profiles |
| attendance | 252 | Attendance tracking |
| progress | 261 | Learning progress tracking |
| knowledge_skill | 7 | Available skills |
| knowledge_assessment | 55 | Skill assessments |
| certificate | 14 | Issued certificates |
| training_instructors | - | Instructor-training mapping |

## Reverting to SQLite

If you need to revert to SQLite:
1. Stop Docker containers: `docker-compose down`
2. Remove DATABASE_URL from docker-compose.yml or your environment
3. The app will automatically use SQLite: `instance/trainings.db`

## Additional Commands

### View MySQL Logs
```bash
docker-compose logs mysql
```

### View Web App Logs
```bash
docker-compose logs web
```

### Connect to MySQL Directly
```bash
docker exec -it qa-trainings-mysql mysql -uqa_user -p qa_trainings
```

### Stop Everything
```bash
docker-compose down
```

### Remove Data Volumes (WARNING: Deletes MySQL data)
```bash
docker-compose down -v
```

## Support

For issues with:
- **SQLite/MySQL**: Check database connection logs
- **Flask app**: Review `docker-compose logs web`
- **Container issues**: Run `docker-compose down && docker-compose up -d`

---

**Database Migration Date**: 2026-01-06
**SQLite Location**: `/instance/trainings.db`
**MySQL Default Port**: 3306
